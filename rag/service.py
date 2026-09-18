from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter

from google import genai
from google.genai import types

from prompt import PROMPT_SORTING_TUTOR

from .config import Settings
from .embeddings import GeminiEmbedder
from .models import RetrievalResult, SearchHit
from .store import VectorStore


class RAGService:
    def __init__(
        self,
        *,
        settings: Settings,
        embedder: GeminiEmbedder,
        store: VectorStore,
        startup_note: str = "",
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.startup_note = startup_note

    @property
    def store_mode(self) -> str:
        return self.store.mode

    def _retrieval_query(
        self, query: str, history: list[dict[str, str]]
    ) -> str:
        query = query.strip()
        if len(query) >= 70:
            return query

        previous_user = next(
            (
                item.get("content", "").strip()
                for item in reversed(history)
                if item.get("role") == "user"
                and item.get("content", "").strip()
                and item.get("content", "").strip() != query
            ),
            "",
        )
        if previous_user:
            return f"{previous_user}\nคำถามต่อเนื่อง: {query}"
        return query

    def retrieve(
        self, query: str, history: list[dict[str, str]]
    ) -> RetrievalResult:
        retrieval_query = self._retrieval_query(query, history)
        started = perf_counter()
        query_vector = (
            self.embedder.embed_query(retrieval_query)
            if getattr(self.store, "requires_query_embedding", True)
            else None
        )
        hits = self.store.search(
            retrieval_query,
            query_vector,
            top_k=self.settings.top_k,
            candidate_k=self.settings.candidate_k,
        )
        elapsed_ms = (perf_counter() - started) * 1000.0
        return RetrievalResult(
            query=query,
            retrieval_query=retrieval_query,
            hits=hits,
            elapsed_ms=elapsed_ms,
        )

    def answerable(self, result: RetrievalResult) -> bool:
        return bool(result.hits) and (
            result.top_score >= self.settings.min_relevance_score
        )

    def _context_text(self, hits: list[SearchHit]) -> str:
        blocks: list[str] = []
        for idx, hit in enumerate(hits, start=1):
            blocks.append(
                (
                    f"[หลักฐาน {idx} | ไฟล์: {hit.source_file} | "
                    f"หน้า: {hit.page_number} | relevance: {hit.score:.3f}]\n"
                    f"{hit.content}"
                )
            )
        return "\n\n".join(blocks)

    def _history_text(self, history: list[dict[str, str]]) -> str:
        recent = history[-self.settings.history_messages :]
        lines: list[str] = []
        for item in recent:
            role = item.get("role")
            content = item.get("content", "").strip()
            if not content:
                continue
            if role == "user":
                lines.append(f"ผู้ใช้: {content}")
            elif role in {"assistant", "model"}:
                lines.append(f"ผู้ช่วย: {content}")
        return "\n".join(lines)

    @staticmethod
    def _citation_suffix(hits: list[SearchHit]) -> str:
        seen: set[tuple[str, int]] = set()
        refs: list[str] = []
        for hit in hits:
            key = (hit.source_file, hit.page_number)
            if key in seen:
                continue
            seen.add(key)
            refs.append(f"{hit.source_file} หน้า {hit.page_number}")
            if len(refs) >= 4:
                break
        if not refs:
            return ""
        return "\n\n📚 อ้างอิงจากเอกสาร: " + ", ".join(refs)

    def stream_answer(
        self,
        *,
        query: str,
        result: RetrievalResult,
        history: list[dict[str, str]],
        model_name: str | None = None,
    ) -> Iterable[str]:
        if not self.answerable(result):
            yield (
                "ผมยังไม่พบข้อมูลที่เพียงพอในเอกสารที่ใช้เป็นฐานความรู้"
                "สำหรับคำถามนี้ครับ ถ้าต้องการ ลองถามใหม่โดยระบุหัวข้อ"
                "หรือชื่ออัลกอริทึมให้ชัดขึ้น"
            )
            return

        context = self._context_text(result.hits)
        history_text = self._history_text(history)

        payload = f"""
คำถามปัจจุบัน:
{query}

ประวัติการสนทนาล่าสุด (ใช้เพื่อเข้าใจคำถามต่อเนื่องเท่านั้น):
{history_text or "(ไม่มี)"}

หลักฐานจากเอกสารที่ระบบค้นคืนมา:
{context}

ตอบคำถามปัจจุบันโดยยึดเฉพาะหลักฐานข้างต้น
""".strip()

        config = types.GenerateContentConfig(
            system_instruction=PROMPT_SORTING_TUTOR,
            temperature=0.1,
            top_p=0.9,
            max_output_tokens=1400,
        )

        model = model_name or self.settings.generation_model
        for chunk in self.client.models.generate_content_stream(
            model=model,
            contents=payload,
            config=config,
        ):
            text = getattr(chunk, "text", None)
            if text:
                yield text

        suffix = self._citation_suffix(result.hits)
        if suffix:
            yield suffix
