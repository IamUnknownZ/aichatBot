from __future__ import annotations

from html import escape

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
<style>
:root {
    --ink: #182033;
    --ink-soft: #344054;
    --muted: #697386;
    --line: rgba(31, 41, 55, .09);
    --line-strong: rgba(79, 70, 229, .16);
    --surface: rgba(255, 255, 255, .88);
    --surface-solid: #ffffff;
    --surface-soft: #f7f8fc;
    --accent: #5b5bd6;
    --accent-2: #7c5ce7;
    --accent-soft: rgba(91, 91, 214, .09);
    --success: #15956f;
    --shadow-soft: 0 12px 34px rgba(31, 42, 70, .07);
    --shadow-composer: 0 16px 44px rgba(31, 42, 70, .12);
}

html {
    scroll-behavior: smooth;
}

body,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[data-testid="stMarkdownContainer"],
[data-testid="stChatMessageContent"],
button,
input,
textarea {
    font-family:
        -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans Thai",
        Tahoma, Arial, sans-serif !important;
}

#MainMenu,
footer {
    visibility: hidden;
}

[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 15% -8%, rgba(91,91,214,.08), transparent 30rem),
        radial-gradient(circle at 93% 2%, rgba(124,92,231,.055), transparent 25rem),
        linear-gradient(180deg, #fbfbfe 0%, #f8f9fc 48%, #fbfcfe 100%);
}

[data-testid="stHeader"] {
    background: transparent;
}

.block-container {
    max-width: 900px !important;
    padding-top: .75rem !important;
    padding-left: clamp(.9rem, 3vw, 1.65rem) !important;
    padding-right: clamp(.9rem, 3vw, 1.65rem) !important;
    padding-bottom: 8.5rem !important;
}

/* ----- compact learning workspace header ----- */
.tutor-hero {
    display: flex;
    align-items: center;
    gap: .9rem;
    min-height: 82px;
    padding: .7rem .15rem 1rem;
    border-bottom: 1px solid var(--line);
    margin-bottom: .55rem;
}

.tutor-brandmark {
    flex: 0 0 auto;
    width: 48px;
    height: 48px;
    display: grid;
    place-items: center;
    border-radius: 16px;
    position: relative;
    background: linear-gradient(145deg, #5b5bd6, #8062e9);
    box-shadow: 0 10px 24px rgba(91,91,214,.20);
}

.tutor-brandmark::after {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 999px;
    position: absolute;
    right: -1px;
    bottom: 3px;
    background: #28b487;
    border: 2px solid #fbfbfe;
}

.tutor-face {
    width: 27px;
    height: 22px;
    border-radius: 9px 9px 11px 11px;
    border: 2px solid rgba(255,255,255,.96);
    position: relative;
}

.tutor-face::before,
.tutor-face::after {
    content: "";
    position: absolute;
    top: 6px;
    width: 4px;
    height: 5px;
    border-radius: 999px;
    background: white;
    animation: tutorBlink 5.6s infinite;
}

.tutor-face::before { left: 5px; }
.tutor-face::after { right: 5px; }

.tutor-header-copy {
    min-width: 0;
    flex: 1;
}

.tutor-eyebrow {
    color: var(--accent);
    font-size: .72rem;
    line-height: 1.3;
    letter-spacing: .055em;
    text-transform: uppercase;
    font-weight: 750;
    margin-bottom: .2rem;
}

.tutor-title {
    color: var(--ink);
    margin: 0;
    font-size: clamp(1.15rem, 3.1vw, 1.55rem);
    line-height: 1.25;
    letter-spacing: -.025em;
    font-weight: 780;
}

.tutor-subtitle {
    color: var(--muted);
    margin: .28rem 0 0;
    line-height: 1.55;
    font-size: .84rem;
}

.tutor-header-meta {
    flex: 0 0 auto;
    text-align: right;
    color: var(--muted);
    font-size: .72rem;
    line-height: 1.5;
}

.tutor-header-meta strong {
    color: var(--ink-soft);
    font-weight: 650;
    display: block;
}

/* ----- quiet trust/status line ----- */
.tutor-status-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: .4rem;
    min-height: 30px;
    margin: 0 0 .75rem;
}

