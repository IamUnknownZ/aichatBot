import os
from time import perf_counter
from uuid import uuid4

import streamlit as st
from dotenv import load_dotenv

from prompt import resolve_response_language, response_language_options
from rag.bootstrap import build_rag_service
from rag.config import Settings
from rag.visuals import (
    compact_image_caption,
    image_message_payload,
    image_preview_groups,
)
from ui import inject_theme, render_welcome_panel
from ui.workspace import inject_workspace_theme, render_workspace_header, persona_avatar
from rag.personas import PERSONAS, get_persona
from rag.chat_history import ChatHistory, HistoryUnavailable, _owner
from ui.browser_identity import browser_identity
from ui.history_state import (
    append_answer_and_log,
    clear_pending_history_saves,
    history_save_status,
    queue_pending_history_save,
    restore_thread,
    retry_pending_history_saves,
    set_history_save_status,
)


load_dotenv()
page_settings = Settings.from_env()
APP_CACHE_VERSION = "2026-09-29-six-persona-v1"

st.set_page_config(
    page_title=f"{page_settings.course_title} · AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_theme()
inject_workspace_theme()


def get_secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value.strip()
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return ""


def track_stream(
    stream,
    timing: dict[str, float | None],
    started: float,
    thinking_placeholder=None,
):
    first_chunk = True
    for chunk in stream:
        if first_chunk:
            first_chunk = False
            if thinking_placeholder is not None:
                thinking_placeholder.empty()
        if timing["ttft_ms"] is None:
            timing["ttft_ms"] = (perf_counter() - started) * 1000.0
        yield chunk


def render_thinking(placeholder, label: str) -> None:
    placeholder.markdown(
        f"""
<div class="tutor-thinking" role="status" aria-live="polite">
  <span class="tutor-thinking-orb">✦</span>
  <span class="tutor-thinking-label">{label}</span>
  <span class="tutor-thinking-dots" aria-hidden="true">
    <i></i><i></i><i></i>
  </span>
</div>
""",
        unsafe_allow_html=True,
    )


def compact_sources(hits) -> list[dict[str, object]]:
    seen: set[tuple[str, int]] = set()
    sources: list[dict[str, object]] = []
    for hit in hits:
        key = (hit.source_file, hit.page_number)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "source_id": hit.source_id,
                "source_file": hit.source_file,
                "page_number": hit.page_number,
                "preview": hit.content[:260].strip(),
                "score": hit.score,
            }
        )
        if len(sources) >= 4:
            break
    return sources


def render_sources(sources: list[dict[str, object]]) -> None:
    if not sources:
        return

    pages = [str(item["page_number"]) for item in sources]
    label = f"📚 แหล่งอ้างอิง · หน้า {', '.join(pages)}"
    with st.expander(label, expanded=False):
        st.caption(
            "หลักฐานที่ระบบใช้ค้นคำตอบจากเอกสารรายวิชา "
            "เปิดดูเมื่อต้องการตรวจสอบที่มา"
        )
        for item in sources:
            st.markdown(
                f"**หน้า {item['page_number']}** · {item['source_file']}"
            )
            preview = str(item.get("preview", "")).strip()
            if preview:
                st.caption(preview)


def render_message_images(
    images: list[dict[str, object]],
    *,
    visual_request: bool,
) -> None:
    if not images:
        return

    def render_items() -> None:
        index = 0
        for group in image_preview_groups(images, columns=3):
            columns = st.columns(len(group))
            for column, image in zip(columns, group):
                index += 1
                metadata = image.get("metadata", {})
                if not isinstance(metadata, dict):
                    metadata = {}
                with column:
                    st.image(image["image_bytes"], width="stretch")
                    st.caption(
                        compact_image_caption(
                            metadata,
                            page_number=image.get("page_number", ""),
                            index=index,
                        )
                    )

    if visual_request:
        st.caption("ภาพจากเอกสารฐานความรู้จริง")
        render_items()
    else:
        with st.expander("ภาพประกอบจากเอกสารฐานความรู้"):
            render_items()


@st.cache_resource(show_spinner=False)
def create_rag_service(
    api_key: str,
    database_url: str,
    cache_version: str,
):
    settings = Settings.from_env(
        api_key=api_key,
        database_url=database_url,
    )
    service = build_rag_service(settings, require_database=True)
    if service.store_mode != "postgres-pgvector":
        raise RuntimeError(
            f"ต้องใช้ postgres-pgvector แต่ได้ {service.store_mode}"
        )
    return service, settings


