from __future__ import annotations

import hashlib
import re
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentChunk, ExtractedImage, ParsedDocument


_WHITESPACE = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = _WHITESPACE.sub(" ", text)
    text = _MANY_NEWLINES.sub("\n\n", text)
    return text.strip()


def _split_long_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    parts: list[str] = []
    start = 0
    while start < len(text):
        stop = min(len(text), start + chunk_size)

        if stop < len(text):
            boundary = max(
                text.rfind("\n", start + chunk_size // 2, stop),
                text.rfind("。", start + chunk_size // 2, stop),
                text.rfind(".", start + chunk_size // 2, stop),
                text.rfind(" ", start + chunk_size // 2, stop),
            )
            if boundary > start:
                stop = boundary + 1

        piece = text[start:stop].strip()
        if piece:
            parts.append(piece)

        if stop >= len(text):
            break
        start = max(start + 1, stop - overlap)

    return parts


def split_page_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []

    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_text(paragraph, chunk_size, overlap))
            continue

        candidate = paragraph if not current else f"{current}\n\n{paragraph}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{paragraph}".strip()
            if len(current) > chunk_size:
                overflow_parts = _split_long_text(current, chunk_size, overlap)
                chunks.extend(overflow_parts[:-1])
                current = overflow_parts[-1] if overflow_parts else ""
        else:
            current = paragraph

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _extract_images_with_pymupdf(
    pdf_path: Path,
    source_id: str,
    *,
    min_width: int = 180,
    min_height: int = 120,
    render_vector_pages: bool = False,
) -> list[ExtractedImage]:
    try:
        import pymupdf
    except ImportError:
        return []

    fitz = pymupdf

    images: list[ExtractedImage] = []
    seen_hashes: set[str] = set()

    doc = fitz.open(pdf_path)
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            for image_idx, image_info in enumerate(page.get_images(full=True), start=1):
                xref = image_info[0]
                extracted = doc.extract_image(xref)
                image_bytes = extracted.get("image", b"")
                if not image_bytes:
                    continue

                width = int(extracted.get("width") or 0)
                height = int(extracted.get("height") or 0)
                if width < min_width or height < min_height:
                    continue

                image_hash = hashlib.sha256(image_bytes).hexdigest()
                if image_hash in seen_hashes:
                    continue
                seen_hashes.add(image_hash)

                ext = (extracted.get("ext") or "png").lower()
                mime = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "webp": "image/webp",
                }.get(ext, f"image/{ext}")

                images.append(
                    ExtractedImage(
                        source_id=source_id,
                        source_file=pdf_path.name,
                        page_number=page_idx + 1,
                        image_index=image_idx,
                        mime_type=mime,
                        image_bytes=image_bytes,
                        width=width or None,
                        height=height or None,
                        sha256=image_hash,
                        metadata={"kind": "embedded_image"},
                    )
                )

            if render_vector_pages and page.get_drawings():
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                page_bytes = pix.tobytes("png")
                page_hash = hashlib.sha256(page_bytes).hexdigest()
                if page_hash not in seen_hashes:
                    seen_hashes.add(page_hash)
                    images.append(
                        ExtractedImage(
                            source_id=source_id,
                            source_file=pdf_path.name,
                            page_number=page_idx + 1,
                            image_index=0,
                            mime_type="image/png",
                            image_bytes=page_bytes,
                            width=pix.width,
                            height=pix.height,
                            sha256=page_hash,
                            metadata={"kind": "vector_page_render"},
                        )
                    )
    finally:
        doc.close()

    return images


def parse_pdf(
    pdf_path: str | Path,
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
    extract_images: bool = False,
    render_vector_pages: bool = False,
) -> ParsedDocument:
    path = Path(pdf_path).expanduser().resolve()
    raw_bytes = path.read_bytes()
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    source_id = sha256

    reader = PdfReader(path)
    chunks: list[DocumentChunk] = []

    for page_idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        page_chunks = split_page_text(text, chunk_size, overlap)
        for chunk_idx, content in enumerate(page_chunks):
            chunks.append(
                DocumentChunk(
                    source_id=source_id,
                    source_file=path.name,
                    page_number=page_idx,
                    chunk_index=chunk_idx,
                    content=content,
                    metadata={
                        "page": page_idx,
                        "chunk_index": chunk_idx,
                        "source_sha256": sha256,
                    },
                )
            )

    images = (
        _extract_images_with_pymupdf(
            path,
            source_id,
            render_vector_pages=render_vector_pages,
        )
        if extract_images or render_vector_pages
        else []
    )

    return ParsedDocument(
        source_id=source_id,
        source_file=path.name,
        sha256=sha256,
        page_count=len(reader.pages),
        chunks=chunks,
        images=images,
    )
