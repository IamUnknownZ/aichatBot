from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentChunk, ExtractedImage, ParsedDocument


_WHITESPACE = re.compile(r"[ \t]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")
_TOPIC_PREFIX = re.compile(r"^(\d+)\.")
_SOURCE_STEM = re.compile(r"^(?P<number>\d+)\.(?P<title>.+?)(?:-(?P<part>\d+))?$")
_LEGACY_TEXTBOOK_NAME = "เอกสารหน่วยที่ 8 การเรียงลำดับข้อมูล.pdf"
_REFERENCE_ONLY_SECTIONS = {
    "batcher_merge",
    "bucket_sort",
    "cocktail_sort",
    "comparison",
    "comparison_summary",
    "external_sort",
    "heap_merge",
    "lower_bound",
    "performance",
    "performance_heap",
    "quick_sort",
    "radix_sort",
    "shell_sort",
    "sqrt_sort",
}


def _source_identity_from_filename(filename: str) -> dict[str, object]:
    if filename == _LEGACY_TEXTBOOK_NAME:
        return {
            "topic_id": "topic-01",
            "topic_name": "หลักการเรียงลำดับข้อมูล",
            "source_part": None,
        }

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
    manifest_source_path: Path | None = None,
) -> dict[str, object]:
    lookup_path = manifest_source_path or path
    real_data_root = _real_data_root(lookup_path)
    if real_data_root is None:
        return {}

    specific_manifest = real_data_root / f"{topic_id.replace('-', '_')}_manifest.json"
    manifest_paths = (
        [specific_manifest]
        if topic_id != "topic-unclassified"
        else sorted(real_data_root.glob("*_manifest.json"))
    )

    for manifest_path in manifest_paths:
        if not manifest_path.exists():
            continue

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_topic_id = str(data.get("topic_id") or "")
        if topic_id != "topic-unclassified" and manifest_topic_id != topic_id:
            raise RuntimeError(
                f"Manifest topic mismatch for {lookup_path.name}: "
                f"{manifest_path.name}"
            )
        if data.get("closed_source") is not True:
            raise RuntimeError(
                f"Manifest must enforce closed_source=true: {manifest_path.name}"
            )

        sources = data.get("sources", {})
        source = sources.get(lookup_path.name) if isinstance(sources, dict) else None
        if not isinstance(source, dict):
            continue

        expected_hash = str(source.get("sha256") or "")
        if expected_hash and expected_hash != sha256:
            raise RuntimeError(
                f"Manifest hash mismatch for {lookup_path.name}; "
                "audit/update the manifest before ingesting this revision"
            )

        pages = source.get("pages", {})
        result: dict[str, object] = {
            "manifest_file": manifest_path.name,
            "topic_id": manifest_topic_id,
            "topic_name": str(data.get("topic_name") or ""),
            "knowledge_scope": str(data.get("knowledge_scope") or "real_data"),
            "language": str(source.get("language") or ""),
            "pages": pages if isinstance(pages, dict) else {},
        }
        for key in (
            "curriculum_status",
            "source_kind",
            "source_quality",
            "source_origin",
            "approved_for_text",
        ):
            if key in source:
                result[key] = source[key]
        return result

    return {}


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


def _trace_clips(page) -> list[object]:
    rects = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        if rect.y0 < 70 or rect.y1 > page.rect.y1 - 45:
            continue
        if max(rect.width, rect.height) < 16 or min(rect.width, rect.height) < 2.5:
            continue
        if rect.width > page.rect.width * 0.9 and rect.height < 6:
            continue
        rects.append(rect)

    if len(rects) < 5:
        return []

    groups: list[list[object]] = []
    for rect in sorted(rects, key=lambda item: (item.y0, item.x0)):
        if not groups:
            groups.append([rect])
            continue
        group_bottom = max(item.y1 for item in groups[-1])
        if rect.y0 <= group_bottom + 35:
            groups[-1].append(rect)
        else:
            groups.append([rect])

    clips: list[object] = []
    for group in groups:
        if len(group) < 5:
            continue
        x0 = min(rect.x0 for rect in group)
        y0 = min(rect.y0 for rect in group)
        x1 = max(rect.x1 for rect in group)
        y1 = max(rect.y1 for rect in group)
        if x1 - x0 < 180 or y1 - y0 < 25:
            continue

        padding_x = 14.0
        padding_y = 18.0
        clip = page.rect & type(group[0])(
            x0 - padding_x,
            y0 - padding_y,
            x1 + padding_x,
            y1 + padding_y,
        )
        if clip.width * clip.height > page.rect.width * page.rect.height * 0.35:
            continue
        clips.append(clip)

    return clips


def _trace_caption(page, visual_metadata: dict[str, object]) -> str:
    for line in page.get_text().splitlines():
        cleaned = " ".join(line.split()).strip()
        if re.search(
            r"(?:Selection|Insertion|Bubble|Shell|Quick|Merge|Heap|Cocktail|Counting|Radix|Bucket)\s+sort",
            cleaned,
            re.IGNORECASE,
        ):
            return cleaned[:140]

    subtopic = str(visual_metadata.get("subtopic") or "").strip()
    if subtopic:
        return subtopic
    section = str(visual_metadata.get("section") or "").strip()
    if section:
        return section.replace("_", " ").title()
    return f"ภาพขั้นตอนจากหน้า {page.number + 1}"


