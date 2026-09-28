from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import Settings
from .embeddings import GeminiEmbedder
from .pdf_ingest import parse_source
from .service import RAGService
from .store import LocalLexicalStore, PgVectorStore


def _approved_source_names(real_data_dir: Path) -> set[str]:
    names: set[str] = set()
    for manifest_path in sorted(real_data_dir.glob("*_manifest.json")):
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if data.get("closed_source") is not True:
            continue
        sources = data.get("sources", {})
        if isinstance(sources, dict):
            names.update(str(name) for name in sources)
    return names


def resolve_source_paths(project_root: str | Path | None = None) -> list[Path]:
    """Return only manifest-approved source files in real_data/."""
    root = (
        Path(project_root).resolve()
        if project_root is not None
        else Path(__file__).resolve().parents[1]
    )
    real_data_dir = root / "real_data"
    if not real_data_dir.exists():
        raise FileNotFoundError(
            "ไม่พบโฟลเดอร์ real_data/ ซึ่งเป็นฐานความรู้จริงของระบบ"
        )

    approved_names = _approved_source_names(real_data_dir)
    source_paths = sorted(
        (
            path
            for path in real_data_dir.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".pdf", ".pages"}
            and path.name in approved_names
        ),
        key=lambda path: path.relative_to(real_data_dir).as_posix().casefold(),
    )
    if not source_paths:
        raise FileNotFoundError(
            "ไม่พบ source ที่ได้รับอนุมัติใน manifest ของ real_data/ "
            "ระบบจะไม่ fallback ไปใช้ข้อมูลทดลอง"
        )
    return source_paths


def resolve_pdf_paths(project_root: str | Path | None = None) -> list[Path]:
    """Return only approved PDF sources for backwards-compatible callers."""
    return [
        path
        for path in resolve_source_paths(project_root)
        if path.suffix.lower() == ".pdf"
    ]


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for block in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_document(source_path: Path, settings: Settings):
    document = parse_source(
        source_path,
        chunk_size=settings.chunk_chars,
        overlap=settings.chunk_overlap,
        extract_images=settings.extract_images,
        render_vector_pages=settings.render_vector_pages,
    )
    if not document.chunks:
        raise RuntimeError(
            f"source ไม่มีข้อความที่สามารถสร้าง RAG index ได้: {source_path.name}"
        )
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
    require_database: bool = False,
) -> RAGService:
    if not settings.gemini_api_key:
        raise ValueError("ยังไม่ได้ตั้งค่า GEMINI_API_KEY")

    source_paths = resolve_source_paths(project_root)
    source_ids = [_file_sha256(path) for path in source_paths]

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
                allowed_source_ids=source_ids,
            )
            store.ensure_schema()

            indexed = {
                source_id: store.has_document(source_id)
                for source_id in source_ids
            }
            missing_paths = [
                path
                for path, source_id in zip(source_paths, source_ids, strict=True)
                if force_reindex or not indexed[source_id]
            ]

            if not missing_paths:
                return RAGService(
                    settings=settings,
                    embedder=embedder,
                    store=store,
                    startup_note=startup_note,
                )

            if not settings.auto_ingest and not force_reindex:
                missing_names = ", ".join(path.name for path in missing_paths)
                raise RuntimeError(
                    "ยังไม่มี index ของเอกสาร real_data บางไฟล์ใน PostgreSQL "
                    f"({missing_names}) และ RAG_AUTO_INGEST=false"
                )

            for source_path in missing_paths:
                document = _parse_document(source_path, settings)
                embeddings = embedder.embed_texts(
                    [chunk.content for chunk in document.chunks],
                    task_type="RETRIEVAL_DOCUMENT",
                )
                image_embeddings = _index_images(
                    embedder,
                    document,
                    settings.index_images,
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
            if require_database:
                raise RuntimeError(
                    "PostgreSQL/pgvector ใช้งานไม่ได้ — "
                    "production จะไม่ fallback ไป local lexical RAG"
                ) from exc
            startup_note = (
                "PostgreSQL/pgvector ยังไม่พร้อม จึงใช้ local lexical RAG "
                "จาก real_data/ เท่านั้น "
                f"({type(exc).__name__})"
            )
    else:
        if require_database:
            raise RuntimeError(
                "DATABASE_URL จำเป็นสำหรับ Streamlit production; "
                "ปิดการ fallback ไป local lexical RAG แล้ว"
            )
        startup_note = (
            "ยังไม่ได้ตั้ง DATABASE_URL — ใช้ local lexical RAG ชั่วคราว "
            "โดยอ่านเฉพาะเอกสารใน real_data/"
        )

    # Strict fallback: combine only approved real_data PDFs.
    # Never fall back to legacy/demo PDFs or external content.
    chunks = []
    images = []
    for source_path in source_paths:
        document = _parse_document(source_path, settings)
        chunks.extend(document.chunks)
        images.extend(document.images)

    local_store = LocalLexicalStore(chunks, images)
    return RAGService(
        settings=settings,
        embedder=embedder,
        store=local_store,
        startup_note=startup_note,
    )
