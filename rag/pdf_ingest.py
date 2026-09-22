from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentChunk, ExtractedImage, ParsedDocument


_WHITESPACE = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_TOPIC_PREFIX = re.compile(r"^(\d+)\.")
_SOURCE_STEM = re.compile(r"^(?P<number>\d+)\.(?P<title>.+?)(?:-(?P<part>\d+))?$")


def _source_identity_from_filename(filename: str) -> dict[str, object]:
    stem = Path(filename).stem
    match = _SOURCE_STEM.match(stem)
    if not match:
        return {
            "topic_id": "topic-unclassified",
            "topic_name": "",
            "source_part": None,
        }

    return {
        "topic_id": f"topic-{int(match.group('number')):02d}",
        "topic_name": match.group("title").strip(),
        "source_part": (
            int(match.group("part"))
            if match.group("part") is not None
            else None
        ),
    }


def _topic_id_from_filename(filename: str) -> str:
    return str(_source_identity_from_filename(filename)["topic_id"])


def _real_data_root(path: Path) -> Path | None:
    for candidate in (path.parent, *path.parents):
        if candidate.name == "real_data":
            return candidate
    return None


def _load_source_manifest(
    path: Path,
    *,
    topic_id: str,
    sha256: str,
) -> dict[str, object]:
    real_data_root = _real_data_root(path)
    if real_data_root is None:
        return {}

    manifest_path = real_data_root / f"{topic_id.replace('-', '_')}_manifest.json"
    if not manifest_path.exists():
        return {}

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("topic_id") != topic_id:
        raise RuntimeError(
            f"Manifest topic mismatch for {path.name}: {manifest_path.name}"
        )
    if data.get("closed_source") is not True:
        raise RuntimeError(
            f"Manifest must enforce closed_source=true: {manifest_path.name}"
        )

    source = data.get("sources", {}).get(path.name)
    if not isinstance(source, dict):
        return {}

    expected_hash = str(source.get("sha256") or "")
    if expected_hash and expected_hash != sha256:
        raise RuntimeError(
            f"Manifest hash mismatch for {path.name}; "
            "audit/update the manifest before ingesting this revision"
        )

    pages = source.get("pages", {})
    return {
        "manifest_file": manifest_path.name,
        "topic_name": str(data.get("topic_name") or ""),
        "knowledge_scope": str(data.get("knowledge_scope") or "real_data"),
        "language": str(source.get("language") or ""),
        "pages": pages if isinstance(pages, dict) else {},
    }


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


_FIGURE_CAPTION = re.compile(
    r"^\s*(?:รูปที่|figure|fig\.?)\s*\d",
    re.IGNORECASE,
)


def _figure_clips(page) -> list[tuple[object, str]]:
    clips: list[tuple[object, str]] = []
    drawings = [drawing.get("rect") for drawing in page.get_drawings()]
    drawings = [rect for rect in drawings if rect is not None]

    for block in page.get_text("blocks"):
        caption = " ".join(str(block[4]).split())
        if not _FIGURE_CAPTION.search(caption):
            continue

        caption_y = float(block[1])
        band_top = max(0.0, caption_y - 280.0)
        candidates = [
            rect
            for rect in drawings
            if rect.width >= 120
            and rect.height >= 45
            and rect.y0 >= band_top
            and rect.y1 <= caption_y + 8
        ]
        if not candidates:
            continue

        figure_rect = max(
            candidates,
            key=lambda rect: rect.width * rect.height,
        )
        padding = 8.0
        clip = page.rect & type(figure_rect)(
            figure_rect.x0 - padding,
            figure_rect.y0 - padding,
            figure_rect.x1 + padding,
            figure_rect.y1 + padding,
        )
        if clip.width >= 140 and clip.height >= 55:
            clips.append((clip, caption))

    return clips


def _extract_images_with_pymupdf(
    pdf_path: Path,
    source_id: str,
    *,
    source_metadata: dict[str, object],
    page_metadata: dict[int, dict[str, object]],
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
            page_number = page_idx + 1
            visual_metadata = {
                **source_metadata,
                **page_metadata.get(page_number, {}),
            }
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
                        page_number=page_number,
                        image_index=image_idx,
                        mime_type=mime,
                        image_bytes=image_bytes,
                        width=width or None,
                        height=height or None,
                        sha256=image_hash,
                        metadata={
                            **visual_metadata,
                            "kind": "embedded_image",
                            "source_only": True,
                        },
                    )
                )

            figure_clips = _figure_clips(page) if render_vector_pages else []
            for figure_idx, (clip, caption) in enumerate(figure_clips, start=1):
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2.0, 2.0),
                    clip=clip,
                    alpha=False,
                )
                figure_bytes = pix.tobytes("png")
                figure_hash = hashlib.sha256(figure_bytes).hexdigest()
                if figure_hash in seen_hashes:
                    continue
                seen_hashes.add(figure_hash)
                images.append(
                    ExtractedImage(
                        source_id=source_id,
                        source_file=pdf_path.name,
                        page_number=page_number,
                        image_index=1000 + figure_idx,
                        mime_type="image/png",
                        image_bytes=figure_bytes,
                        width=pix.width,
                        height=pix.height,
                        sha256=figure_hash,
                        metadata={
                            **visual_metadata,
                            "kind": "figure_crop",
                            "caption": caption,
                            "clip": [
                                round(float(clip.x0), 2),
                                round(float(clip.y0), 2),
                                round(float(clip.x1), 2),
                                round(float(clip.y1), 2),
                            ],
                            "source_only": True,
                        },
                    )
                )

            # Full-page rendering is only a fallback when no figure region
            # could be isolated from the source page.
            if render_vector_pages and page.get_drawings() and not figure_clips:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                page_bytes = pix.tobytes("png")
                page_hash = hashlib.sha256(page_bytes).hexdigest()
                if page_hash not in seen_hashes:
                    seen_hashes.add(page_hash)
                    images.append(
                        ExtractedImage(
                            source_id=source_id,
                            source_file=pdf_path.name,
                            page_number=page_number,
                            image_index=0,
                            mime_type="image/png",
                            image_bytes=page_bytes,
                            width=pix.width,
                            height=pix.height,
                            sha256=page_hash,
                            metadata={
                                **visual_metadata,
                                "kind": "vector_page_render",
                                "source_only": True,
                            },
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
    identity = _source_identity_from_filename(path.name)
    topic_id = str(identity["topic_id"])
    manifest = _load_source_manifest(
        path,
        topic_id=topic_id,
        sha256=sha256,
    )
    manifest_pages = manifest.get("pages", {})
    page_metadata = {
        int(page_number): metadata
        for page_number, metadata in (
            manifest_pages.items()
            if isinstance(manifest_pages, dict)
            else []
        )
        if str(page_number).isdigit() and isinstance(metadata, dict)
    }
    source_metadata = {
        **identity,
        "source_sha256": sha256,
        "knowledge_scope": "real_data",
        "source_only": True,
        **{
            key: value
            for key, value in manifest.items()
            if key != "pages"
        },
    }

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
                        **source_metadata,
                        **page_metadata.get(page_idx, {}),
                        "page": page_idx,
                        "physical_page": page_idx,
                        "chunk_index": chunk_idx,
                        "source_only": True,
                    },
                )
            )

    images = (
        _extract_images_with_pymupdf(
            path,
            source_id,
            source_metadata=source_metadata,
            page_metadata=page_metadata,
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