.tutor-chip {
    display: inline-flex;
    align-items: center;
    gap: .28rem;
    color: var(--muted);
    background: transparent;
    border: 0;
    border-right: 1px solid var(--line);
    padding: .08rem .5rem .08rem 0;
    font-size: .72rem;
    line-height: 1.35;
}

.tutor-chip:last-child {
    border-right: 0;
}

.tutor-chip:first-child {
    color: var(--success);
    font-weight: 650;
}

/* ----- empty state ----- */
.tutor-welcome {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--line);
    background: rgba(255,255,255,.68);
    border-radius: 19px;
    padding: 1.15rem 1.2rem;
    color: var(--muted);
    line-height: 1.7;
    margin: .3rem 0 .75rem;
    box-shadow: 0 8px 26px rgba(31,42,70,.035);
}

.tutor-welcome::before {
    content: "";
    position: absolute;
    width: 3px;
    left: 0;
    top: 14px;
    bottom: 14px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
}

.tutor-welcome-title {
    display: block;
    color: var(--ink);
    font-size: .96rem;
    font-weight: 720;
    margin-bottom: .16rem;
}

/* ----- texting-app conversation hierarchy ----- */
[data-testid="stChatMessage"] {
    border: 0;
    background: transparent;
    box-shadow: none;
    padding: .32rem 0;
    margin-bottom: .38rem;
    display: flex;
    align-items: flex-start;
    gap: .5rem;
}

/* User = right */
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
) {
    width: fit-content;
    max-width: min(78%, 650px);
    margin-left: auto;
    margin-right: 0;
    padding: .68rem .92rem;
    border: 1px solid rgba(91,91,214,.12);
    border-radius: 18px 18px 5px 18px;
    background: linear-gradient(145deg, rgba(91,91,214,.12), rgba(124,92,231,.08));
    box-shadow: 0 6px 18px rgba(91,91,214,.055);
    flex-direction: row-reverse;
}

/* Sorty = left */
[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]
) {
    width: fit-content;
    max-width: min(86%, 720px);
    margin-left: 0;
    margin-right: auto;
    padding: .74rem .95rem;
    border: 1px solid var(--line);
    border-radius: 18px 18px 18px 5px;
    background: rgba(255,255,255,.78);
    box-shadow: 0 7px 22px rgba(31,42,70,.045);
}

/* Keep emoji avatar visually attached to its own side */
[data-testid="stChatMessage"] > :first-child {
    transform: scale(.84);
    flex: 0 0 auto;
}

[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
) > :first-child {
    margin-left: .08rem;
}

[data-testid="stChatMessage"]:has(
    [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]
) > :first-child {
    margin-right: .08rem;
}

[data-testid="stChatMessageContent"] {
    color: var(--ink-soft);
    font-size: .96rem;
    line-height: 1.76;
}

[data-testid="stChatMessageContent"] p {
    margin-bottom: .62rem;
}

[data-testid="stChatMessageContent"] h1,
[data-testid="stChatMessageContent"] h2,
[data-testid="stChatMessageContent"] h3 {
    color: var(--ink);
    letter-spacing: -.018em;
    margin-top: 1rem;
    margin-bottom: .45rem;
}

[data-testid="stChatMessageContent"] ul,
[data-testid="stChatMessageContent"] ol {
    padding-left: 1.3rem;
}

[data-testid="stChatMessageContent"] code {
    border-radius: 7px;
}

[data-testid="stChatMessageContent"] pre {
    border: 1px solid var(--line);
    border-radius: 14px;
}

[data-testid="stChatMessageContent"] table {
    border-radius: 12px;
    overflow: hidden;
}

/* Evidence is secondary, but visibly available */
[data-testid="stChatMessage"] [data-testid="stExpander"] {
    margin-top: .42rem;
    border: 1px solid var(--line) !important;
    border-radius: 13px !important;
    background: rgba(248,249,252,.72);
    box-shadow: none !important;
}

[data-testid="stChatMessage"] [data-testid="stExpander"] summary {
    color: var(--muted);
    font-size: .78rem;
}

