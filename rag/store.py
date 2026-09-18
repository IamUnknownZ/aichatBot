from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import numpy as np

from .models import DocumentChunk, ExtractedImage, ParsedDocument, SearchHit


def _char_trigrams(text: str) -> set[str]:
    compact = re.sub(r"\s+", " ", text.lower()).strip()
    if len(compact) < 3:
        return {compact} if compact else set()
    return {compact[i : i + 3] for i in range(len(compact) - 2)}


def _normalize_display_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _lexical_similarity(query: str, text: str) -> float:
    q = _char_trigrams(query)
    if not q:
        return 0.0
    t = _char_trigrams(text)
    if not t:
        return 0.0
    return len(q & t) / len(q)


class VectorStore(Protocol):
    mode: str

    def search(
        self,
        query: str,
        query_vector: list[float] | None,
        *,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]:
        ...

    def images_for_pages(
        self, pages: list[int], *, limit: int = 3
    ) -> list[ExtractedImage]:
        ...

    def log_retrieval(
        self,
        *,
        query: str,
        elapsed_ms: float,
        hits: list[SearchHit],
    ) -> None:
        ...

    def log_answer(
        self,
        *,
        query: str,
        retrieval_ms: float,
        ttft_ms: float,
        total_ms: float,
        top_score: float,
        answered: bool,
        model_name: str,
        pages: list[int],
        answer_chars: int,
    ) -> None:
        ...

    def get_or_create_profile(self, display_name: str) -> dict[str, str] | None:
        ...

    def get_recent_questions(
        self, user_id: str, *, limit: int = 6
    ) -> list[str]:
        ...

    def save_exchange(
        self,
        *,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        ...


class LocalLexicalStore:
    mode = "local-lexical"
    requires_query_embedding = False

    def __init__(
        self,
        chunks: list[DocumentChunk],
        images: list[ExtractedImage] | None = None,
    ) -> None:
        self.chunks = chunks
        self.images = images or []

    @staticmethod
    def _word_tokens(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[A-Za-z0-9_+-]+|[ก-๙]+", text.lower())
            if len(token) > 1
        }

    def search(
        self,
        query: str,
        query_vector: list[float] | None,
        *,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]:
        query_tokens = self._word_tokens(query)
        query_compact = re.sub(r"\s+", " ", query.lower()).strip()

        hits: list[SearchHit] = []
        for chunk in self.chunks:
            text = chunk.content
            text_lower = text.lower()
            text_tokens = self._word_tokens(text)

            trigram_score = _lexical_similarity(query, text)
            token_score = (
                len(query_tokens & text_tokens) / len(query_tokens)
                if query_tokens
                else 0.0
            )

            phrase_boost = 0.0
            english_terms = [
                token for token in query_tokens
                if re.fullmatch(r"[a-z0-9_+-]+", token)
            ]
            if english_terms:
                matched = sum(1 for term in english_terms if term in text_lower)
                phrase_boost = 0.12 * (matched / len(english_terms))

            score = min(
                1.0,
                0.58 * trigram_score
                + 0.42 * token_score
                + phrase_boost,
            )

            if score <= 0:
                continue

            hits.append(
                SearchHit(
                    source_id=chunk.source_id,
                    source_file=chunk.source_file,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=score,
                    vector_score=0.0,
                    lexical_score=score,
                    metadata=chunk.metadata,
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def images_for_pages(
        self, pages: list[int], *, limit: int = 3
    ) -> list[ExtractedImage]:
        wanted = set(pages)
        return [img for img in self.images if img.page_number in wanted][:limit]

    def log_retrieval(
        self,
        *,
        query: str,
        elapsed_ms: float,
        hits: list[SearchHit],
    ) -> None:
        return None

    def log_answer(
        self,
        *,
        query: str,
        retrieval_ms: float,
        ttft_ms: float,
        total_ms: float,
        top_score: float,
        answered: bool,
        model_name: str,
        pages: list[int],
        answer_chars: int,
    ) -> None:
        return None

    def get_or_create_profile(self, display_name: str) -> dict[str, str] | None:
        name = display_name.strip()
        if not name:
            return None
        return {"user_id": str(uuid4()), "display_name": name}

    def get_recent_questions(
        self, user_id: str, *, limit: int = 6
    ) -> list[str]:
        return []

    def save_exchange(
        self,
        *,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        return None


class MemoryVectorStore:
    mode = "memory"
    requires_query_embedding = True

    def __init__(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        images: list[ExtractedImage] | None = None,
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        self.chunks = chunks
        self.matrix = np.asarray(embeddings, dtype=np.float32)
        self.images = images or []

    def search(
        self,
        query: str,
        query_vector: list[float] | None,
        *,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]:
        if not self.chunks:
            return []

        q = np.asarray(query_vector, dtype=np.float32)
        vector_scores = self.matrix @ q
        count = min(max(top_k, candidate_k), len(self.chunks))
        candidate_indices = np.argpartition(
            -vector_scores, count - 1
        )[:count]

        hits: list[SearchHit] = []
        for idx in candidate_indices:
            chunk = self.chunks[int(idx)]
            vector_score = float(vector_scores[int(idx)])
            lexical_score = _lexical_similarity(query, chunk.content)
            score = 0.88 * vector_score + 0.12 * lexical_score
            hits.append(
                SearchHit(
                    source_id=chunk.source_id,
                    source_file=chunk.source_file,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=score,
                    vector_score=vector_score,
                    lexical_score=lexical_score,
                    metadata=chunk.metadata,
                )
            )

        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:top_k]

    def images_for_pages(
        self, pages: list[int], *, limit: int = 3
    ) -> list[ExtractedImage]:
        wanted = set(pages)
        return [img for img in self.images if img.page_number in wanted][:limit]

    def log_retrieval(
        self,
        *,
        query: str,
        elapsed_ms: float,
        hits: list[SearchHit],
    ) -> None:
        return None

    def log_answer(
        self,
        *,
        query: str,
        retrieval_ms: float,
        ttft_ms: float,
        total_ms: float,
        top_score: float,
        answered: bool,
        model_name: str,
        pages: list[int],
        answer_chars: int,
    ) -> None:
        return None

    def get_or_create_profile(self, display_name: str) -> dict[str, str] | None:
        name = display_name.strip()
        if not name:
            return None
        return {"user_id": str(uuid4()), "display_name": name}

    def get_recent_questions(
        self, user_id: str, *, limit: int = 6
    ) -> list[str]:
        return []

    def save_exchange(
        self,
        *,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        return None


class PgVectorStore:
    mode = "postgres-pgvector"
    requires_query_embedding = True

    def __init__(self, database_url: str, *, embedding_dim: int = 768) -> None:
        self.database_url = database_url
        self.embedding_dim = embedding_dim
        self._pool = None

    def _connect(self, *, register: bool = True):
        import psycopg

        if not register:
            return psycopg.connect(self.database_url)

        if self._pool is None:
            from pgvector.psycopg import register_vector
            from psycopg_pool import ConnectionPool

            def configure(conn):
                register_vector(conn)
                # Pool configure callbacks must return an idle connection.
                conn.commit()

            self._pool = ConnectionPool(
                conninfo=self.database_url,
                min_size=1,
                max_size=6,
                open=True,
                configure=configure,
            )
        return self._pool.connection()

    def ensure_schema(self) -> None:
        schema_path = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
        schema = schema_path.read_text(encoding="utf-8")
        schema = schema.replace("vector(768)", f"vector({self.embedding_dim})")

        # The vector type may not exist yet, so do not register the adapter
        # until after CREATE EXTENSION has been executed.
        with self._connect(register=False) as conn:
            with conn.cursor() as cur:
                cur.execute(schema)
            conn.commit()

    def has_document(self, source_id: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM rag_documents WHERE source_id = %s LIMIT 1",
                    (source_id,),
                )
                return cur.fetchone() is not None

    def replace_document(
        self,
        document: ParsedDocument,
        embeddings: list[list[float]],
        *,
        embedding_model: str,
        image_embeddings: list[list[float] | None] | None = None,
    ) -> None:
        from psycopg.types.json import Jsonb

        if len(document.chunks) != len(embeddings):
            raise ValueError("chunk embedding count mismatch")

        image_embeddings = image_embeddings or [None] * len(document.images)
        if len(image_embeddings) != len(document.images):
            raise ValueError("image embedding count mismatch")

        with self._connect() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM rag_documents
                        WHERE source_file = %s AND source_id <> %s
                        """,
                        (document.source_file, document.source_id),
                    )

                    cur.execute(
                        """
                        INSERT INTO rag_documents (
                            source_id, source_file, sha256, page_count,
                            embedding_model, embedding_dim, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, now())
                        ON CONFLICT (source_id) DO UPDATE SET
                            source_file = EXCLUDED.source_file,
                            page_count = EXCLUDED.page_count,
                            embedding_model = EXCLUDED.embedding_model,
                            embedding_dim = EXCLUDED.embedding_dim,
                            updated_at = now()
                        """,
                        (
                            document.source_id,
                            document.source_file,
                            document.sha256,
                            document.page_count,
                            embedding_model,
                            self.embedding_dim,
                        ),
                    )
                    cur.execute(
                        "DELETE FROM rag_document_chunks WHERE source_id = %s",
                        (document.source_id,),
                    )
                    cur.execute(
                        "DELETE FROM rag_document_images WHERE source_id = %s",
                        (document.source_id,),
                    )

                    cur.executemany(
                        """
                        INSERT INTO rag_document_chunks (
                            source_id, source_file, page_number, chunk_index,
                            content, metadata, embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            (
                                chunk.source_id,
                                chunk.source_file,
                                chunk.page_number,
                                chunk.chunk_index,
                                chunk.content,
                                Jsonb(chunk.metadata),
                                np.asarray(vector, dtype=np.float32),
                            )
                            for chunk, vector in zip(
                                document.chunks, embeddings, strict=True
                            )
                        ],
                    )

                    if document.images:
                        cur.executemany(
                            """
                            INSERT INTO rag_document_images (
                                source_id, source_file, page_number, image_index,
                                mime_type, image_bytes, width, height, sha256,
                                metadata, embedding
                            )
                            VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            """,
                            [
                                (
                                    image.source_id,
                                    image.source_file,
                                    image.page_number,
                                    image.image_index,
                                    image.mime_type,
                                    image.image_bytes,
                                    image.width,
                                    image.height,
                                    image.sha256,
                                    Jsonb(image.metadata),
                                    (
                                        np.asarray(image_vector, dtype=np.float32)
                                        if image_vector is not None
                                        else None
                                    ),
                                )
                                for image, image_vector in zip(
                                    document.images,
                                    image_embeddings,
                                    strict=True,
                                )
                            ],
                        )

    def search(
        self,
        query: str,
        query_vector: list[float] | None,
        *,
        top_k: int,
        candidate_k: int,
    ) -> list[SearchHit]:
        query_arr = np.asarray(query_vector, dtype=np.float32)
        by_id: dict[int, dict[str, object]] = {}

        vector_sql = """
            SELECT
                id, source_id, source_file, page_number, chunk_index,
                content, metadata,
                1 - (embedding <=> %s) AS vector_score,
                similarity(content, %s) AS lexical_score
            FROM rag_document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        lexical_sql = """
            SELECT
                id, source_id, source_file, page_number, chunk_index,
                content, metadata,
                1 - (embedding <=> %s) AS vector_score,
                similarity(content, %s) AS lexical_score
            FROM rag_document_chunks
            WHERE embedding IS NOT NULL
            ORDER BY similarity(content, %s) DESC
            LIMIT %s
        """

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    vector_sql,
                    (query_arr, query, query_arr, candidate_k),
                )
                rows = cur.fetchall()
                for vector_rank, row in enumerate(rows, start=1):
                    by_id[int(row[0])] = {
                        "row": row,
                        "vector_rank": vector_rank,
                        "lexical_rank": None,
                    }

                cur.execute(
                    lexical_sql,
                    (query_arr, query, query, candidate_k),
                )
                for lexical_rank, row in enumerate(cur.fetchall(), start=1):
                    item = by_id.setdefault(
                        int(row[0]),
                        {
                            "row": row,
                            "vector_rank": None,
                            "lexical_rank": None,
                        },
                    )
                    item["lexical_rank"] = lexical_rank

        hits: list[SearchHit] = []
        for item in by_id.values():
            row = item["row"]
            vector_score = float(row[7] or 0.0)
            lexical_score = float(row[8] or 0.0)
            raw_score = 0.88 * vector_score + 0.12 * lexical_score

            vector_rank = item["vector_rank"]
            lexical_rank = item["lexical_rank"]
            rrf_bonus = 0.0
            if vector_rank is not None:
                rrf_bonus += 1.0 / (60.0 + float(vector_rank))
            if lexical_rank is not None:
                rrf_bonus += 1.0 / (60.0 + float(lexical_rank))

            score = raw_score + 0.02 * rrf_bonus
            metadata = row[6] if isinstance(row[6], dict) else {}

            hits.append(
                SearchHit(
                    source_id=str(row[1]),
                    source_file=str(row[2]),
                    page_number=int(row[3]),
                    chunk_index=int(row[4]),
                    content=str(row[5]),
                    score=score,
                    vector_score=vector_score,
                    lexical_score=lexical_score,
                    metadata=metadata,
                )
            )

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]

    def images_for_pages(
        self, pages: list[int], *, limit: int = 3
    ) -> list[ExtractedImage]:
        if not pages or limit <= 0:
            return []

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        source_id, source_file, page_number, image_index,
                        mime_type, image_bytes, width, height, sha256, metadata
                    FROM rag_document_images
                    WHERE page_number = ANY(%s)
                    ORDER BY page_number, image_index
                    LIMIT %s
                    """,
                    (pages, limit),
                )
                rows = cur.fetchall()

        return [
            ExtractedImage(
                source_id=str(row[0]),
                source_file=str(row[1]),
                page_number=int(row[2]),
                image_index=int(row[3]),
                mime_type=str(row[4]),
                image_bytes=bytes(row[5]),
                width=row[6],
                height=row[7],
                sha256=str(row[8] or ""),
                metadata=row[9] if isinstance(row[9], dict) else {},
            )
            for row in rows
        ]

    def log_retrieval(
        self,
        *,
        query: str,
        elapsed_ms: float,
        hits: list[SearchHit],
    ) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rag_retrieval_logs (
                            query_text, elapsed_ms, top_score, hit_pages, hit_scores
                        )
                        VALUES (%s, %s, %s, %s::jsonb, %s::jsonb)
                        """,
                        (
                            query,
                            elapsed_ms,
                            hits[0].score if hits else 0.0,
                            json.dumps([h.page_number for h in hits]),
                            json.dumps([round(h.score, 6) for h in hits]),
                        ),
                    )
                conn.commit()
        except Exception:
            return None

    def log_answer(
        self,
        *,
        query: str,
        retrieval_ms: float,
        ttft_ms: float,
        total_ms: float,
        top_score: float,
        answered: bool,
        model_name: str,
        pages: list[int],
        answer_chars: int,
    ) -> None:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rag_answer_logs (
                            query_text, retrieval_ms, ttft_ms, total_ms,
                            top_score, answered, model_name, hit_pages,
                            answer_chars
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (
                            query,
                            retrieval_ms,
                            ttft_ms,
                            total_ms,
                            top_score,
                            answered,
                            model_name,
                            json.dumps(pages),
                            answer_chars,
                        ),
                    )
                conn.commit()
        except Exception:
            return None

    def get_or_create_profile(self, display_name: str) -> dict[str, str] | None:
        name = unicodedata.normalize("NFKC", display_name).strip()
        normalized = _normalize_display_name(name)
        if not normalized:
            return None

        candidate_id = str(uuid4())
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rag_user_profiles (
                        user_id, display_name, normalized_name, last_seen_at
                    )
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (normalized_name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        last_seen_at = now()
                    RETURNING user_id, display_name
                    """,
                    (candidate_id, name, normalized),
                )
                row = cur.fetchone()
            conn.commit()

        if not row:
            return None
        return {"user_id": str(row[0]), "display_name": str(row[1])}

    def get_recent_questions(
        self, user_id: str, *, limit: int = 6
    ) -> list[str]:
        if not user_id or limit <= 0:
            return []

        fetch_limit = max(limit * 3, limit)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT m.content
                    FROM rag_chat_messages AS m
                    JOIN rag_chat_sessions AS s
                      ON s.session_id = m.session_id
                    WHERE s.user_id = %s
                      AND m.role = 'user'
                    ORDER BY m.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, fetch_limit),
                )
                rows = cur.fetchall()

        seen: set[str] = set()
        questions: list[str] = []
        for row in rows:
            question = str(row[0]).strip()
            key = question.casefold()
            if not question or key in seen:
                continue
            seen.add(key)
            questions.append(question)
            if len(questions) >= limit:
                break
        return questions

    def save_exchange(
        self,
        *,
        user_id: str,
        session_id: str,
        question: str,
        answer: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if not user_id or not session_id:
            return

        from psycopg.types.json import Jsonb

        payload = metadata or {}
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO rag_chat_sessions (
                            session_id, user_id, last_seen_at
                        )
                        VALUES (%s, %s, now())
                        ON CONFLICT (session_id) DO UPDATE SET
                            user_id = EXCLUDED.user_id,
                            last_seen_at = now()
                        """,
                        (session_id, user_id),
                    )
                    cur.executemany(
                        """
                        INSERT INTO rag_chat_messages (
                            session_id, role, content, metadata
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        [
                            (session_id, "user", question, Jsonb(payload)),
                            (session_id, "assistant", answer, Jsonb(payload)),
                        ],
                    )
                conn.commit()
        except Exception:
            # History persistence is best-effort and must never delay/fail tutoring.
            return None
