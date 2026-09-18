from __future__ import annotations

from html import escape

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
<style>
:root {
    --tutor-ink: #172033;
    --tutor-muted: #667085;
    --tutor-blue: #4263eb;
    --tutor-indigo: #7048e8;
    --tutor-surface: rgba(255, 255, 255, 0.88);
    --tutor-border: rgba(66, 99, 235, 0.12);
    --tutor-shadow: 0 18px 50px rgba(31, 45, 74, 0.09);
}

#MainMenu, footer {visibility: hidden;}

.block-container {
    max-width: 920px !important;
    padding-top: 1.15rem !important;
    padding-bottom: 7rem !important;
    padding-left: clamp(.75rem, 2.5vw, 1.35rem) !important;
    padding-right: clamp(.75rem, 2.5vw, 1.35rem) !important;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 10% 0%, rgba(112,72,232,.07), transparent 30rem),
        radial-gradient(circle at 95% 8%, rgba(66,99,235,.07), transparent 28rem);
}

.tutor-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 112px;
    gap: 1.15rem;
    align-items: center;
    background: var(--tutor-surface);
    border: 1px solid var(--tutor-border);
    border-radius: 24px;
    padding: clamp(1.05rem, 3vw, 1.55rem);
    box-shadow: var(--tutor-shadow);
    margin-bottom: .85rem;
    backdrop-filter: blur(12px);
}

.tutor-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .02em;
    color: var(--tutor-blue);
    background: rgba(66,99,235,.08);
    border-radius: 999px;
    padding: .3rem .58rem;
    margin-bottom: .55rem;
}

.tutor-title {
    color: var(--tutor-ink);
    font-size: clamp(1.55rem, 4.2vw, 2.25rem);
    line-height: 1.16;
    font-weight: 800;
    letter-spacing: -.035em;
    margin: 0;
}

.tutor-subtitle {
    color: var(--tutor-muted);
    font-size: clamp(.88rem, 2.4vw, 1rem);
    line-height: 1.65;
    margin: .55rem 0 0;
    max-width: 680px;
}

.tutor-mascot-wrap {
    position: relative;
    display: grid;
    place-items: center;
    min-height: 96px;
}

.tutor-mascot {
    width: 78px;
    height: 68px;
    border-radius: 24px 24px 28px 28px;
    background: linear-gradient(145deg, #597ef7, #7950f2);
    box-shadow: 0 12px 28px rgba(66,99,235,.25);
    position: relative;
    animation: tutorFloat 4.8s ease-in-out infinite;
}

.tutor-mascot::before {
    content: "";
    position: absolute;
    width: 34px;
    height: 9px;
    left: 22px;
    top: -8px;
    background: #4c6ef5;
    border-radius: 999px 999px 0 0;
}

.tutor-mascot-eyes {
    position: absolute;
    left: 17px;
    top: 22px;
    display: flex;
    gap: 18px;
}

.tutor-eye {
    width: 10px;
    height: 12px;
    background: white;
    border-radius: 999px;
    animation: tutorBlink 5.5s infinite;
}

.tutor-mouth {
    position: absolute;
    width: 24px;
    height: 10px;
    left: 27px;
    top: 44px;
    border-bottom: 3px solid rgba(255,255,255,.94);
    border-radius: 0 0 50% 50%;
}

.tutor-spark {
    position: absolute;
    right: 5px;
    top: 0;
    font-size: 1.1rem;
    color: #f59f00;
    animation: tutorPulse 2.6s ease-in-out infinite;
}

.tutor-status-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: .45rem;
    margin: 0 0 .9rem;
}

.tutor-chip {
    display: inline-flex;
    align-items: center;
    gap: .3rem;
    border: 1px solid rgba(102,112,133,.16);
    background: rgba(255,255,255,.72);
    color: #667085;
    border-radius: 999px;
    padding: .24rem .55rem;
    font-size: .75rem;
}

.tutor-welcome {
    border: 1px solid var(--tutor-border);
    background: rgba(255,255,255,.80);
    border-radius: 18px;
    padding: .9rem 1rem;
    color: var(--tutor-muted);
    line-height: 1.6;
    margin: .2rem 0 .8rem;
}

[data-testid="stChatMessage"] {
    border: 1px solid rgba(15,23,42,.06);
    border-radius: 18px;
    padding: .72rem .82rem;
    margin-bottom: .55rem;
    background: rgba(255,255,255,.78);
    box-shadow: 0 5px 18px rgba(31,45,74,.035);
}