/* ----- thinking / typing feedback ----- */
.tutor-thinking {
    display: inline-flex;
    align-items: center;
    gap: .48rem;
    min-height: 34px;
    padding: .35rem .65rem;
    border-radius: 12px;
    color: var(--muted);
    background: rgba(255,255,255,.58);
    border: 1px solid var(--line);
    font-size: .78rem;
    margin: .15rem 0 .45rem;
}

.tutor-thinking-orb {
    color: var(--accent);
    font-size: .78rem;
    animation: tutorPulse 2.2s ease-in-out infinite;
}

.tutor-thinking-dots {
    display: inline-flex;
    align-items: center;
    gap: 3px;
}

.tutor-thinking-dots i {
    display: block;
    width: 4px;
    height: 4px;
    border-radius: 999px;
    background: #8b91a1;
    animation: thinkingDot 1.15s ease-in-out infinite;
}

.tutor-thinking-dots i:nth-child(2) { animation-delay: .13s; }
.tutor-thinking-dots i:nth-child(3) { animation-delay: .26s; }

/* ----- composer ----- */
[data-testid="stBottom"] {
    background:
        linear-gradient(180deg, rgba(248,249,252,0), rgba(248,249,252,.96) 31%, rgba(248,249,252,.99) 100%);
    padding-top: 1.4rem;
}

div[data-testid="stChatInput"] {
    border: 1px solid rgba(91,91,214,.14);
    border-radius: 19px;
    background: rgba(255,255,255,.96);
    box-shadow: var(--shadow-composer);
    backdrop-filter: blur(14px);
}

div[data-testid="stChatInput"]:focus-within {
    border-color: rgba(91,91,214,.32);
    box-shadow: 0 17px 48px rgba(64,64,150,.15);
}

/* ----- prompt cards/buttons ----- */
div.stButton > button {
    border-radius: 13px;
    min-height: 2.65rem;
    border: 1px solid var(--line);
    background: rgba(255,255,255,.74);
    color: var(--ink-soft);
    box-shadow: none;
    justify-content: flex-start;
    text-align: left;
    transition: transform .14s ease, border-color .14s ease, background .14s ease;
}

div.stButton > button:hover {
    transform: translateY(-1px);
    border-color: rgba(91,91,214,.24);
    background: white;
    color: var(--ink);
}

div.stButton > button:active {
    transform: translateY(0);
}

/* ----- sidebar ----- */
[data-testid="stSidebar"] {
    background: rgba(250,250,253,.97);
    border-right: 1px solid var(--line);
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: .55rem;
}

[data-testid="stSidebar"] .stButton > button {
    min-height: 2.35rem;
    border-radius: 11px;
    background: transparent;
}

[data-testid="stSidebar"] [data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: rgba(255,255,255,.54);
}

/* ----- dialogs and form controls ----- */
[data-testid="stDialog"] > div {
    border-radius: 22px;
}

[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {
    border-radius: 12px !important;
}

/* ----- motion ----- */
@keyframes tutorBlink {
    0%, 45%, 49%, 100% { transform: scaleY(1); }
    47% { transform: scaleY(.12); }
}

@keyframes tutorPulse {
    0%,100% { transform: scale(.92); opacity: .55; }
    50% { transform: scale(1.08); opacity: 1; }
}

@keyframes thinkingDot {
    0%, 60%, 100% { transform: translateY(0); opacity: .35; }
    30% { transform: translateY(-3px); opacity: 1; }
}

@media (max-width: 700px) {
    .block-container {
        padding-top: .45rem !important;
        padding-left: .75rem !important;
        padding-right: .75rem !important;
        padding-bottom: 8rem !important;
    }

    .tutor-hero {
        min-height: 72px;
        padding-bottom: .75rem;
    }

    .tutor-brandmark {
        width: 42px;
        height: 42px;
        border-radius: 14px;
    }

    .tutor-title {
        font-size: 1.08rem;
    }

    .tutor-subtitle {
        font-size: .78rem;
        line-height: 1.45;
    }

    .tutor-header-meta {
        display: none;
    }

    .tutor-status-row {
        margin-bottom: .5rem;
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
    ) {
        max-width: 88%;
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]
    ) {
        max-width: 92%;
    }

    .tutor-welcome {
        border-radius: 16px;
        padding: .95rem 1rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; }

    .tutor-face::before,
    .tutor-face::after,
    .tutor-thinking-orb,
    .tutor-thinking-dots i {
        animation: none !important;
    }

    div.stButton > button {
        transition: none !important;
        transform: none !important;
    }
}

