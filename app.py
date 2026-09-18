import json
import os
from time import perf_counter
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from rag.bootstrap import build_rag_service
from rag.config import Settings
from ui import inject_theme, render_hero, render_welcome_panel


load_dotenv()
page_settings = Settings.from_env()

st.set_page_config(
    page_title=f"{page_settings.course_title} · AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()


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


def track_stream(stream, timing: dict[str, float | None], started: float):
    for chunk in stream:
        if timing["ttft_ms"] is None:
            timing["ttft_ms"] = (perf_counter() - started) * 1000.0
        yield chunk


def render_copy_button(text_to_copy: str, element_id: str) -> None:
    escaped_text = json.dumps(text_to_copy)
    html_code = f"""
    <div style="display:flex;justify-content:flex-end;margin-top:2px;margin-bottom:4px;">
        <button id="copy_btn_{element_id}" onclick='
            navigator.clipboard.writeText({escaped_text}).then(() => {{
                const btn = document.getElementById("copy_btn_{element_id}");
                btn.innerHTML = "✓ คัดลอกแล้ว";
                setTimeout(() => btn.innerHTML = "คัดลอกคำตอบ", 1500);
            }});
        ' style="
            background:transparent;color:#667085;border:1px solid rgba(102,112,133,.18);
            border-radius:10px;padding:4px 9px;font-size:12px;
            font-family:inherit;cursor:pointer;">
            คัดลอกคำตอบ
        </button>
    </div>
    """
    components.html(html_code, height=32)


@st.cache_resource(show_spinner=False)
def create_rag_service(api_key: str, database_url: str):
    settings = Settings.from_env(
        api_key=api_key,
        database_url=database_url,
    )
    service = build_rag_service(settings)
    return service, settings


def refresh_recent_questions(service, settings) -> list[str]:
    profile = st.session_state.get("profile")
    if not profile:
        return []
    try:
        return service.store.get_recent_questions(
            profile["user_id"],
            limit=settings.recent_question_limit,
        )
    except Exception:
        return []


def ensure_chat_state(settings: Settings) -> None:
    if "chat_session_id" not in st.session_state:
        st.session_state["chat_session_id"] = str(uuid4())

    if "messages" not in st.session_state or not st.session_state["messages"]:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    f"ถามเรื่อง **{settings.course_title}** ได้เลยครับ "
                    "ผมจะค้นจากเอกสารรายวิชาก่อนตอบ และถ้าข้อมูลไม่พอจะบอกตรง ๆ"
                ),
            }
        ]


api_key = get_secret("GEMINI_API_KEY")
database_url = get_secret("DATABASE_URL")

service = None
settings = page_settings
service_error = None

if api_key:
    try:
        with st.spinner("กำลังเชื่อมต่อฐานความรู้..."):
            service, settings = create_rag_service(api_key, database_url)
    except Exception as exc:
        service_error = f"{type(exc).__name__}: {exc}"


if service is not None and settings.profile_enabled:

    @st.dialog("ยินดีต้อนรับ 👋", width="small")
    def profile_dialog():
        st.write(
            f"ก่อนเริ่มคุยกับ **{settings.tutor_name}** บอกชื่อที่อยากให้เรียกสั้น ๆ "
            "เพื่อให้ระบบจำประวัติคำถามของคุณได้"
        )
        with st.form("profile_form", border=False):
            display_name = st.text_input(
                "ชื่อ / ชื่อเล่น",
                placeholder="เช่น บาส",
                max_chars=40,
            )
            submitted = st.form_submit_button(
                "เริ่มเรียน",
                type="primary",
                use_container_width=True,
            )

        st.caption(
            "นี่เป็นโปรไฟล์เพื่อจดจำประวัติ ไม่ใช่ระบบยืนยันตัวตน "
            "ถ้าใช้ในห้องเรียนควรเลือกชื่อที่ไม่ซ้ำกับเพื่อน"
        )

        if submitted:
            name = display_name.strip()
            if not name:
                st.warning("กรอกชื่อก่อนเริ่มใช้งานครับ")
                return

            persisted = service.store_mode == "postgres-pgvector"
            try:
                profile = service.store.get_or_create_profile(name)
            except Exception:
                profile = None
                persisted = False

            if profile is None:
                profile = {
                    "user_id": str(uuid4()),
                    "display_name": name,
                }
                persisted = False

            st.session_state["profile"] = profile
            st.session_state["profile_persisted"] = persisted
            st.session_state["chat_session_id"] = str(uuid4())

            try:
                st.session_state["recent_questions"] = (
                    service.store.get_recent_questions(
                        profile["user_id"],
                        limit=settings.recent_question_limit,
                    )
                    if persisted
                    else []
                )
            except Exception:
                st.session_state["recent_questions"] = []

            st.rerun()


if settings.profile_enabled and service is not None and "profile" not in st.session_state:
    profile_dialog()
    st.stop()


ensure_chat_state(settings)

student_name = None
if st.session_state.get("profile"):
    student_name = st.session_state["profile"].get("display_name")

render_hero(
    course_title=settings.course_title,
    course_level=settings.course_level,
    tutor_name=settings.tutor_name,
    mascot_symbol=settings.mascot_emoji,
    student_name=student_name,
)

if service is not None:
    mode_label = (
        "PostgreSQL + pgvector"
        if service.store_mode == "postgres-pgvector"
        else "Local lexical RAG"
    )
    profile_label = (
        "จำประวัติแล้ว"
        if st.session_state.get("profile_persisted")
        else "ประวัติใน session"
    )
    st.markdown(
        f"""
<div class="tutor-status-row">
  <span class="tutor-chip">● ฐานความรู้พร้อม</span>
  <span class="tutor-chip">{mode_label}</span>
  <span class="tutor-chip">{profile_label}</span>
</div>
""",
        unsafe_allow_html=True,
    )