def ensure_chat_state(settings: Settings) -> None:
    st.session_state.setdefault("active_persona", "nui")
    threads = st.session_state.setdefault("persona_threads", {})
    active = st.session_state["active_persona"]
    if active not in threads:
        persona = get_persona(active)
        threads[active] = [{"role": "assistant", "content":
            f"สวัสดีครับ ผมคือ **{persona.name}** เป็น AI ช่วยเรียน "
            f"**{settings.course_title}** · {persona.subtitle} "
            "คำตอบจะยึดเอกสารบทเรียน และจะบอกเมื่อหลักฐานไม่พอ"}]
    st.session_state["messages"] = threads[active]
    st.session_state.setdefault("response_language", "thai")


api_key = get_secret("GEMINI_API_KEY")
database_url = get_secret("DATABASE_URL")
service = None
settings = page_settings
service_error = None
if api_key:
    try:
        with st.spinner("กำลังเชื่อมต่อฐานความรู้..."):
            service, settings = create_rag_service(api_key, database_url, APP_CACHE_VERSION)
    except Exception:
        service_error = "ไม่สามารถเชื่อมต่อฐานความรู้ได้ กรุณาตรวจการตั้งค่าและ index"

ensure_chat_state(settings)
identity = browser_identity()
history_backend = None
history_ready = False
history_notice = ""
if service is not None and identity:
    try:
        history_backend = ChatHistory(service.store._connect)
        if not st.session_state.get("history_schema_ready"):
            history_backend.initialize()
            st.session_state["history_schema_ready"] = True
        owner_key = _owner(identity["token"])
        if st.session_state.get("history_owner") != owner_key:
            profile = history_backend.get_profile(identity["token"])
            st.session_state["history_owner"] = owner_key
            st.session_state["history_loaded"] = set()
            st.session_state["persona_threads"] = {}
            ensure_chat_state(settings)
            st.session_state["display_name"] = (profile or {}).get("display_name", "")
        history_ready = restore_thread(st.session_state, history_backend,
            identity["token"], st.session_state["active_persona"])
        if history_ready and identity.get("persisted"):
            retry_pending_history_saves(
                st.session_state,
                history_backend,
                identity["token"],
                st.session_state["active_persona"],
            )
        st.session_state["messages"] = st.session_state["persona_threads"][st.session_state["active_persona"]]
        if not history_ready:
            history_notice = "โหลดประวัติเดิมไม่สำเร็จ · ไม่ถือว่าประวัติว่าง และยังไม่บันทึกทับ"
    except (HistoryUnavailable, ValueError):
        history_notice = "ระบบประวัติยังไม่พร้อม · บทสนทนาใหม่อยู่ใน session นี้เท่านั้น"

if service is not None and settings.profile_enabled:
    if identity is None:
        st.info("กำลังเตรียมรหัสผู้ใช้สำหรับเบราว์เซอร์นี้")
        st.stop()
    @st.dialog("ยินดีต้อนรับ · AI Learning Studio", width="small")
    def display_name_dialog():
        st.write("ชื่อใช้แสดงผลเท่านั้น ชื่อซ้ำกันได้โดยไม่รวมประวัติ")
        with st.form("display_name_form"):
            display = st.text_input("ชื่อ / ชื่อเล่น", max_chars=40)
            submit = st.form_submit_button("เริ่มเรียน", type="primary")
        st.caption("ประวัติผูกกับเบราว์เซอร์นี้ ไม่ใช่บัญชีล็อกอิน ล้างข้อมูลเบราว์เซอร์หรือเปลี่ยนเครื่องจะไม่เห็นประวัติเดิม")
        if submit:
            if not display.strip():
                st.warning("กรอกชื่อที่ต้องการให้เรียก")
                return
            st.session_state["display_name"] = display.strip()
            if history_backend and history_ready:
                try:
                    history_backend.set_profile(identity["token"], display.strip())
                except HistoryUnavailable:
                    st.session_state["history_name_failed"] = True
            st.rerun()
    if not st.session_state.get("display_name"):
        display_name_dialog()
        st.stop()

