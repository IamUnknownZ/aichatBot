from __future__ import annotations

import hashlib
from pathlib import Path

from .config import Settings
from .embeddings import GeminiEmbedder
from .pdf_ingest import parse_pdf
from .service import RAGService
from .store import LocalLexicalStore, MemoryVectorStore, PgVectorStore


def resolve_pdf_path(project_root: str | Path | None = None) -> Path:
    root = (
        Path(project_root).resolve()
        if project_root is not None
        else Path(__file__).resolve().parents[1]
    )
    candidates = [
        root
        / "docs"
        / "อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf",
        root / "อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "ไม่พบไฟล์ PDF ฐานความรู้ใน docs/ หรือโฟลเดอร์หลักของโปรเจกต์"
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_document(pdf_path: Path, settings: Settings):
    document = parse_pdf(
        pdf_path,
        chunk_size=settings.chunk_chars,
        overlap=settings.chunk_overlap,
        extract_images=settings.extract_images,
        render_vector_pages=settings.render_vector_pages,
    )
    if not document.chunks:
        raise RuntimeError("PDF ไม่มีข้อความที่สามารถสร้าง RAG index ได้")
    return document


def _index_images(embedder: GeminiEmbedder, document, enabled: bool):
    if not enabled or not document.images:
        return [None] * len(document.images)

    vectors = []
    for image in document.images:
        try:
            vectors.append(
                embedder.embed_image(image.image_bytes, image.mime_type)
            )
        except Exception:
            vectors.append(None)
    return vectors


def build_rag_service(
    settings: Settings,
    *,
    project_root: str | Path | None = None,
    force_reindex: bool = False,
) -> RAGService:
    if not settings.gemini_api_key:
        raise ValueError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY")

    pdf_path = resolve_pdf_path(project_root)
    embedder = GeminiEmbedder(
        api_key=settings.gemini_api_key,
        text_model=settings.embedding_model,
        multimodal_model=settings.multimodal_embedding_model,
        output_dimensionality=settings.embedding_dim,
    )

    startup_note = ""

    if settings.database_url:
        try:
            store = PgVectorStore(
                settings.database_url,
                embedding_dim=settings.embedding_dim,
            )
            store.ensure_schema()

            # Fast cold-start path: if this exact PDF hash already exists,
            # skip PDF text extraction and all document embedding calls.
            source_id = _file_sha256(pdf_path)
            already_indexed = store.has_document(source_id)

            if already_indexed and not force_reindex:
                return RAGService(
                    settings=settings,
                    embedder=embedder,
                    store=store,
                    startup_note=startup_note,
                )

            if not settings.auto_ingest and not force_reindex:
                raise RuntimeError(
                    "ยังไม่มี index ของ PDF เวอร์ชันนี้ใน PostgreSQL "
                    "และ RAG_AUTO_INGEST=false"
                )

            document = _parse_document(pdf_path, settings)
            embeddings = embedder.embed_texts(
                [chunk.content for chunk in document.chunks],
                task_type="RETRIEVAL_DOCUMENT",
            )
            image_embeddings = _index_images(
                embedder, document, settings.index_images
            )
            store.replace_document(
                document,
                embeddings,
                embedding_model=settings.embedding_model,
                image_embeddings=image_embeddings,
            )

            return RAGService(
                settings=settings,
                embedder=embedder,
                store=store,
                startup_note=startup_note,
            )
        except Exception as exc:
            startup_note = (
                "PostgreSQL/pgvector ยังไม่พร้อม จึงใช้ local lexical RAG "
                f"เพื่อให้แอปยังตอบจากเอกสารได้ ({type(exc).__name__})"
            )
    else:
        startup_note = (
            "ยังไม่ได้ตั้ง DATABASE_URL — ใช้ local lexical RAG ชั่วคราว "
            "โดยไม่สร้าง document embeddings ตอน cold-start"
        )

    # Safe deployment fallback: page-aware retrieval without bulk embedding.
    # This keeps Streamlit responsive and avoids embedding quota spikes.
    document = _parse_document(pdf_path, settings)
    local_store = LocalLexicalStore(
        document.chunks,
        document.images,
    )
    return RAGService(
        settings=settings,
        embedder=embedder,
        store=local_store,
        startup_note=startup_note,
    )