@media (prefers-color-scheme: dark) {
    :root {
        --ink: #f2f4f8;
        --ink-soft: #d5dae4;
        --muted: #9ca5b5;
        --line: rgba(255,255,255,.085);
        --line-strong: rgba(145,135,255,.18);
        --surface: rgba(20,23,31,.88);
        --surface-solid: #151820;
        --surface-soft: #191c25;
        --accent: #9b91ff;
        --accent-2: #b08cff;
        --accent-soft: rgba(155,145,255,.11);
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 15% -8%, rgba(100,90,220,.12), transparent 30rem),
            linear-gradient(180deg, #11141b 0%, #151821 100%);
    }

    .tutor-brandmark::after {
        border-color: #11141b;
    }

    .tutor-welcome,
    .tutor-thinking,
    div.stButton > button {
        background: rgba(25,28,38,.72);
    }

    div[data-testid="stChatInput"] {
        background: rgba(25,28,38,.96);
    }

    [data-testid="stBottom"] {
        background: linear-gradient(180deg, rgba(17,20,27,0), rgba(17,20,27,.97) 32%);
    }

    [data-testid="stSidebar"] {
        background: rgba(17,20,27,.98);
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageContent"][aria-label="Chat message from assistant"]
    ) {
        background: rgba(30, 34, 46, .96);
        border-color: rgba(255,255,255,.09);
        box-shadow: 0 8px 24px rgba(0,0,0,.16);
    }

    [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageContent"][aria-label="Chat message from user"]
    ) {
        background: linear-gradient(
            145deg,
            rgba(112, 102, 230, .28),
            rgba(132, 90, 220, .20)
        );
        border-color: rgba(166, 154, 255, .18);
    }

    [data-testid="stChatMessageContent"],
    [data-testid="stChatMessageContent"] p,
    [data-testid="stChatMessageContent"] li {
        color: #e6e9f0 !important;
    }

    [data-testid="stChatMessageContent"] strong,
    [data-testid="stChatMessageContent"] h1,
    [data-testid="stChatMessageContent"] h2,
    [data-testid="stChatMessageContent"] h3 {
        color: #f7f8fb !important;
    }

    [data-testid="stChatMessage"] [data-testid="stExpander"] {
        background: rgba(24,27,36,.92);
        border-color: rgba(255,255,255,.08) !important;
    }

    [data-testid="stChatMessage"] [data-testid="stExpander"] summary {
        color: #c5cad5 !important;
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
<header class="tutor-hero">
  <div class="tutor-brandmark" aria-hidden="true">
    <div class="tutor-face"></div>
  </div>

  <div class="tutor-header-copy">
    <div class="tutor-eyebrow">{escape(tutor_name)} · AI Tutor</div>
    <h1 class="tutor-title">{escape(course_title)}</h1>
    <p class="tutor-subtitle">
      {greeting}ถามสั้น ๆ หรือพิมพ์คำทับศัพท์ได้ ระบบจะช่วยตีความก่อนค้นจากเอกสาร
    </p>
  </div>

  <div class="tutor-header-meta">
    <strong>{escape(course_level)}</strong>
    ฐานความรู้รายวิชา
  </div>
</header>
""",
        unsafe_allow_html=True,
    )


def render_welcome_panel(tutor_name: str) -> None:
    st.markdown(
        f"""
<div class="tutor-welcome">
  <span class="tutor-welcome-title">เริ่มถาม {escape(tutor_name)} ได้เลย</span>
  พิมพ์แบบธรรมชาติก็ได้ เช่น “บับเบิลซอร์ท”, “ต่างจาก Selection Sort ยังไง”
  หรือ “ช่วย Trace 5, 1, 4, 2” — ถ้าข้อมูลไม่มีในเอกสาร ระบบจะไม่เดาคำตอบให้
</div>
""",
        unsafe_allow_html=True,
    )
