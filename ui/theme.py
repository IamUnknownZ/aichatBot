from __future__ import annotations

from html import escape

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
<style>
:root {
    --tutor-ink: #111827;
    --tutor-muted: #697386;
    --tutor-blue: #4f6ef7;
    --tutor-indigo: #7657f6;
    --tutor-cyan: #35b9d4;
    --tutor-surface: rgba(255, 255, 255, 0.88);
    --tutor-border: rgba(79, 110, 247, 0.13);
    --tutor-shadow: 0 22px 60px rgba(49, 61, 100, 0.10);
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
        radial-gradient(circle at 14% -8%, rgba(118,87,246,.12), transparent 31rem),
        radial-gradient(circle at 92% 6%, rgba(53,185,212,.10), transparent 27rem),
        linear-gradient(180deg, #fbfcff 0%, #f7f9ff 44%, #ffffff 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

.tutor-hero {
    position: relative;
    overflow: hidden;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 172px;
    gap: 1.15rem;
    align-items: center;
    background:
        linear-gradient(135deg, rgba(255,255,255,.96), rgba(246,248,255,.90));
    border: 1px solid var(--tutor-border);
    border-radius: 28px;
    padding: clamp(1.15rem, 3vw, 1.75rem);
    box-shadow: var(--tutor-shadow);
    margin-bottom: .8rem;
    backdrop-filter: blur(16px);
}

.tutor-hero::after {
    content: "";
    position: absolute;
    width: 210px;
    height: 210px;
    right: -82px;
    top: -105px;
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(79,110,247,.15), rgba(53,185,212,.10));
    pointer-events: none;
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
    z-index: 1;
    display: grid;
    place-items: center;
    min-height: 126px;
    border: 1px solid rgba(79,110,247,.10);
    border-radius: 22px;
    background: linear-gradient(180deg, rgba(255,255,255,.72), rgba(245,247,255,.88));
    box-shadow: inset 0 1px 0 rgba(255,255,255,.9);
}

.tutor-mascot {
    width: 76px;
    height: 66px;
    border-radius: 25px 25px 29px 29px;
    background: linear-gradient(145deg, #5878f7, #7657f6);
    box-shadow: 0 13px 28px rgba(79,110,247,.24);
    position: relative;
    animation: tutorFloat 5.2s ease-in-out infinite;
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
    right: 12px;
    top: 8px;
    font-size: 1rem;
    color: #f59f00;
    animation: tutorPulse 2.8s ease-in-out infinite;
}

.tutor-sort-bars {
    position: absolute;
    left: 50%;
    bottom: 10px;
    transform: translateX(-50%);
    display: flex;
    align-items: end;
    gap: 4px;
    height: 24px;
}

.tutor-sort-bar {
    width: 7px;
    border-radius: 4px 4px 2px 2px;
    background: linear-gradient(180deg, rgba(53,185,212,.95), rgba(79,110,247,.92));
    opacity: .78;
    animation: sortPulse 4.8s ease-in-out infinite;
}

.tutor-sort-bar:nth-child(1) { height: 9px; animation-delay: -.8s; }
.tutor-sort-bar:nth-child(2) { height: 20px; animation-delay: -1.6s; }
.tutor-sort-bar:nth-child(3) { height: 13px; animation-delay: -2.4s; }
.tutor-sort-bar:nth-child(4) { height: 23px; animation-delay: -3.2s; }
.tutor-sort-bar:nth-child(5) { height: 16px; animation-delay: -4s; }

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
    border: 1px solid rgba(15,23,42,.055);
    border-radius: 20px;
    padding: .78rem .9rem;
    margin-bottom: .7rem;
    background: rgba(255,255,255,.82);
    box-shadow: 0 8px 24px rgba(31,45,74,.045);
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    margin-left: clamp(2rem, 9vw, 6rem);
    background: linear-gradient(135deg, rgba(79,110,247,.10), rgba(118,87,246,.08));
    border-color: rgba(79,110,247,.13);
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    margin-right: clamp(.5rem, 5vw, 3rem);
}

[data-testid="stChatMessageContent"] {
    line-height: 1.78;
    font-size: .98rem;
}

[data-testid="stChatMessageContent"] p {
    margin-bottom: .55rem;
}

div[data-testid="stChatInput"] {
    border-radius: 20px;
    border: 1px solid rgba(79,110,247,.14);
    background: rgba(255,255,255,.92);
    box-shadow: 0 14px 40px rgba(31,45,74,.10);
    backdrop-filter: blur(16px);
}

[data-testid="stBottom"] {
    background: linear-gradient(180deg, rgba(255,255,255,0), rgba(248,250,255,.94) 34%);
    padding-top: 1rem;
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
    50% { transform: scale(1.10) rotate(7deg); opacity: 1; }
}

@keyframes sortPulse {
    0%,100% { transform: scaleY(.86); opacity: .55; }
    50% { transform: scaleY(1.05); opacity: .90; }
}

@media (prefers-reduced-motion: reduce) {
    .tutor-mascot, .tutor-eye, .tutor-spark, .tutor-sort-bar,
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
    <div class="tutor-sort-bars">
      <span class="tutor-sort-bar"></span>
      <span class="tutor-sort-bar"></span>
      <span class="tutor-sort-bar"></span>
      <span class="tutor-sort-bar"></span>
      <span class="tutor-sort-bar"></span>
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
  <b>{escape(tutor_name)} พร้อมแล้ว</b> — พิมพ์สั้น ๆ ก็ได้ เช่น “บับเบิลซอร์ท”
  หรือถามต่อเนื่องแบบ “แล้วมันต่างกันยังไง” ระบบจะช่วยตีความก่อนค้นจากเอกสาร
</div>
""",
        unsafe_allow_html=True,
    )