with st.sidebar:
    st.markdown("### ✦ AI Learning Studio")
    st.caption("6 AI tutors · ฐานความรู้เดียวกัน")
    st.markdown("##### เลือกเพื่อน AI")
    for persona in PERSONAS:
        selected = st.session_state["active_persona"] == persona.id
        with st.container(key=f"persona-card-{persona.id}"):
            face, label = st.columns([1, 4], vertical_alignment="center")
            with face:
                st.image(persona_avatar(persona), width=42)
            with label:
                if st.button(f"{persona.name} · {persona.subtitle}", key=f"persona_{persona.id}",
                             type="primary" if selected else "secondary", use_container_width=True):
                    st.session_state["active_persona"] = persona.id
                    st.session_state.pop("queued_prompt", None)
                    st.rerun()
    st.divider()
    st.caption("คุณ · ผู้เรียน")
    student_name = st.session_state.get("display_name", "")
    if student_name:
        st.markdown(f"**{student_name}**")
    with st.expander("ชื่อแสดงผล", expanded=False):
        name = st.text_input("ชื่อ / ชื่อเล่น", value=student_name, max_chars=40)
        if st.button("บันทึกชื่อ", key="save_display_name"):
            if name.strip():
                st.session_state["display_name"] = name.strip()
                if history_backend and history_ready:
                    try:
                        history_backend.set_profile(identity["token"], name.strip())
                        st.session_state["history_name_failed"] = False
                    except HistoryUnavailable:
                        st.session_state["history_name_failed"] = True
                st.rerun()
    st.caption("ชื่อใช้แสดงผล ไม่ใช้ค้นหรือรวมประวัติ")
    if st.button("เริ่มแชตใหม่", key="new_chat", use_container_width=True):
        st.session_state["confirm_clear"] = st.session_state["active_persona"]
    if st.session_state.get("confirm_clear") == st.session_state["active_persona"]:
        st.warning("จะลบบทสนทนาของ AI คนนี้เท่านั้น ย้อนกลับไม่ได้")
        left, right = st.columns(2)
        if left.button("ยืนยันลบ", key="confirm_delete"):
            can_clear = not history_backend and not st.session_state.get("history_owner")
            if history_backend and history_ready:
                can_clear = history_backend.clear_history(identity["token"], st.session_state["active_persona"])
            if can_clear:
                st.session_state["persona_threads"].pop(st.session_state["active_persona"], None)
                st.session_state.pop("confirm_clear", None)
                clear_pending_history_saves(
                    st.session_state,
                    identity["token"] if identity else None,
                    st.session_state["active_persona"],
                )
                st.rerun()
            else:
                st.error("ลบไม่สำเร็จ ประวัติเดิมยังอยู่")
        if right.button("ยกเลิก", key="cancel_delete"):
            st.session_state.pop("confirm_clear", None)
            st.rerun()
    st.caption("ประวัติเป็นของเบราว์เซอร์นี้ · หลีกเลี่ยงเครื่องสาธารณะ")
    if identity and not identity.get("persisted"):
        st.warning("เบราว์เซอร์ไม่อนุญาตให้จำรหัส ประวัติจะกลับมาไม่ได้หลังปิด session")
    if st.session_state.get("history_name_failed"):
        st.warning("ชื่อยังไม่ถูกบันทึกถาวร")
    with st.expander("Advanced", expanded=False):
        show_debug = st.checkbox("แสดง RAG debug", value=False)
        st.caption(f"Model: {settings.generation_model}")
        st.caption(f"Retrieval: {service.store_mode if service else 'unavailable'}")

active_persona = get_persona(st.session_state["active_persona"])
if service is not None:
    service = service.for_persona(active_persona.id)
    settings = service.settings
render_workspace_header(active_persona, settings.course_title, student_name)
if history_notice:
    st.warning(history_notice)
elif history_ready:
    st.caption("โหลดประวัติแล้ว · แยกตาม AI · ชื่อซ้ำกันได้")
save_status = (
    history_save_status(
        st.session_state,
        identity["token"] if identity else None,
        active_persona.id,
    )
)
if save_status == "saved":
    st.caption(f"บันทึกประวัติของ {active_persona.name} แล้ว")
elif save_status == "pending":
    st.warning(f"บันทึกประวัติของ {active_persona.name} ยังไม่สำเร็จ · จะลองอีกครั้ง")
elif save_status == "failed":
    st.warning(f"บันทึกประวัติของ {active_persona.name} ไม่สำเร็จ · คำตอบยังอยู่ใน session นี้")
elif save_status == "session_only":
    st.warning(f"คำตอบของ {active_persona.name} อยู่ใน session นี้เท่านั้น · ยังไม่ได้บันทึกประวัติถาวร")
if service_error:
    st.warning(service_error)
elif service is None:
    st.info("หน้าตา UI พร้อมแสดงตัวอย่าง · ต้องตั้ง GEMINI_API_KEY และฐานข้อมูลก่อนถาม AI")