elif service_error:
    st.error(f"ระบบฐานความรู้ยังไม่พร้อม: {service_error}")
else:
    st.info("ยังไม่ได้ตั้งค่า GEMINI_API_KEY สำหรับระบบ AI")


with st.sidebar:
    if student_name:
        st.markdown(f"### 👋 {student_name}")
        st.caption(f"กำลังเรียน: {settings.course_title}")

    recent_questions = st.session_state.get("recent_questions", [])
    if recent_questions:
        st.markdown("#### คำถามล่าสุด")
        for idx, question in enumerate(recent_questions[: settings.recent_question_limit]):
            label = question if len(question) <= 44 else question[:41] + "…"
            if st.button(
                label,
                key=f"recent_question_{idx}",
                use_container_width=True,
            ):
                st.session_state["queued_prompt"] = question

    st.divider()

    if st.button("เริ่มแชตใหม่", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["chat_session_id"] = str(uuid4())
        st.rerun()

    if settings.profile_enabled and student_name:
        if st.button("เปลี่ยนชื่อ", use_container_width=True):
            for key in (
                "profile",
                "profile_persisted",
                "recent_questions",
                "messages",
                "chat_session_id",
            ):
                st.session_state.pop(key, None)
            st.rerun()

    with st.expander("Advanced", expanded=False):
        show_debug = st.checkbox(
            "แสดง RAG debug",
            value=False,
            help="ใช้ตอนพัฒนา/เก็บผลการทดลองบทที่ 4",
        )
        st.caption(f"Model: {settings.generation_model}")
        st.caption(
            f"top-k {settings.top_k} · threshold {settings.min_relevance_score:.2f}"
        )
        if service is not None and service.startup_note:
            st.warning(service.startup_note)

if "show_debug" not in locals():
    show_debug = False


messages = st.session_state["messages"]
for message in messages:
    role = "assistant" if message["role"] in {"assistant", "model"} else "user"
    avatar = "🧠" if role == "assistant" else "🙂"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])


preset_query = None
if service is not None and len(messages) <= 1:
    render_welcome_panel(settings.tutor_name)
    st.caption("ลองเริ่มด้วยคำถามเหล่านี้")
    quick_prompts = [
        ("เห็นภาพ", "อธิบาย Bubble Sort ให้เห็นภาพแบบเข้าใจง่าย"),
        ("เปรียบเทียบ", "Bubble Sort กับ Selection Sort ต่างกันอย่างไร"),
        ("Trace", "ช่วย Trace Bubble Sort กับข้อมูล 5, 1, 4, 2 ทีละรอบ"),
        ("Big-O", "สรุป Big-O ของอัลกอริทึมการเรียงลำดับในบทเรียน"),
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

    with st.chat_message("assistant", avatar="🧠"):
        try:
            request_started = perf_counter()
            with st.spinner("กำลังค้นส่วนที่เกี่ยวข้องในเอกสาร..."):
                result = service.retrieve(user_query, history_before)

            stream = service.stream_answer(
                query=user_query,
                result=result,
                history=history_before,
                model_name=settings.generation_model,
            )
            timing = {"ttft_ms": None}
            response_text = st.write_stream(
                track_stream(stream, timing, request_started)
            ) or ""

            total_ms = (perf_counter() - request_started) * 1000.0
            ttft_ms = timing["ttft_ms"] or total_ms
            answered = service.answerable(result)

            render_copy_button(
                response_text,
                f"latest_{len(st.session_state['messages'])}",
            )

            if settings.max_images_per_answer > 0:
                images = service.store.images_for_pages(
                    result.pages,
                    limit=settings.max_images_per_answer,
                )
                if images:
                    with st.expander("ภาพประกอบจากหน้าที่เกี่ยวข้อง"):
                        for image in images:
                            st.image(
                                image.image_bytes,
                                caption=f"หน้า {image.page_number}",
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

            st.session_state["messages"].append(
                {"role": "assistant", "content": response_text}
            )

            # Persist only after the visible response is complete.
            service.store.log_answer(
                query=user_query,
                retrieval_ms=result.elapsed_ms,
                ttft_ms=ttft_ms,
                total_ms=total_ms,
                top_score=result.top_score,
                answered=answered,
                model_name=settings.generation_model,
                pages=result.pages,
                answer_chars=len(response_text),
            )

            profile = st.session_state.get("profile")
            if profile:
                service.store.save_exchange(
                    user_id=profile["user_id"],
                    session_id=st.session_state["chat_session_id"],
                    question=user_query,
                    answer=response_text,
                    metadata={
                        "pages": result.pages,
                        "top_score": round(result.top_score, 6),
                        "answered": answered,
                        "retrieval_ms": round(result.elapsed_ms, 2),
                        "ttft_ms": round(ttft_ms, 2),
                        "total_ms": round(total_ms, 2),
                        "model": settings.generation_model,
                    },
                )

                recent = st.session_state.get("recent_questions", [])
                updated = [user_query] + [
                    q for q in recent if q.casefold() != user_query.casefold()
                ]
                st.session_state["recent_questions"] = updated[
                    : settings.recent_question_limit
                ]

        except Exception as exc:
            error_text = (
                "เกิดข้อผิดพลาดระหว่างค้นข้อมูลหรือสร้างคำตอบ: "
                f"{type(exc).__name__}: {exc}"
            )
            st.error(error_text)
            st.session_state["messages"].append(
                {"role": "assistant", "content": error_text}
            )
