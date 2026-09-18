"""RAG package for the Streamlit sorting-algorithm tutor."""

from .config import Settings
from .bootstrap import build_rag_service

__all__ = ["Settings", "build_rag_service"]