messages = st.session_state["messages"]
for message in messages:
    role = "assistant" if message["role"] in {"assistant", "model"} else "user"
    avatar = persona_avatar(active_persona) if role == "assistant" else "🙂"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])
        if role == "assistant":
            render_sources(message.get("sources", []))
            render_message_images(message.get("images", []),
                visual_request=bool(message.get("visual_request")))


preset_query = None
if service is not None and len(messages) <= 1:
    render_welcome_panel(settings.tutor_name)
    st.caption("ลองเริ่มด้วยคำถามเหล่านี้")
    quick_prompts = [
        ("🫧 Bubble Sort · เริ่มจากภาพรวม", "อธิบาย Bubble Sort ให้เห็นภาพแบบเข้าใจง่าย"),
        ("↔️ เปรียบเทียบสองวิธี", "Bubble Sort กับ Selection Sort ต่างกันอย่างไร"),
        ("🧩 Trace ทีละรอบ", "ช่วย Trace Bubble Sort กับข้อมูล 5, 1, 4, 2 ทีละรอบ"),
        ("⏱️ Big-O แบบเข้าใจง่าย", "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"),
    ]
    cols = st.columns(2)
    for idx, (label, prompt) in enumerate(quick_prompts):
        with cols[idx % 2]:
            if st.button(
                label,
                key=f"quick_{idx}",
                use_container_width=True,
                help=prompt,
            ):
                preset_query = prompt


queued_query = st.session_state.pop("queued_prompt", None)
language_options = response_language_options()
language_labels = [label for label, _ in language_options]
language_by_label = {label: mode for label, mode in language_options}
current_language = st.session_state.get("response_language", "thai")
if current_language not in language_by_label.values():
    current_language = "thai"
    st.session_state["response_language"] = current_language
current_language_label = next(
    (
        label
        for label, mode in language_options
        if mode == current_language
    ),
    language_labels[0],
)
with st.container(key="language-float", border=False):
    st.markdown(
        """
<div class="language-float-label">
  <span>🌐 ภาษาคำตอบ</span>
  <span>Response language</span>
</div>
""",
        unsafe_allow_html=True,
    )
    selected_language_label = st.segmented_control(
        "ภาษาคำตอบ / Response language",
        options=language_labels,
        default=current_language_label,
        key="response_language_control",
        help="เลือกภาษาไทยหรือภาษาอังกฤษสำหรับคำตอบถัดไป",
        width="content",
        label_visibility="collapsed",
    )
    if selected_language_label is None:
        selected_language_label = current_language_label
    response_language = language_by_label[selected_language_label]
    st.session_state["response_language"] = response_language

typed_query = st.chat_input(
    f"ถามเกี่ยวกับ {settings.course_title}...",
    disabled=service is None,
)
user_query = preset_query or queued_query or typed_query