[data-testid="stChatMessageContent"] {
    line-height: 1.72;
}

[data-testid="stChatMessageContent"] p {
    margin-bottom: .55rem;
}

div[data-testid="stChatInput"] {
    border-radius: 18px;
}

div.stButton > button {
    border-radius: 14px;
    min-height: 2.55rem;
    border-color: rgba(66,99,235,.14);
    transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}

div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 18px rgba(66,99,235,.09);
    border-color: rgba(66,99,235,.30);
}

[data-testid="stSidebar"] {
    border-right: 1px solid rgba(66,99,235,.08);
}

@keyframes tutorFloat {
    0%,100% { transform: translateY(0) rotate(-1deg); }
    50% { transform: translateY(-7px) rotate(1deg); }
}

@keyframes tutorBlink {
    0%, 46%, 50%, 100% { transform: scaleY(1); }
    48% { transform: scaleY(.12); }
}

@keyframes tutorPulse {
    0%,100% { transform: scale(.9) rotate(0deg); opacity: .6; }
    50% { transform: scale(1.12) rotate(8deg); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
    .tutor-mascot, .tutor-eye, .tutor-spark,
    div.stButton > button {
        animation: none !important;
        transition: none !important;
        transform: none !important;
    }
}

@media (max-width: 640px) {
    .tutor-hero {
        grid-template-columns: 1fr 78px;
        border-radius: 20px;
        gap: .55rem;
    }
    .tutor-mascot {
        width: 62px;
        height: 56px;
        border-radius: 20px 20px 23px 23px;
    }
    .tutor-mascot::before {
        width: 26px;
        left: 18px;
    }
    .tutor-mascot-eyes {
        left: 13px;
        top: 18px;
        gap: 14px;
    }
    .tutor-eye { width: 8px; height: 10px; }
    .tutor-mouth { width: 20px; left: 21px; top: 36px; }
}

@media (prefers-color-scheme: dark) {
    :root {
        --tutor-ink: #f1f5f9;
        --tutor-muted: #b7c0ce;
        --tutor-surface: rgba(20, 25, 38, .82);
        --tutor-border: rgba(134, 157, 255, .16);
        --tutor-shadow: 0 18px 50px rgba(0,0,0,.20);
    }
    [data-testid="stChatMessage"] {
        background: rgba(20,25,38,.72);
        border-color: rgba(255,255,255,.06);
    }
    .tutor-chip {
        background: rgba(20,25,38,.72);
        color: #bdc7d6;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_hero(
    *,
    course_title: str,
    course_level: str,
    tutor_name: str,
    mascot_symbol: str,
    student_name: str | None = None,
) -> None:
    greeting = (
        f"สวัสดี {escape(student_name)} · "
        if student_name
        else ""
    )
    st.markdown(
        f"""
<section class="tutor-hero">
  <div>
    <div class="tutor-eyebrow">AI TUTOR · {escape(course_level)}</div>
    <h1 class="tutor-title">{escape(course_title)}</h1>
    <p class="tutor-subtitle">
      {greeting}{escape(tutor_name)} ช่วยค้นคำตอบจากเอกสารรายวิชา อธิบายให้เห็นภาพ
      และอ้างอิงหน้าที่เกี่ยวข้องโดยไม่ยัดเนื้อหาที่คุณไม่ได้ถาม
    </p>
  </div>
  <div class="tutor-mascot-wrap" aria-hidden="true">
    <span class="tutor-spark">{escape(mascot_symbol)}</span>
    <div class="tutor-mascot">
      <div class="tutor-mascot-eyes">
        <span class="tutor-eye"></span><span class="tutor-eye"></span>
      </div>
      <div class="tutor-mouth"></div>
    </div>
  </div>
</section>
""",
        unsafe_allow_html=True,
    )


def render_welcome_panel(tutor_name: str) -> None:
    st.markdown(
        f"""
<div class="tutor-welcome">
  <b>{escape(tutor_name)} พร้อมแล้ว</b> — ถามเป็นภาษาธรรมชาติได้เลย
  ถ้าข้อมูลไม่มีในเอกสาร ระบบควรบอกว่าไม่พบข้อมูล แทนการเดาคำตอบ
</div>
""",
        unsafe_allow_html=True,
    )
