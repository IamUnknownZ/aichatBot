from __future__ import annotations

from collections.abc import Iterable
from copy import copy
from dataclasses import replace
import logging
import re
from time import perf_counter

from google import genai
from google.genai import types

from prompt import build_tutor_prompt, resolve_response_language

from .clarifications import (
    TOTAL_CLARIFICATION_ALIASES,
    match_clarification,
)
from .config import Settings
from .embeddings import GeminiEmbedder
from .models import ExtractedImage, RetrievalResult, SearchHit
from .personas import get_persona
from .query_lexicon import (
    PRIMARY_CURRICULUM_TOPICS,
    TOTAL_ALIASES,
    aliases_for,
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

VISUAL_MARKERS = (
    "รูป", "ภาพ", "แผนภาพ", "ไดอะแกรม",
    "image", "picture", "diagram", "visual",
)

GENERAL_SORT_TERMS = (
    "การเรียงลำดับข้อมูล",
    "การจัดเรียงข้อมูล",
    "data sorting",
    "sorting",
)
DEFINITION_MARKERS = (
    "คือ",
    "หมายถึง",
    "ความหมาย",
    "what is",
    "define",
    "definition",
)
PRIMARY_COMPLEXITY_TOPICS = tuple(PRIMARY_CURRICULUM_TOPICS[1:])

logger = logging.getLogger(__name__)


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
        self.persona_id = None

    def for_persona(self, persona_id: str) -> "RAGService":
        """Isolate request identity while sharing immutable indexes/connection pools."""
        from .personas import get_persona
        persona = get_persona(persona_id)
        selected = copy(self)
        selected.settings = replace(self.settings, tutor_name=persona.name)
        selected.persona_id = persona.id
        return selected

    @property
    def thai_statement_particle(self) -> str:
        persona_id = getattr(self, "persona_id", None)
        if not persona_id:
            return "ครับ"
        persona = get_persona(persona_id)
        return persona.thai_statement_particle

    @property
    def thai_first_person(self) -> str:
        persona_id = getattr(self, "persona_id", None)
        return get_persona(persona_id).thai_self_reference if persona_id else "ผม"

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
    def select_user_visible_images(
        images: list[ExtractedImage],
        *,
        limit: int,
        topic: str | None = None,
    ) -> list[ExtractedImage]:
        visible = [
            image
            for image in images
            if (
                image.metadata.get("kind") in {"figure_crop", "trace_crop"}
                or (
                    image.metadata.get("kind") == "embedded_image"
                    and image.metadata.get("user_visible") is True
                )
            )
            and image.metadata.get("curriculum_status") != "reference_only"
            and image.metadata.get("user_visible", True) is not False
        ]
        if not topic:
            return visible[: max(0, limit)]
        return [
            image
            for image in visible
            if RAGService._image_matches_topic(image, topic)
        ][: max(0, limit)]

    @staticmethod
    def topic_from_query(query: str) -> str | None:
        if len(RAGService.topic_targets(query)) >= 2:
            return None
        match = match_alias(query, "topics")
        return match.canonical if match is not None else None

    @staticmethod
    def topic_targets(query: str) -> list[str]:
        """Return every primary sorting topic explicitly named in a query.

        ``match_alias`` intentionally returns one best match for ordinary
        topic queries. Comparison questions need a different contract: all
        named topics must survive retrieval and reranking.
        """
        normalized = _normalize_text(query)
        compact = _compact_text(query)
        targets: list[str] = []
        for topic in PRIMARY_CURRICULUM_TOPICS[1:]:
            candidates = (topic, *aliases_for("topics", topic))
            if any(
                (
                    _normalize_text(alias) in normalized
                    or _compact_text(alias) in compact
                )
                for alias in candidates
                if len(_compact_text(alias)) >= 4
            ):
                targets.append(topic)
        return targets

    @staticmethod
    def visual_topic(
        query: str,
        history: list[dict[str, str]],
    ) -> str | None:
        explicit_topic = RAGService.topic_from_query(query)
        if explicit_topic:
            return explicit_topic

        for item in reversed(history):
            if item.get("role") != "user":
                continue
            content = item.get("content", "").strip()
            if not content:
                continue
            targets = RAGService.topic_targets(content)
            if len(targets) >= 2:
                return None
            if len(targets) == 1:
                return targets[0]
            match = match_alias(content, "topics")
            if match is not None:
                return match.canonical
        return None

    @staticmethod
    def _image_matches_topic(image: ExtractedImage, topic: str) -> bool:
        metadata = image.metadata
        topic_stem = _normalize_text(topic).removesuffix(" sort").strip()
        visual_topic = _normalize_text(str(metadata.get("visual_topic") or ""))
        if visual_topic:
            visual_topic_stem = visual_topic.removesuffix(" sort").strip()
            return topic_stem in {visual_topic, visual_topic_stem}
        section = _normalize_text(str(metadata.get("section") or ""))
        if section:
            return topic_stem in section

        searchable = " ".join(
            str(metadata.get(field) or "")
            for field in ("caption", "subtopic", "label")
        )
        searchable = _normalize_text(searchable)
        mentioned_topics = []
        for candidate in PRIMARY_CURRICULUM_TOPICS[1:]:
            candidate_stem = _normalize_text(candidate).removesuffix(" sort")
            thai_alias = _normalize_text(primary_thai_alias("topics", candidate))
            if (
                _normalize_text(candidate) in searchable
                or candidate_stem in searchable
                or thai_alias in searchable
            ):
                mentioned_topics.append(candidate)

        if mentioned_topics:
            return topic in mentioned_topics
        return True

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

    @staticmethod
    def _previous_user_query(history: list[dict[str, str]]) -> str | None:
        for item in reversed(history):
            if item.get("role") == "user":
                content = item.get("content", "").strip()
                if content:
                    return content
        return None

    def is_visual_request(self, query: str) -> bool:
        clarification = match_clarification(query)
        if clarification is not None and clarification.canonical == "visualize":
            return True
        normalized = _normalize_text(query)
        normalized = normalized.replace("ภาพรวม", "").replace("รูปแบบ", "")
        return any(marker in normalized for marker in VISUAL_MARKERS)

    @staticmethod
    def _asks_primary_topic_list(query: str) -> bool:
        normalized = _normalize_text(query)
        scope_markers = (
            "sorting algorithm",
            "sorting algorithms",
            "อัลกอริทึมการเรียงลำดับ",
            "การเรียงลำดับข้อมูล",
        )
        list_markers = (
            "มีอะไรบ้าง",
            "หัวข้อ",
            "กี่แบบ",
            "กี่ชนิด",
            "ประเภท",
            "which",
            "list",
            "types",
        )
        return (
            any(_normalize_text(marker) in normalized for marker in scope_markers)
            and any(_normalize_text(marker) in normalized for marker in list_markers)
        )

    @staticmethod
    def _asks_complexity_question(query: str) -> bool:
        match = match_alias(query, "concepts")
        return bool(
            match is not None
            and match.canonical == "time complexity Big-O"
        )

    @staticmethod
    def _asks_coursewide_complexity_summary(query: str) -> bool:
        if not RAGService._asks_complexity_question(query):
            return False

        normalized = _normalize_text(query)
        broad_markers = (
            "อัลกอริทึมการเรียงลำดับ",
            "การเรียงลำดับข้อมูล",
            "ในบทเรียน",
            "ในหลักสูตร",
            "ทั้งหมด",
            "ทุกอัลกอริทึม",
            "sorting algorithms",
            "sorting algorithm",
            "all algorithms",
            "in this lesson",
            "in the lesson",
        )
        broad_request = any(
            _normalize_text(marker) in normalized
            for marker in broad_markers
        )
        explicitly_all = any(
            _normalize_text(marker) in normalized
            for marker in ("ทั้งหมด", "ทุกอัลกอริทึม", "all algorithms", "every algorithm")
        )
        return broad_request and (
            not RAGService.topic_targets(query) or explicitly_all
        )

    @staticmethod
    def _complexity_summary_query(query: str) -> str:
        topic_terms: list[str] = []
        for topic in PRIMARY_COMPLEXITY_TOPICS:
            topic_terms.extend((topic, primary_thai_alias("topics", topic)))
        return " ".join(
            [
                query,
                *topic_terms,
                "time complexity Big-O best average worst case",
                "ความซับซ้อนเชิงเวลา กรณีดีที่สุด กรณีเฉลี่ย กรณีแย่ที่สุด",
            ]
        )

    def direct_response(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        language_mode: str = "thai",
    ) -> str | None:
        language = resolve_response_language(language_mode, query)
        persona_id = getattr(self, "persona_id", None)
        persona = get_persona(persona_id) if persona_id else None
        if self._asks_primary_topic_list(query):
            if language == "en":
                topics = (
                    "Data Sorting Fundamentals",
                    "Bubble Sort",
                    "Selection Sort",
                    "Insertion Sort",
                    "Merge Sort",
                    "Counting Sort",
                )
                return (
                    "### Sorting Algorithms in this lesson\n\n"
                    + "\n".join(
                        f"{index}. **{topic}**"
                        for index, topic in enumerate(topics, start=1)
                    )
                )
            return (
                "### หัวข้อการเรียงลำดับข้อมูลในบทเรียน\n\n"
                + "\n".join(
                    f"{index}. **{topic}**"
                    for index, topic in enumerate(PRIMARY_CURRICULUM_TOPICS, start=1)
                )
            )

        non_curriculum = match_alias(query, "non_curriculum_topics")
        if non_curriculum is not None:
            if language == "en":
                return (
                    f"**{non_curriculum.canonical}** is mentioned in some course "
                    "documents, but it is not one of the 6 primary topics.\n\n"
                    "The primary topics are **Data Sorting Fundamentals, Bubble Sort, "
                    "Selection Sort, Insertion Sort, Merge Sort, and Counting Sort**."
                )
            return (
                f"**{non_curriculum.canonical}** ถูกกล่าวถึงในเอกสารบางส่วน "
                f"แต่ไม่ใช่หนึ่งใน 6 หัวข้อหลักของบทเรียนนี้{self.thai_statement_particle}\n\n"
                "หัวข้อหลักคือ **หลักการเรียงลำดับข้อมูล, Bubble Sort, "
                "Selection Sort, Insertion Sort, Merge Sort และ Counting Sort**"
            )

        social = match_alias(
            query,
            "social",
            allow_substring=False,
            allow_fuzzy=True,
        )
        if social is not None:
            if language == "en":
                english_social = {
                    "greeting": (
                        "Hi 👋 I can help with sorting algorithms. Ask about "
                        "Bubble Sort, Counting Sort, or compare two course topics."
                    ),
                    "thanks": "You're welcome 🙂 Ask me about the next topic anytime.",
                    "farewell": "Sure 👋 Come back anytime to continue learning sorting algorithms.",
                    "help": (
                        f"I'm **{self.settings.tutor_name}**, your AI Tutor for "
                        f"**{self.settings.course_title}**.\n\n"
                        "Try asking about **Bubble Sort**, **Counting Sort**, "
                        "a comparison, or a step-by-step trace."
                    ),
                    "identity": (
                        f"I'm **{self.settings.tutor_name}**, an AI Tutor for "
                        f"**{self.settings.course_title}**."
                    ),
                }
                response = english_social.get(social.canonical)
                if response:
                    return response
            if social.canonical == "greeting":
                if persona and persona.thai_self_reference == "ฉัน":
                    return (
                        "สวัสดีค่ะ 👋 พร้อมช่วยเรื่องการเรียงลำดับข้อมูลค่ะ "
                        "พิมพ์สั้น ๆ ได้เลย เช่น **บับเบิลซอร์ท**, **Counting Sort** "
                        "หรือถามให้เปรียบเทียบหัวข้อในบทเรียนก็ได้ค่ะ"
                    )
                return (
                    "ไงครับ 👋 พร้อมช่วยเรื่องการเรียงลำดับข้อมูลครับ "
                    "พิมพ์สั้น ๆ ได้เลย เช่น **บับเบิลซอร์ท**, **Counting Sort** "
                    "หรือถามให้เปรียบเทียบหัวข้อในบทเรียนก็ได้"
                )

            if social.canonical == "thanks":
                if persona and persona.thai_self_reference == "ฉัน":
                    return "ยินดีค่ะ 🙂 ถ้ามีหัวข้อถัดไป พิมพ์ชื่อสั้น ๆ มาได้เลยค่ะ"
                return "ยินดีครับ 🙂 ถ้ามีหัวข้อถัดไป พิมพ์ชื่อสั้น ๆ มาได้เลย"

            if social.canonical == "farewell":
                if persona and persona.thai_self_reference == "ฉัน":
                    return "ได้เลยค่ะ 👋 ไว้กลับมาถามต่อเรื่อง Sorting Algorithms ได้ตลอดค่ะ"
                return "ได้เลยครับ 👋 ไว้กลับมาถามต่อเรื่อง Sorting Algorithms ได้ตลอด"

            if social.canonical == "help":
                if persona and persona.thai_self_reference == "ฉัน":
                    return (
                        f"ฉันคือ **{self.settings.tutor_name}** ผู้ช่วยเรียนเรื่อง "
                        f"**{self.settings.course_title}** ค่ะ\n\n"
                        "ลองถามได้หลายแบบ เช่น **บับเบิลซอร์ท**, "
                        "**อธิบาย Counting Sort**, **Selection Sort ต่างจาก Bubble Sort ยังไง** "
                        "หรือ **ช่วย Trace Bubble Sort 5, 1, 4, 2**"
                    )
                return (
                    f"ผมคือ **{self.settings.tutor_name}** ผู้ช่วยเรียนเรื่อง "
                    f"**{self.settings.course_title}** ครับ\n\n"
                    "ลองถามได้หลายแบบ เช่น **บับเบิลซอร์ท**, "
                    "**อธิบาย Counting Sort**, **Selection Sort ต่างจาก Bubble Sort ยังไง** "
                    "หรือ **ช่วย Trace Bubble Sort 5, 1, 4, 2**"
                )

            if social.canonical == "identity":
                if persona and persona.thai_self_reference == "ฉัน":
                    return (
                        f"ฉันชื่อ **{self.settings.tutor_name}** ค่ะ เป็น AI Tutor สำหรับ "
                        f"**{self.settings.course_title}**"
                    )
                return (
                    f"ผมชื่อ **{self.settings.tutor_name}** ครับ เป็น AI Tutor สำหรับ "
                    f"**{self.settings.course_title}**"
                )

        clarification = match_clarification(query)
        if clarification is not None:
            prior_history = history or []
            if (
                clarification.canonical == "visualize"
                and self._previous_user_query(prior_history)
            ):
                return None
            previous_topic = self._previous_topic(prior_history)
            if clarification.use_topic_context and previous_topic:
                return None
            if language == "en":
                english_clarifications = {
                    "general_sort": "Which sorting topic would you like to study? For example, Bubble Sort, Selection Sort, Insertion Sort, Merge Sort, or the overall idea of sorting.",
                    "general_algorithm": "Which sorting algorithm do you mean? Please provide its name.",
                    "compare": "Which two algorithms would you like to compare?",
                    "code": "Which algorithm would you like code or pseudocode for?",
                    "trace": "Which algorithm and input data should I trace step by step?",
                    "complexity": "Which algorithm's Time Complexity or Big-O would you like to see?",
                    "visualize": "Which topic would you like to see as a diagram or image?",
                    "summary": "Which topic or algorithm would you like me to summarize?",
                    "explain": "Which topic would you like me to explain?",
                }
                return english_clarifications.get(
                    clarification.canonical,
                    clarification.prompt,
                )
            return clarification.prompt

        return None

    @staticmethod
    def _is_general_sort_definition(query: str) -> bool:
        normalized = _normalize_text(query)
        if match_alias(query, "topics") is not None:
            return False
        return (
            any(
                _normalize_text(term) in normalized
                for term in GENERAL_SORT_TERMS
            )
            and any(
                _normalize_text(marker) in normalized
                for marker in DEFINITION_MARKERS
            )
        )

    def _retrieval_query(
        self, query: str, history: list[dict[str, str]]
    ) -> str:
        query = query.strip()

        if self._asks_coursewide_complexity_summary(query):
            return self._complexity_summary_query(query)

        clarification = match_clarification(query)
        if clarification is not None and clarification.use_topic_context:
            if clarification.canonical == "visualize":
                previous_query = self._previous_user_query(history)
                if previous_query:
                    return previous_query
            previous_topic = self._previous_topic(history)
            if previous_topic:
                return f"{previous_topic} {query}".strip()

        if self.is_visual_request(query):
            visual_subject = _normalize_text(query)
            for marker in VISUAL_MARKERS:
                visual_subject = visual_subject.replace(marker, " ")
            visual_subject = " ".join(visual_subject.split()).strip()
            if visual_subject:
                query = visual_subject

        topic_match = match_alias(query, "topics")
        concept_match = match_alias(query, "concepts")
        action_match = match_alias(query, "actions")

        if self._is_general_sort_definition(query):
            return (
                "การเรียงลำดับข้อมูล การจัดเรียงข้อมูล Data Sorting "
                "ความหมาย คืออะไร จากน้อยไปมาก จากมากไปน้อย"
            )

        topic_targets = self.topic_targets(query)
        if len(topic_targets) >= 2:
            parts: list[str] = []
            for topic in topic_targets:
                parts.extend((topic, primary_thai_alias("topics", topic)))
            parts.extend((query, "comparison", "difference", "เปรียบเทียบ", "ต่างกัน"))
            if concept_match:
                parts.append(concept_match.canonical)
            if action_match:
                parts.append(action_match.canonical)
            return " ".join(part for part in parts if part).strip()

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

    @staticmethod
    def _rerank_topic_hits(
        query: str,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        topic_targets = RAGService.topic_targets(query)
        if len(topic_targets) >= 2:
            target_details = [
                (
                    _normalize_text(topic),
                    _normalize_text(primary_thai_alias("topics", topic)),
                    topic.casefold().replace(" ", "_"),
                )
                for topic in topic_targets
            ]
            target_sections = {detail[2] for detail in target_details}

            def comparison_rank(hit: SearchHit) -> tuple[int, float]:
                content_norm = _normalize_text(hit.content)
                section = str(hit.metadata.get("section") or "").casefold()
                relevance = 0
                for topic_norm, thai_norm, section_key in target_details:
                    relevance += min(content_norm.count(topic_norm), 4) * 2
                    if thai_norm:
                        relevance += min(content_norm.count(thai_norm), 4)
                    if section == section_key:
                        relevance += 4
                if section and section not in target_sections:
                    relevance -= 4
                return (relevance, hit.score)

            ranked = sorted(hits, key=comparison_rank, reverse=True)
            diverse: list[SearchHit] = []
            selected_keys: set[tuple[str, int, int]] = set()
            for topic in topic_targets:
                selected = RAGService._best_topic_hit(topic, ranked)
                if selected is None:
                    continue
                key = RAGService._hit_key(selected)
                if key not in selected_keys:
                    selected_keys.add(key)
                    diverse.append(selected)
            diverse.extend(
                hit
                for hit in ranked
                if RAGService._hit_key(hit) not in selected_keys
            )
            return diverse

        topic_match = match_alias(query, "topics")
        if topic_match is None or topic_match.score < 0.80:
            return hits

        topic = topic_match.canonical
        topic_norm = _normalize_text(topic)
        thai_norm = _normalize_text(primary_thai_alias("topics", topic))
        section_key = topic.casefold().replace(" ", "_")
        requested_action = match_alias(query, "actions")
        action_name = requested_action.canonical if requested_action else ""

        def topic_rank(hit: SearchHit) -> tuple[int, float]:
            content_norm = _normalize_text(hit.content)
            subtopic_norm = _normalize_text(str(hit.metadata.get("subtopic") or ""))
            section = str(hit.metadata.get("section") or "").casefold()
            exact_count = content_norm.count(topic_norm)
            thai_count = content_norm.count(thai_norm) if thai_norm else 0
            section_match = int(section == section_key)
            other_section_penalty = int(
                bool(section) and section != section_key
            )
            relevance = (
                section_match * 2
                + min(exact_count, 4) * 2
                + min(thai_count, 4)
                - other_section_penalty * 3
            )
            if action_name == "code":
                if any(term in subtopic_norm for term in ("implementation", "code")):
                    relevance += 12
                elif "pseudocode" in subtopic_norm:
                    relevance += 8
                if re.search(r"\b(def|function)\b|merge_sort\s*\(", hit.content):
                    relevance += 4
            return (relevance, hit.score)

        return sorted(hits, key=topic_rank, reverse=True)

    @staticmethod
    def _looks_corrupted_text(text: str) -> bool:
        """Detect common Thai PDF text-extraction substitutions.

        Some source PDFs extract glyphs such as ``L``, ``4`` and ``@`` in the
        middle of Thai words. Passing those chunks to the model produces the
        visibly broken answers users see, so they are safer to exclude than
        to present as grounded evidence.
        """
        if "\ufffd" in text:
            return True
        if re.search(r"[\ue000-\uf8ff]", text) or "¾" in text:
            return True
        if re.search(r"(?:^|\s)ํ(?=[ก-๙])", text):
            return True
        return re.search(r"[ก-๙][L4@][ก-๙]", text) is not None

    @staticmethod
    def _contains_complexity_evidence(text: str) -> bool:
        normalized = text.casefold()
        return re.search(r"(?:o|θ|ω)\s*\(\s*n", normalized) is not None

    @classmethod
    def _is_overall_complexity_claim(cls, topic: str, hit: SearchHit) -> bool:
        if not cls._contains_complexity_evidence(hit.content):
            return False

        subtopic = str(hit.metadata.get("subtopic") or "")
        searchable = f"{subtopic}\n{hit.content}".casefold()
        if topic == "Merge Sort":
            # A linear-time MERGE step is not the running time of Merge Sort.
            # Require either its recurrence or an explicit whole-algorithm
            # running-time label before using this chunk in a course-wide table.
            recurrence = re.search(r"\bt\s*\(\s*n\s*\)\s*=", searchable)
            whole_algorithm_label = re.search(
                r"merge\s+sort.{0,60}(?:running\s+time|time\s+complexity)"
                r"|(?:running\s+time|time\s+complexity).{0,60}merge\s+sort",
                searchable,
            )
            return recurrence is not None or whole_algorithm_label is not None

        complexity_markers = (
            "time complexity",
            "running time",
            "worst case",
            "average case",
            "best case",
            "number of comparisons",
            "comparisons",
            "ความซับซ้อน",
            "กรณีแย่ที่สุด",
            "กรณีเฉลี่ย",
            "กรณีดีที่สุด",
        )
        return any(marker in searchable for marker in complexity_markers)

    @classmethod
    def _coursewide_complexity_hits(
        cls, hits: list[SearchHit],
    ) -> list[SearchHit]:
        selected: list[SearchHit] = []
        for topic in PRIMARY_COMPLEXITY_TOPICS:
            section = topic.casefold().replace(" ", "_")
            candidates = [
                hit
                for hit in hits
                if str(hit.metadata.get("section") or "").casefold() == section
                and str(hit.metadata.get("curriculum_status") or "primary")
                == "primary"
                and cls._is_overall_complexity_claim(topic, hit)
            ]
            if candidates:
                selected.append(max(candidates, key=lambda hit: hit.score))
        return selected

    @staticmethod
    def _complexity_expressions(topic: str, content: str) -> list[str]:
        matches = list(
            re.finditer(
                r"(?P<notation>O|Θ|Ω)\s*\(\s*(?P<expression>[^)]{1,32})\)",
                content,
                flags=re.IGNORECASE,
            )
        )
        if topic == "Merge Sort" and matches:
            # The recurrence also contains Θ(n) for the merge work at one
            # level; the final expression is the whole algorithm's bound.
            matches = [matches[-1]]

        superscripts = str.maketrans("234", "²³⁴")
        expressions: list[str] = []
        for match in matches:
            expression = re.sub(r"\s+", "", match.group("expression")).casefold()
            expression = re.sub(
                r"n(?:\^)?([2-4])\b",
                lambda exponent: "n" + exponent.group(1).translate(superscripts),
                expression,
            )
            expression = re.sub(r"nlog(?:2)?n", "n log n", expression)
            expression = re.sub(r"log(?:2)?n", "log n", expression)
            expression = re.sub(r"\s*\+\s*", " + ", expression)
            notation = match.group("notation").upper()
            if notation == "Θ":
                notation = "Θ"
            elif notation == "Ω":
                notation = "Ω"
            expressions.append(f"{notation}({expression})")

        return list(dict.fromkeys(expressions))

    @staticmethod
    def _coursewide_formula_matches(topic: str, content: str) -> list[re.Match[str]]:
        matches = list(
            re.finditer(
                r"(?P<notation>O|Θ|Ω)\s*\(\s*(?P<expression>[^)]{1,32})\)",
                content,
                flags=re.IGNORECASE,
            )
        )
        if topic != "Merge Sort":
            return matches

        # Do not report the Θ(n) work of a single merge level as the total
        # Merge Sort bound. Select only a solved T(n) = Θ(...) expression.
        total_bound = re.search(
            r"\bt\s*\(\s*n\s*\)\s*=\s*(?:O|Θ|Ω)\s*\([^)]{1,32}\)",
            content,
            flags=re.IGNORECASE,
        )
        if total_bound is None:
            return []
        return [
            match
            for match in matches
            if total_bound.start() <= match.start() < total_bound.end()
        ][:1]

    @classmethod
    def _coursewide_complexity_fallback(
        cls,
        hits: list[SearchHit],
        language: str,
    ) -> str | None:
        selected = cls._coursewide_complexity_hits(
            cls._filter_corrupted_hits(hits)
        )
        by_section = {
            str(hit.metadata.get("section") or "").casefold(): hit
            for hit in selected
        }
        rows: list[tuple[str, str]] = []

        thai_case_labels = {
            "worst case": "กรณีแย่ที่สุด",
            "average case": "กรณีเฉลี่ย",
            "best case": "กรณีดีที่สุด",
            "comparisons": "จำนวนการเปรียบเทียบ",
        }
        english_case_labels = {
            "worst case": "Worst case",
            "average case": "Average case",
            "best case": "Best case",
            "comparisons": "Comparisons",
        }

        for topic in PRIMARY_COMPLEXITY_TOPICS:
            section = topic.casefold().replace(" ", "_")
            hit = by_section.get(section)
            if hit is None:
                return None
            matches = cls._coursewide_formula_matches(topic, hit.content)
            if not matches:
                return None

            rendered: list[str] = []
            case_labels = (
                thai_case_labels if language == "th" else english_case_labels
            )
            previous_formula_end = 0
            for match in matches:
                formula = cls._complexity_expressions(
                    topic,
                    match.group(0),
                )
                if not formula:
                    previous_formula_end = match.end()
                    continue
                prefix = hit.content[previous_formula_end:match.start()].casefold()
                case_markers = [
                    (prefix.rfind(marker), label)
                    for marker, label in (
                        ("worst case", "worst case"),
                        ("average case", "average case"),
                        ("best case", "best case"),
                    )
                    if marker in prefix
                ]
                nearest_case = max(case_markers, default=(-1, None))
                marker_positions = [
                    (prefix.rfind(marker), label)
                    for marker, label in (
                        ("comparison", "comparisons"),
                        ("time complexity", "time"),
                        ("running time", "time"),
                        ("complexity", "time"),
                        (" time", "time"),
                        ("auxiliary storage", "space"),
                        ("storage", "space"),
                        ("memory", "space"),
                        (" space", "space"),
                    )
                    if marker in prefix
                ]
                nearest_marker = max(marker_positions, default=(-1, None))
                label = (
                    nearest_case[1]
                    if nearest_case[0] >= 0
                    else nearest_marker[1]
                )
                if label == "space":
                    previous_formula_end = match.end()
                    continue
                if label is None:
                    subtopic = str(hit.metadata.get("subtopic") or "").casefold()
                    if not any(
                        marker in subtopic
                        for marker in ("running time", "time complexity", "complexity")
                    ):
                        previous_formula_end = match.end()
                        continue
                    label = "time"
                if label == "time":
                    label = None
                rendered_value = formula[0]
                if label is not None:
                    rendered_value = f"{case_labels[label]}: {rendered_value}"
                if rendered_value not in rendered:
                    rendered.append(rendered_value)
                previous_formula_end = match.end()

            if not rendered:
                return None
            rows.append((topic, "; ".join(rendered)))

        if language == "en":
            table = [
                "### Big-O summary from the course documents",
                "",
                "| Algorithm | Time complexity |",
                "|---|---|",
                *[f"| {topic} | {value} |" for topic, value in rows],
                "",
                "The source uses Θ where it gives a tight bound; case labels are "
                "shown only when the evidence identifies them.",
            ]
        else:
            table = [
                "### สรุปความซับซ้อนเวลา (Big-O) จากเอกสาร",
                "",
                "| อัลกอริทึม | ความซับซ้อนเวลา |",
                "|---|---|",
                *[f"| {topic} | {value} |" for topic, value in rows],
                "",
                "เอกสารใช้ Θ เมื่อระบุขอบเขตแน่น และแสดงกรณีดีที่สุด/เฉลี่ย/แย่ที่สุด "
                "เฉพาะหัวข้อที่หลักฐานระบุไว้",
            ]
        return "\n".join(table)

    @classmethod
    def _filter_corrupted_hits(cls, hits: list[SearchHit]) -> list[SearchHit]:
        return [hit for hit in hits if not cls._looks_corrupted_text(hit.content)]

    @staticmethod
    def _hit_key(hit: SearchHit) -> tuple[str, int, int]:
        return (hit.source_id, hit.page_number, hit.chunk_index)

    @staticmethod
    def _topic_hit_matches(
        hit: SearchHit,
        topic: str,
        *,
        exact_section_only: bool = False,
    ) -> bool:
        section = str(hit.metadata.get("section") or "").casefold()
        section_key = topic.casefold().replace(" ", "_")
        if section == section_key:
            return True
        if exact_section_only:
            return False
        content = _normalize_text(hit.content)
        topic_norm = _normalize_text(topic)
        thai_norm = _normalize_text(primary_thai_alias("topics", topic))
        return topic_norm in content or bool(thai_norm and thai_norm in content)

    @classmethod
    def _best_topic_hit(
        cls,
        topic: str,
        hits: list[SearchHit],
    ) -> SearchHit | None:
        exact = [
            hit
            for hit in hits
            if cls._topic_hit_matches(hit, topic, exact_section_only=True)
        ]
        candidates = exact or [
            hit for hit in hits if cls._topic_hit_matches(hit, topic)
        ]
        return max(candidates, key=lambda hit: hit.score) if candidates else None

    def _search_hits(
        self,
        retrieval_query: str,
        query_vector: list[float] | None,
        topic_targets: list[str],
        *,
        complexity_focus: bool = False,
    ) -> list[SearchHit]:
        """Search the base query and fan out when multiple topics are named."""
        search_top_k = max(self.settings.top_k, self.settings.candidate_k)
        hits = self.store.search(
            retrieval_query,
            query_vector,
            top_k=search_top_k,
            candidate_k=self.settings.candidate_k,
        )
        if len(topic_targets) < 2 and not (complexity_focus and topic_targets):
            return hits

        clean_base_hits = self._filter_corrupted_hits(hits)
        missing_targets = [
            topic
            for topic in topic_targets
            if not any(
                self._topic_hit_matches(
                    hit,
                    topic,
                    exact_section_only=True,
                )
                and (
                    not complexity_focus
                    or self._is_overall_complexity_claim(topic, hit)
                )
                for hit in clean_base_hits
            )
        ]
        if not missing_targets:
            return hits

        requires_embedding = getattr(
            self.store,
            "requires_query_embedding",
            True,
        )
        for topic in missing_targets:
            if complexity_focus:
                topic_query = (
                    f"{topic} {primary_thai_alias('topics', topic)} "
                    "time complexity Big-O best average worst case "
                    "ความซับซ้อนเชิงเวลา กรณีดีที่สุด กรณีเฉลี่ย กรณีแย่ที่สุด"
                ).strip()
            else:
                topic_query = (
                    f"{topic} {primary_thai_alias('topics', topic)} "
                    "คืออะไร หลักการทำงาน ขั้นตอน ตัวอย่าง"
                ).strip()
            topic_vector = (
                self.embedder.embed_query(topic_query)
                if requires_embedding
                else None
            )
            hits.extend(
                self.store.search(
                    topic_query,
                    topic_vector,
                    top_k=search_top_k,
                    candidate_k=self.settings.candidate_k,
                )
            )

        unique_hits: dict[tuple[str, int, int], SearchHit] = {}
        for hit in hits:
            key = (hit.source_id, hit.page_number, hit.chunk_index)
            previous = unique_hits.get(key)
            if previous is None or hit.score > previous.score:
                unique_hits[key] = hit
        return list(unique_hits.values())

    @staticmethod
    def _rerank_definition_hits(
        query: str,
        hits: list[SearchHit],
    ) -> list[SearchHit]:
        if not RAGService._is_general_sort_definition(query):
            return hits

        def definition_rank(hit: SearchHit) -> tuple[int, float]:
            text = _normalize_text(hit.content)
            quality = 0
            if "การเรียงลำดับข้อมูล หรือการจัดเรียงข้อมูล" in text:
                quality += 8
            if "data sorting" in text:
                quality += 4
            if "เป็นการ" in text:
                quality += 3
            if "จากน้อยไปมาก" in text or "จากมากไปน้อย" in text:
                quality += 2
            if len(text) < 120:
                quality -= 8
            if any(
                marker in text
                for marker in (
                    "แบบฝึกหัด",
                    "จงตอบคำถาม",
                    "หัวข้อเรื่อง",
                    "อธิบายหลักการ",
                )
            ):
                quality -= 6
            return (quality, hit.score)

        return sorted(hits, key=definition_rank, reverse=True)

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
        retrieval_topics = self.topic_targets(retrieval_query)
        complexity_focus = self._asks_complexity_question(query)
        coursewide_complexity = self._asks_coursewide_complexity_summary(query)
        started = perf_counter()
        query_vector = (
            self.embedder.embed_query(retrieval_query)
            if getattr(self.store, "requires_query_embedding", True)
            else None
        )
        hits = self._search_hits(
            retrieval_query,
            query_vector,
            retrieval_topics,
            complexity_focus=complexity_focus,
        )
        hits = self._filter_corrupted_hits(hits)
        ranking_query = retrieval_query if len(retrieval_topics) >= 2 else query
        hits = self._rerank_topic_hits(ranking_query, hits)
        hits = self._rerank_definition_hits(query, hits)
        if coursewide_complexity:
            hits = self._coursewide_complexity_hits(hits)
            hits = hits[: max(self.settings.top_k, len(PRIMARY_COMPLEXITY_TOPICS))]
        else:
            hits = hits[: self.settings.top_k]
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

        if self._asks_coursewide_complexity_summary(result.query):
            required_sections = {
                topic.casefold().replace(" ", "_")
                for topic in PRIMARY_COMPLEXITY_TOPICS
            }
            supported_sections = {
                str(hit.metadata.get("section") or "").casefold()
                for hit in self._coursewide_complexity_hits(result.hits)
                if hit.score >= 0.10
            }
            return required_sections.issubset(supported_sections)

        return result.top_score >= threshold

    def _context_text(self, hits: list[SearchHit]) -> str:
        blocks: list[str] = []
        clean_hits = self._filter_corrupted_hits(hits)
        for idx, hit in enumerate(clean_hits, start=1):
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

    @staticmethod
    def _clean_evidence_text(hit: SearchHit) -> str:
        text = " ".join(hit.content.split()).strip()
        text = re.sub(
            r"^หน่วยที่\s*\d+\s+การเรียงล\s*า?ดับข้อมูล\s*\d*\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text

    @staticmethod
    def _evidence_points(text: str, *, limit: int = 4) -> list[str]:
        words = text.split()
        if not words:
            return []
        points: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            current.append(word)
            current_len += len(word) + 1
            if current_len >= 170:
                points.append(" ".join(current).rstrip(" ,;:-"))
                current = []
                current_len = 0
                if len(points) >= limit:
                    break
        if current and len(points) < limit:
            points.append(" ".join(current).rstrip(" ,;:-"))
        return points

    @staticmethod
    def _points_match_language(points: list[str], language: str) -> bool:
        if not points:
            return False
        if language == "th":
            return all(
                any("\u0e00" <= char <= "\u0e7f" for char in point)
                for point in points
            )
        return all(
            any(char.isascii() and char.isalpha() for char in point)
            for point in points
        )

    @staticmethod
    def _fallback_language_notice(language: str) -> str:
        if language == "th":
            return (
                "_หมายเหตุ: หลักฐานในเอกสารเป็นภาษาอังกฤษบางส่วน "
                "จึงคงข้อความต้นฉบับไว้ในคำตอบสำรองเพื่อไม่ให้แปลความหมายผิด_"
            )
        return (
            "_Note: Some retrieved evidence is in Thai, so the source wording "
            "is preserved in this fallback to avoid mistranslation._"
        )

    def _generation_failure_notice(self, language: str) -> str:
        if language == "en":
            return (
                "Sorry, I couldn't generate a reliable answer from the course "
                "documents just now. Please try again shortly."
            )
        return (
            f"ขออภัย{self.thai_statement_particle} ตอนนี้ระบบสร้างคำตอบจากเอกสารไม่สำเร็จ "
            "กรุณาลองใหม่อีกครั้งในอีกสักครู่"
        )

    def _comparison_grounded_fallback(
        self,
        query: str,
        hits: list[SearchHit],
        language: str,
    ) -> str:
        targets = self.topic_targets(query)
        sections: list[tuple[str, list[str]]] = []
        missing_topics: list[str] = []
        language_mismatch = False
        for topic in targets:
            hit = self._best_topic_hit(topic, hits)
            if hit is None:
                missing_topics.append(topic)
                continue
            points = self._evidence_points(
                self._clean_evidence_text(hit),
                limit=2,
            )
            if not points:
                missing_topics.append(topic)
                continue
            if not self._points_match_language(points, language):
                language_mismatch = True
            sections.append((topic, points))

        if not sections:
            if language == "en":
                return (
                    "The generation step took too long, and no suitable evidence "
                    "was available for the compared topics."
                )
            return (
                "ระบบสร้างคำตอบใช้เวลานานเกินกำหนด และไม่พบหลักฐานที่เหมาะสม "
                f"สำหรับหัวข้อที่นำมาเปรียบเทียบ{self.thai_statement_particle}"
            )

        if language == "en":
            answer = [
                "### Comparing " + " and ".join(topic for topic, _ in sections),
                "",
            ]
        else:
            answer = [
                "### เปรียบเทียบ " + " กับ ".join(topic for topic, _ in sections),
                "",
            ]
        if language_mismatch:
            answer.extend([self._fallback_language_notice(language), ""])
        for index, (topic, points) in enumerate(sections):
            if index:
                answer.append("")
            answer.append(f"**{topic}**")
            answer.extend(f"- {point}" for point in points)
        if missing_topics:
            answer.extend(
                [
                    "",
                    (
                        "_ยังไม่พบหลักฐานเพียงพอสำหรับ: "
                        + ", ".join(missing_topics)
                        + " จึงไม่สรุปแทน_"
                    )
                    if language == "th"
                    else (
                        "_Insufficient evidence for: "
                        + ", ".join(missing_topics)
                        + "; no unsupported summary was added._"
                    ),
                ]
            )
        return "\n".join(answer)

    def _fast_grounded_fallback(
        self,
        query: str,
        hits: list[SearchHit],
        language_mode: str = "thai",
    ) -> str:
        language = resolve_response_language(language_mode, query)
        hits = self._filter_corrupted_hits(hits)
        if not hits:
            if language == "en":
                return (
                    "The generation step took too long, and no suitable evidence "
                    "was available to show as a fallback."
                )
            return (
                "ระบบสร้างคำตอบใช้เวลานานเกินกำหนด "
                "และไม่พบข้อความที่เหมาะสำหรับแสดงแทนจากเอกสาร"
            )

        if len(self.topic_targets(query)) >= 2:
            return self._comparison_grounded_fallback(query, hits, language)

        text = self._clean_evidence_text(hits[0])
        anchors = (
            "การเรียงลำดับข้อมูล หรือการจัดเรียงข้อมูล",
            "การเรียงลำดับข้อมูลแบบ",
        )
        for anchor in anchors:
            pos = text.find(anchor)
            if pos >= 0:
                text = text[pos:]
                break

        points = self._evidence_points(text)
        if not points:
            if language == "en":
                return (
                    "The generation step took too long, and no suitable evidence "
                    "was available to show as a fallback."
                )
            return (
                "ระบบสร้างคำตอบใช้เวลานานเกินกำหนด "
                "และไม่พบข้อความที่เหมาะสำหรับแสดงแทนจากเอกสาร"
            )

        language_mismatch = not self._points_match_language(points, language)
        notice = (
            [self._fallback_language_notice(language), ""]
            if language_mismatch
            else []
        )

        topic_match = match_alias(query, "topics")
        if topic_match is not None and topic_match.score >= 0.80:
            title = topic_match.canonical
            if language == "en":
                title = {
                    "หลักการเรียงลำดับข้อมูล": "Data Sorting Fundamentals",
                }.get(title, title)
                answer = [
                    f"### {title}",
                    "",
                    *notice,
                    "**Meaning**",
                    f"- {points[0]}",
                ]
            else:
                answer = [
                    f"### {title}",
                    "",
                    *notice,
                    "**ความหมาย**",
                    f"- {points[0]}",
                ]
            if len(points) > 1:
                answer.extend(
                    ["", "**How it works**" if language == "en" else "**หลักการทำงาน**"]
                )
                answer.extend(
                    f"{idx}. {point}"
                    for idx, point in enumerate(points[1:], start=1)
                )
            return "\n".join(answer)

        if self._is_general_sort_definition(query):
            if language == "en":
                return "\n".join(
                    [
                        "### Data Sorting Fundamentals",
                        "",
                        *notice,
                        "**Meaning**",
                        f"- {points[0]}",
                        *[f"- {point}" for point in points[1:]],
                    ]
                )
            return "\n".join(
                [
                    "### การเรียงลำดับข้อมูล",
                    "",
                    *notice,
                    "**ความหมาย**",
                    f"- {points[0]}",
                    *[f"- {point}" for point in points[1:]],
                ]
            )

        return "\n".join([*notice, *(f"- {point}" for point in points)])

    def stream_answer(
        self,
        *,
        query: str,
        result: RetrievalResult,
        history: list[dict[str, str]],
        model_name: str | None = None,
        language_mode: str = "auto",
    ) -> Iterable[str]:
        language = resolve_response_language(language_mode, query)
        direct_text = self.direct_response(query, history, language_mode)
        if direct_text:
            yield direct_text
            return

        if not self.answerable(result):
            if self._asks_coursewide_complexity_summary(query):
                if language == "en":
                    yield (
                        "I couldn't verify Big-O evidence for every primary "
                        "algorithm, so I won't fill in the missing entries."
                    )
                else:
                    yield (
                        f"{self.thai_first_person}ยังตรวจหลักฐาน Big-O ของอัลกอริทึมหลักได้ไม่ครบ "
                        f"จึงขอไม่เติมค่าที่เอกสารยังยืนยันไม่ได้{self.thai_statement_particle}"
                    )
                return
            if language == "en":
                yield (
                    "I could not find enough information in the course documents "
                    "to answer this question. Try naming a specific algorithm or topic."
                )
                return
            yield (
                f"{self.thai_first_person}ยังไม่พบข้อมูลที่เพียงพอในเอกสารที่ใช้เป็นฐานความรู้"
                f"สำหรับคำถามนี้{self.thai_statement_particle} ถ้าต้องการ ลองถามใหม่โดยระบุหัวข้อ"
                "หรือชื่ออัลกอริทึมให้ชัดขึ้น"
            )
            return

        if self._asks_coursewide_complexity_summary(query):
            summary = self._coursewide_complexity_fallback(
                result.hits,
                language,
            )
            if summary is not None:
                yield summary
            elif language == "en":
                yield (
                    "I found complexity evidence, but could not safely format a "
                    "complete table for all five primary algorithms."
                )
            else:
                yield (
                    "พบหลักฐานเรื่องความซับซ้อน แต่ยังจัดรูปตารางให้ครบทั้ง "
                    f"5 อัลกอริทึมหลักอย่างปลอดภัยไม่ได้{self.thai_statement_particle}"
                )
            return

        if self._is_general_sort_definition(query):
            yield self._fast_grounded_fallback(
                query,
                result.hits,
                language_mode,
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
ภาษาที่ต้องใช้ในคำตอบ: {"ภาษาไทย" if language == "th" else "English"}
""".strip()

        config = types.GenerateContentConfig(
            system_instruction=build_tutor_prompt(language_mode, query, persona_id=getattr(self, "persona_id", None)),
            max_output_tokens=self.settings.generation_max_output_tokens,
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.MINIMAL
            ),
            http_options=types.HttpOptions(
                timeout=self.settings.generation_timeout_ms
            ),
        )

        model = model_name or self.settings.generation_model
        emitted = False
        try:
            for chunk in self.client.models.generate_content_stream(
                model=model,
                contents=payload,
                config=config,
            ):
                text = getattr(chunk, "text", None)
                if text:
                    emitted = True
                    yield text
        except Exception as exc:
            logger.warning(
                "Answer generation stream failed (%s)",
                type(exc).__name__,
            )
            if not emitted:
                yield self._generation_failure_notice(language)
                return
            yield (
                "\n\n_คำตอบอาจไม่ครบเพราะการสร้างคำตอบขัดข้อง กรุณาลองใหม่_"
                if language == "th"
                else "\n\n_This answer may be incomplete due to a generation error. Please try again._"
            )
            return

        if not emitted:
            logger.warning("Answer generation stream returned no text")
            yield self._generation_failure_notice(language)

        # Citations are rendered as structured UI by Streamlit instead of
        # being appended to the teaching prose. This keeps answers readable
        # while preserving inspectable evidence.
