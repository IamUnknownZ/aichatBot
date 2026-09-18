from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter

from google import genai
from google.genai import types

from prompt import PROMPT_SORTING_TUTOR

from .clarifications import (
    TOTAL_CLARIFICATION_ALIASES,
    match_clarification,
)
from .config import Settings
from .embeddings import GeminiEmbedder
from .models import RetrievalResult, SearchHit
from .query_lexicon import (
    TOTAL_ALIASES,
    compact_text as lexicon_compact_text,
    match_alias,
    normalize_text as lexicon_normalize_text,
    primary_thai_alias,
)
from .store import VectorStore


FOLLOW_UP_MARKERS = (
    "แล้ว", "มัน", "ตัวนี้", "อันนี้", "ตัวนั้น", "อันนั้น",
    "เมื่อกี้", "ข้างบน", "ต่างกัน", "ดีกว่า", "ทำไม",
)


def _normalize_text(value: str) -> str:
    return lexicon_normalize_text(value)


def _compact_text(value: str) -> str:
    return lexicon_compact_text(value)


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

    @property
    def lexicon_size(self) -> int:
        return TOTAL_ALIASES

    @property
    def clarification_lexicon_size(self) -> int:
        return TOTAL_CLARIFICATION_ALIASES

    @staticmethod
    def _previous_topic(history: list[dict[str, str]]) -> str | None:
        for item in reversed(history):
            if item.get("role") != "user":
                continue
            content = item.get("content", "").strip()
            if not content:
                continue
            match = match_alias(content, "topics")
            if match is not None:
                return match.canonical
        return None

    def direct_response(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
    ) -> str | None:
        social = match_alias(
            query,
            "social",
            allow_substring=False,
            allow_fuzzy=True,
        )
        if social is not None:
            if social.canonical == "greeting":
                return (
                    "ไงครับ 👋 พร้อมช่วยเรื่อง Sorting Algorithms ครับ "
                    "พิมพ์สั้น ๆ ได้เลย เช่น **บับเบิลซอร์ท**, **Quick Sort** "
                    "หรือถามให้เปรียบเทียบสองอัลกอริทึมก็ได้"
                )

            if social.canonical == "thanks":
                return "ยินดีครับ 🙂 ถ้ามีหัวข้อถัดไป พิมพ์ชื่อสั้น ๆ มาได้เลย"

            if social.canonical == "farewell":
                return "ได้เลยครับ 👋 ไว้กลับมาถามต่อเรื่อง Sorting Algorithms ได้ตลอด"

            if social.canonical == "help":
                return (
                    f"ผมคือ **{self.settings.tutor_name}** ผู้ช่วยเรียนเรื่อง "
                    f"**{self.settings.course_title}** ครับ\n\n"
                    "ลองถามได้หลายแบบ เช่น **บับเบิลซอร์ท**, "
                    "**อธิบาย Quick Sort**, **Selection Sort ต่างจาก Bubble Sort ยังไง** "
                    "หรือ **ช่วย Trace Bubble Sort 5, 1, 4, 2**"
                )

            if social.canonical == "identity":
                return (
                    f"ผมชื่อ **{self.settings.tutor_name}** ครับ เป็น AI Tutor สำหรับ "
                    f"**{self.settings.course_title}**"
                )

        clarification = match_clarification(query)
        if clarification is not None:
            previous_topic = self._previous_topic(history or [])
            if clarification.use_topic_context and previous_topic:
                return None
            return clarification.prompt

        return None

    def _retrieval_query(
        self, query: str, history: list[dict[str, str]]
    ) -> str:
        query = query.strip()

        clarification = match_clarification(query)
        if clarification is not None and clarification.use_topic_context:
            previous_topic = self._previous_topic(history)
            if previous_topic:
                return f"{previous_topic} {query}".strip()

        topic_match = match_alias(query, "topics")
        concept_match = match_alias(query, "concepts")
        action_match = match_alias(query, "actions")

        # Expand clean topic-only or typo-only utterances without an extra LLM call.
        # Example: "บับเบิลซอร์ท" -> a richer standalone retrieval query.
        if topic_match:
            topic = topic_match.canonical
            thai_alias = primary_thai_alias("topics", topic)

            if (
                topic_match.match_type in {"exact", "fuzzy"}
                and concept_match is None
                and action_match is None
            ):
                return (
                    f"{topic} {thai_alias} คืออะไร หลักการทำงาน "
                    "ขั้นตอน ตัวอย่าง การทำงาน"
                ).strip()

            parts = [topic, thai_alias, query]
            if concept_match:
                parts.append(concept_match.canonical)
            if action_match:
                parts.append(action_match.canonical)
            return " ".join(part for part in parts if part).strip()

        # Concept-only utterances such as "บิ๊กโอ" are also expanded into the
        # course domain so lexical/vector retrieval gets enough context.
        if concept_match:
            if concept_match.match_type in {"exact", "fuzzy"}:
                return (
                    f"{concept_match.canonical} sorting algorithms "
                    "อัลกอริทึมการเรียงลำดับ ความหมาย ตัวอย่าง"
                )
            return f"{query} {concept_match.canonical}".strip()

        # Context is added only for genuine follow-up utterances instead of
        # blindly prepending the previous question to every short query.
        normalized = _normalize_text(query)
        should_use_context = (
            len(query) <= 55
            and any(marker in normalized for marker in FOLLOW_UP_MARKERS)
        )

        if should_use_context:
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
        if self.direct_response(query, history):
            return RetrievalResult(
                query=query,
                retrieval_query="__conversation__",
                hits=[],
                elapsed_ms=0.0,
            )

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
        if result.retrieval_query == "__conversation__":
            return True
        if not result.hits:
            return False

        threshold = self.settings.min_relevance_score

        # Short in-domain terms can produce lower lexical similarity than
        # full questions. Relax the gate only when the lexicon strongly
        # recognizes a course topic/concept; unrelated queries keep the
        # original threshold.
        domain_matches = [
            match_alias(result.query, "topics"),
            match_alias(result.query, "concepts"),
        ]
        if any(
            match is not None and match.score >= 0.80
            for match in domain_matches
        ):
            threshold = max(0.30, threshold - 0.10)

        return result.top_score >= threshold

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
        direct_text = self.direct_response(query, history)
        if direct_text:
            yield direct_text
            return

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

        # Citations are rendered as structured UI by Streamlit instead of
        # being appended to the teaching prose. This keeps answers readable
        # while preserving inspectable evidence.
