from __future__ import annotations

from typing import Any

from .models import ExtractedImage


def display_image_label(metadata: dict[str, Any], index: int) -> str:
    """Return the reviewed label while retaining the source caption separately."""
    return str(
        metadata.get("label")
        or metadata.get("caption")
        or f"ภาพ {index}"
    )


def compact_image_caption(
    metadata: dict[str, Any],
    *,
    page_number: int | str,
    index: int,
) -> str:
    """Return a short label suitable for a compact image preview card."""
    return f"{display_image_label(metadata, index)} · หน้า {page_number}"


def image_preview_groups(
    images: list[dict[str, Any]],
    *,
    columns: int = 3,
) -> list[list[dict[str, Any]]]:
    """Pack image payloads into ordered rows for a small preview grid."""
    columns = max(1, int(columns))
    return [images[start : start + columns] for start in range(0, len(images), columns)]


def image_message_payload(
    images: list[ExtractedImage],
) -> list[dict[str, Any]]:
    """Keep selected visuals available when Streamlit reruns the script."""
    return [
        {
            "source_id": image.source_id,
            "source_file": image.source_file,
            "page_number": image.page_number,
            "image_index": image.image_index,
            "mime_type": image.mime_type,
            "image_bytes": image.image_bytes,
            "width": image.width,
            "height": image.height,
            "sha256": image.sha256,
            "metadata": dict(image.metadata),
        }
        for image in images
    ]