if user_query:
    if service is None:
        st.error("ระบบฐานความรู้ยังไม่พร้อม")
        st.stop()

    history_before = list(st.session_state["messages"])
    st.session_state["messages"].append(
        {"role": "user", "content": user_query}
    )

    with st.chat_message("user", avatar="🙂"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar=persona_avatar(active_persona)):
        try:
            request_started = perf_counter()
            thinking_placeholder = st.empty()
            render_thinking(
                thinking_placeholder,
                "กำลังค้นส่วนที่เกี่ยวข้องในเอกสาร",
            )
            result = service.retrieve(user_query, history_before)
            answered = service.answerable(result)
            visual_request = service.is_visual_request(user_query)
            visual_topic = (
                service.visual_topic(user_query, history_before)
                if visual_request
                else None
            )
            explicit_visual_topic = (
                service.topic_from_query(user_query)
                if visual_request
                else None
            )

            current_references = list(
                dict.fromkeys(
                    (hit.source_id, hit.page_number)
                    for hit in result.hits
                )
            )
            previous_references = []
            if visual_request and explicit_visual_topic is None:
                for message in reversed(history_before):
                    sources = message.get("sources", [])
                    previous_references = [
                        (str(source["source_id"]), int(source["page_number"]))
                        for source in sources
                        if source.get("source_id")
                    ]
                    if previous_references:
                        break

            image_references = list(
                dict.fromkeys(
                    (previous_references + current_references)
                    if visual_request
                    else current_references
                )
            )
            images = []
            if answered and settings.max_images_per_answer > 0:
                image_candidates = service.store.images_for_references(
                    image_references,
                    limit=settings.max_images_per_answer * 4,
                )
                images = service.select_user_visible_images(
                    image_candidates,
                    limit=settings.max_images_per_answer,
                    topic=visual_topic,
                )
            image_payload = image_message_payload(images)

            render_thinking(
                thinking_placeholder,
                "กำลังเรียบเรียงคำตอบ",
            )
            timing = {"ttft_ms": None}

            if not answered:
                stream = service.stream_answer(
                    query=user_query,
                    result=result,
                    history=history_before,
                    model_name=settings.generation_model,
                    language_mode=response_language,
                )
                response_text = "".join(stream)
                thinking_placeholder.empty()
                st.markdown(response_text)
                timing["ttft_ms"] = (perf_counter() - request_started) * 1000.0
            elif visual_request:
                thinking_placeholder.empty()
                if resolve_response_language(response_language, user_query) == "en":
                    response_text = (
                        "Yes. Relevant visuals from the course documents are below."
                        if images
                        else "I could not find a reviewed visual for the retrieved pages."
                    )
                else:
                    response_text = (
                        "มีครับ ภาพประกอบจากเอกสารที่เกี่ยวข้องอยู่ด้านล่าง"
                        if images
                        else "จากหน้าที่ค้นเจอ ตอนนี้ไม่พบภาพประกอบที่ดึงมาแสดงได้ครับ"
                    )
                st.markdown(response_text)
                timing["ttft_ms"] = (perf_counter() - request_started) * 1000.0
            else:
                stream = service.stream_answer(
                    query=user_query,
                    result=result,
                    history=history_before,
                    model_name=settings.generation_model,
                    language_mode=response_language,
                )
                response_text = st.write_stream(
                    track_stream(
                        stream,
                        timing,
                        request_started,
                        thinking_placeholder,
                    )
                ) or ""
                thinking_placeholder.empty()

            total_ms = (perf_counter() - request_started) * 1000.0
            ttft_ms = timing["ttft_ms"] or total_ms

            answer_sources = (
                compact_sources(result.hits)
                if answered and result.retrieval_query != "__conversation__"
                else []
            )
            render_sources(answer_sources)

            render_message_images(
                image_payload,
                visual_request=visual_request,
            )

            if show_debug:
                with st.expander("RAG debug"):
                    st.write(
                        {
                            "retrieval_query": result.retrieval_query,
                            "retrieval_ms": round(result.elapsed_ms, 1),
                            "ttft_ms": round(ttft_ms, 1),
                            "total_ms": round(total_ms, 1),
                            "top_score": round(result.top_score, 4),
                            "answerable": answered,
                            "pages": result.pages,
                        }
                    )
                    st.dataframe(
                        [
                            {
                                "page": hit.page_number,
                                "score": round(hit.score, 4),
                                "vector": round(hit.vector_score, 4),
                                "lexical": round(hit.lexical_score, 4),
                                "preview": hit.content[:180],
                            }
                            for hit in result.hits
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

            append_answer_and_log(
                st.session_state["messages"],
                {
                    "role": "assistant",
                    "content": response_text,
                    "sources": answer_sources,
                    "images": image_payload,
                    "visual_request": visual_request,
                },
                service.store,
                {
                    "query": user_query,
                    "retrieval_ms": result.elapsed_ms,
                    "ttft_ms": ttft_ms,
                    "total_ms": total_ms,
                    "top_score": result.top_score,
                    "answered": answered,
                    "model_name": settings.generation_model,
                    "pages": result.pages,
                    "answer_chars": len(response_text),
                },
            )

            if history_backend and history_ready and identity and identity.get("persisted"):
                queued = queue_pending_history_save(
                    st.session_state,
                    identity["token"],
                    active_persona.id,
                    user_query,
                    response_text,
                    {"sources": answer_sources, "images": image_payload,
                     "visual_request": visual_request},
                )
                if queued:
                    retry_pending_history_saves(
                        st.session_state,
                        history_backend,
                        identity["token"],
                        active_persona.id,
                    )
            else:
                set_history_save_status(
                    st.session_state,
                    identity["token"] if identity else None,
                    active_persona.id,
                    "session_only",
                )

            # Re-render the completed exchange from session history so the
            # streamed assistant block does not remain as a stale/ghost
            # element during the next Streamlit rerun.
            st.rerun()

        except Exception as exc:
            if "thinking_placeholder" in locals():
                thinking_placeholder.empty()
            error_text = (
                "เกิดข้อผิดพลาดระหว่างค้นข้อมูลหรือสร้างคำตอบ: "
                f"{type(exc).__name__}: {exc}"
            )
            st.error(error_text)
            st.session_state["messages"].append(
                {"role": "assistant", "content": error_text}
            )