def _curriculum_status(metadata: dict[str, object]) -> str:
    explicit = str(metadata.get("curriculum_status") or "").strip()
    if explicit:
        return explicit
    section = str(metadata.get("section") or "").strip()
    if section in _REFERENCE_ONLY_SECTIONS:
        return "reference_only"
    return "primary"


def _page_visual_specs(
    visual_metadata: dict[str, object],
    *,
    kind: str,
) -> list[dict[str, object]]:
    raw_specs = visual_metadata.get("visuals")
    if not isinstance(raw_specs, list):
        return []

    specs: list[dict[str, object]] = []
    for raw_spec in raw_specs:
        if not isinstance(raw_spec, dict):
            continue
        spec_kind = str(raw_spec.get("kind") or "").strip()
        if spec_kind and spec_kind != kind:
            continue
        specs.append(raw_spec)
    return specs


def _visual_metadata(
    visual_metadata: dict[str, object],
    *,
    kind: str,
    ordinal: int,
    default_caption: str,
) -> dict[str, object]:
    specs = _page_visual_specs(visual_metadata, kind=kind)
    if ordinal > len(specs):
        return {"caption": default_caption, "label": default_caption}

    spec = specs[ordinal - 1]
    label = str(spec.get("label") or default_caption).strip()
    result: dict[str, object] = {
        "caption": default_caption,
        "label": label,
        "source_caption": default_caption,
    }
    for key in (
        "visual_topic",
        "visual_role",
        "visual_step",
        "visual_steps",
        "visual_detail",
        "sequence_id",
        "curriculum_status",
        "user_visible",
        "source_quality",
        "source_origin",
        "duplicate_of",
    ):
        if key in spec:
            result[key] = spec[key]
    return result


def _manual_clips(
    page,
    visual_metadata: dict[str, object],
    *,
    kind: str,
) -> list[object]:
    specs = _page_visual_specs(visual_metadata, kind=kind)
    if not specs or not all(isinstance(spec.get("clip"), list) for spec in specs):
        return []

    clips: list[object] = []
    rect_type = type(page.rect)
    for spec in specs:
        values = spec["clip"]
        if not isinstance(values, list) or len(values) != 4:
            return []
        try:
            clip = page.rect & rect_type(*(float(value) for value in values))
        except (TypeError, ValueError):
            return []
        if clip.width <= 0 or clip.height <= 0:
            return []
        clips.append(clip)
    return clips


