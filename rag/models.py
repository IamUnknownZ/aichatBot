from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    source_id: str
    source_file: str
    page_number: int
    chunk_index: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedImage:
    source_id: str
    source_file: str
    page_number: int
    image_index: int
    mime_type: str
    image_bytes: bytes
    width: int | None = None
    height: int | None = None
    sha256: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParsedDocument:
    source_id: str
    source_file: str
    sha256: str
    page_count: int
    chunks: list[DocumentChunk]
    images: list[ExtractedImage]


@dataclass(frozen=True)
class SearchHit:
    source_id: str
    source_file: str
    page_number: int
    chunk_index: int
    content: str
    score: float
    vector_score: float
    lexical_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    retrieval_query: str
    hits: list[SearchHit]
    elapsed_ms: float

    @property
    def top_score(self) -> float:
        return self.hits[0].score if self.hits else 0.0

    @property
    def pages(self) -> list[int]:
        seen: set[int] = set()
        pages: list[int] = []
        for hit in self.hits:
            if hit.page_number not in seen:
                seen.add(hit.page_number)
                pages.append(hit.page_number)
        return pages
