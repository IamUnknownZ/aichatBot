from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    generation_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    multimodal_embedding_model: str = "gemini-embedding-2"
    embedding_dim: int = 768
    database_url: str = ""

    course_title: str = "อัลกอริทึมการเรียงลำดับข้อมูล"
    course_level: str = "มหาวิทยาลัยปีที่ 1"
    tutor_name: str = "Sorty"
    mascot_emoji: str = "✦"
    profile_enabled: bool = True
    recent_question_limit: int = 6

    top_k: int = 5
    candidate_k: int = 18
    min_relevance_score: float = 0.42
    chunk_chars: int = 1200
    chunk_overlap: int = 180
    history_messages: int = 6

    extract_images: bool = False
    render_vector_pages: bool = False
    index_images: bool = False
    max_images_per_answer: int = 3
    auto_ingest: bool = False
    allow_memory_fallback: bool = False

    @classmethod
    def from_env(
        cls,
        *,
        api_key: str | None = None,
        database_url: str | None = None,
        generation_model: str | None = None,
    ) -> "Settings":
        return cls(
            gemini_api_key=(api_key or os.getenv("GEMINI_API_KEY", "")).strip(),
            generation_model=(
                generation_model
                or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
            ).strip(),
            embedding_model=os.getenv(
                "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
            ).strip(),
            multimodal_embedding_model=os.getenv(
                "GEMINI_MULTIMODAL_EMBEDDING_MODEL",
                "gemini-embedding-2",
            ).strip(),
            embedding_dim=_env_int("RAG_EMBEDDING_DIM", 768),
            database_url=(
                database_url
                if database_url is not None
                else os.getenv("DATABASE_URL", "")
            ).strip(),
            course_title=os.getenv(
                "COURSE_TITLE", "อัลกอริทึมการเรียงลำดับข้อมูล"
            ).strip(),
            course_level=os.getenv(
                "COURSE_LEVEL", "มหาวิทยาลัยปีที่ 1"
            ).strip(),
            tutor_name=os.getenv("TUTOR_NAME", "Sorty").strip(),
            mascot_emoji=os.getenv("MASCOT_EMOJI", "✦").strip() or "✦",
            profile_enabled=_env_bool("PROFILE_ENABLED", True),
            recent_question_limit=max(
                0, _env_int("RECENT_QUESTION_LIMIT", 6)
            ),
            top_k=max(1, _env_int("RAG_TOP_K", 5)),
            candidate_k=max(5, _env_int("RAG_CANDIDATE_K", 18)),
            min_relevance_score=_env_float("RAG_MIN_SCORE", 0.42),
            chunk_chars=max(400, _env_int("RAG_CHUNK_CHARS", 1200)),
            chunk_overlap=max(0, _env_int("RAG_CHUNK_OVERLAP", 180)),
            history_messages=max(0, _env_int("RAG_HISTORY_MESSAGES", 6)),
            extract_images=_env_bool("RAG_EXTRACT_IMAGES", False),
            render_vector_pages=_env_bool("RAG_RENDER_VECTOR_PAGES", False),
            index_images=_env_bool("RAG_INDEX_IMAGES", False),
            max_images_per_answer=max(
                0, _env_int("RAG_MAX_IMAGES_PER_ANSWER", 3)
            ),
            auto_ingest=_env_bool("RAG_AUTO_INGEST", False),
            allow_memory_fallback=_env_bool("RAG_ALLOW_MEMORY_FALLBACK", False),
        )