def _extract_images_with_pymupdf(
    pdf_path: Path,
    source_id: str,
    *,
    source_metadata: dict[str, object],
    page_metadata: dict[int, dict[str, object]],
    source_file: str | None = None,
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
    display_source_file = source_file or pdf_path.name

    doc = fitz.open(pdf_path)
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_number = page_idx + 1
            visual_metadata = {
                **source_metadata,
                **page_metadata.get(page_number, {}),
            }
            visual_metadata["curriculum_status"] = _curriculum_status(
                visual_metadata
            )
            if visual_metadata.get("visual_mode") in {"none", "internal_only"}:
                visual_metadata["user_visible"] = False
            for image_idx, image_info in enumerate(page.get_images(full=True), start=1):
                xref = image_info[0]
                if not page.get_image_rects(xref):
                    continue
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
                label_metadata = _visual_metadata(
                    visual_metadata,
                    kind="embedded_image",
                    ordinal=image_idx,
                    default_caption=(
                        f"ภาพจาก {display_source_file} หน้า {page_number}"
                    ),
                )

                images.append(
                    ExtractedImage(
                        source_id=source_id,
                        source_file=display_source_file,
                        page_number=page_number,
                        image_index=image_idx,
                        mime_type=mime,
                        image_bytes=image_bytes,
                        width=width or None,
                        height=height or None,
                        sha256=image_hash,
                        metadata={
                            **visual_metadata,
                            **label_metadata,
                            "kind": "embedded_image",
                            "source_only": True,
                        },
                    )
                )

            figure_clips = []
            if render_vector_pages:
                manual_figure_clips = _manual_clips(
                    page,
                    visual_metadata,
                    kind="figure_crop",
                )
                if manual_figure_clips:
                    figure_clips = [
                        (clip, _trace_caption(page, visual_metadata))
                        for clip in manual_figure_clips
                    ]
                else:
                    figure_clips = _figure_clips(page)
            trace_clips = (
                (
                    _manual_clips(
                        page,
                        visual_metadata,
                        kind="trace_crop",
                    )
                    or _trace_clips(page)
                )
                if render_vector_pages and not figure_clips
                else []
            )
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
                label_metadata = _visual_metadata(
                    visual_metadata,
                    kind="figure_crop",
                    ordinal=figure_idx,
                    default_caption=caption,
                )
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
                            **label_metadata,
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

            trace_caption = _trace_caption(page, visual_metadata)
            for trace_idx, clip in enumerate(trace_clips, start=1):
                pix = page.get_pixmap(
                    matrix=fitz.Matrix(2.0, 2.0),
                    clip=clip,
                    alpha=False,
                )
                trace_bytes = pix.tobytes("png")
                trace_hash = hashlib.sha256(trace_bytes).hexdigest()
                if trace_hash in seen_hashes:
                    continue
                seen_hashes.add(trace_hash)
                label_metadata = _visual_metadata(
                    visual_metadata,
                    kind="trace_crop",
                    ordinal=trace_idx,
                    default_caption=trace_caption,
                )
                images.append(
                    ExtractedImage(
                        source_id=source_id,
                        source_file=pdf_path.name,
                        page_number=page_number,
                        image_index=2000 + trace_idx,
                        mime_type="image/png",
                        image_bytes=trace_bytes,
                        width=pix.width,
                        height=pix.height,
                        sha256=trace_hash,
                        metadata={
                            **visual_metadata,
                            "kind": "trace_crop",
                            **label_metadata,
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

            # Full-page rendering remains internal fallback only when no
            # precise figure/trace region could be isolated.
            if (
                render_vector_pages
                and page.get_drawings()
                and not figure_clips
                and not trace_clips
            ):
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
    source_file_override: str | None = None,
    source_id_override: str | None = None,
    manifest_source_path: str | Path | None = None,
) -> ParsedDocument:
    path = Path(pdf_path).expanduser().resolve()
    raw_bytes = path.read_bytes()
    sha256 = source_id_override or hashlib.sha256(raw_bytes).hexdigest()
    source_id = sha256
    source_file = source_file_override or path.name
    manifest_lookup_path = (
        Path(manifest_source_path).expanduser().resolve()
        if manifest_source_path is not None
        else path
    )
    identity = _source_identity_from_filename(source_file)
    topic_id = str(identity["topic_id"])
    manifest = _load_source_manifest(
        manifest_lookup_path,
        topic_id=topic_id,
        sha256=sha256,
        manifest_source_path=manifest_lookup_path,
    )
    manifest_topic_id = str(manifest.get("topic_id") or "").strip()
    if manifest_topic_id:
        identity["topic_id"] = manifest_topic_id
        identity["topic_name"] = str(
            manifest.get("topic_name") or identity["topic_name"]
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
            chunk_metadata = {
                **source_metadata,
                **page_metadata.get(page_idx, {}),
                "page": page_idx,
                "physical_page": page_idx,
                "chunk_index": chunk_idx,
                "source_only": True,
            }
            chunk_metadata["curriculum_status"] = _curriculum_status(
                chunk_metadata
            )
            chunks.append(
                DocumentChunk(
                    source_id=source_id,
                    source_file=source_file,
                    page_number=page_idx,
                    chunk_index=chunk_idx,
                    content=content,
                    metadata=chunk_metadata,
                )
            )

    images = (
        _extract_images_with_pymupdf(
            path,
            source_id,
            source_metadata=source_metadata,
            page_metadata=page_metadata,
            source_file=source_file,
            render_vector_pages=render_vector_pages,
        )
        if extract_images or render_vector_pages
        else []
    )

    return ParsedDocument(
        source_id=source_id,
        source_file=source_file,
        sha256=sha256,
        page_count=len(reader.pages),
        chunks=chunks,
        images=images,
    )


def _convert_pages_to_pdf(source_path: Path, output_dir: Path) -> Path:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if executable is None:
        raise RuntimeError(
            "ไม่สามารถอ่านไฟล์ .pages ได้: ต้องติดตั้ง LibreOffice "
            "เพื่อแปลงเป็น PDF ชั่วคราว"
        )

    result = subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(source_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    converted = output_dir / f"{source_path.stem}.pdf"
    if result.returncode != 0 or not converted.exists():
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"แปลงไฟล์ .pages ไม่สำเร็จ: {source_path.name}"
            + (f" ({detail})" if detail else "")
        )
    return converted


def parse_source(
    source_path: str | Path,
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
    extract_images: bool = False,
    render_vector_pages: bool = False,
) -> ParsedDocument:
    path = Path(source_path).expanduser().resolve()
    if path.suffix.lower() != ".pages":
        return parse_pdf(
            path,
            chunk_size=chunk_size,
            overlap=overlap,
            extract_images=extract_images,
            render_vector_pages=render_vector_pages,
        )

    source_id = hashlib.sha256(path.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="sorting-pages-") as temp_dir:
        converted = _convert_pages_to_pdf(path, Path(temp_dir))
        return parse_pdf(
            converted,
            chunk_size=chunk_size,
            overlap=overlap,
            extract_images=extract_images,
            render_vector_pages=render_vector_pages,
            source_file_override=path.name,
            source_id_override=source_id,
            manifest_source_path=path,
        )
