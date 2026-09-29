"""Stitch-inspired presentation without copying its fictional people/features."""
from html import escape
from io import BytesIO
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


def persona_avatar(persona):
    image = Image.new('RGB', (96, 96), '#242d38')
    draw = ImageDraw.Draw(image)
    draw.ellipse((3, 3, 92, 92), fill=persona.color)
    font = ImageFont.truetype('DejaVuSans.ttf', 36)
    initials = 'ST' if persona.id == 'sabaitae' else persona.name[0]
    draw.text((48, 48), initials, fill='#14202b', font=font, anchor='mm')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def render_workspace_header(persona, course_title, student_name=None):
    greeting = f'สวัสดี {escape(student_name)} · ' if student_name else ''
    st.markdown(f'''<header class="workspace-header">
      <div class="workspace-avatar" style="background:{persona.color}">{escape(persona.name[0])}</div>
      <div><h1>{escape(persona.name)} <span class="workspace-badge">AI Tutor</span></h1>
      <p>{escape(persona.subtitle)} · {escape(course_title)}</p></div>
    </header><p class="workspace-intro">{greeting}เลือกเพื่อน AI แล้วถามจากเอกสารบทเรียนได้เลย</p>''', unsafe_allow_html=True)


def inject_workspace_theme():
    st.markdown('''<style>
:root {--ink:#e2e8f0;--muted:#94a3b8;--surface:#242d38;--accent:#38bdf8;}
[data-testid="stAppViewContainer"] {background:#1b222b !important;color:#e2e8f0;}
[data-testid="stSidebar"] {background:#192028 !important;border-right:1px solid #334050;}
[data-testid="stHeader"] {background:#1b222b !important;}
.block-container {max-width:1100px !important;padding-top:1.1rem !important;padding-bottom:10rem !important;}
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"] {color:#cbd5e1 !important;}
[data-testid="stMarkdownContainer"] h1,[data-testid="stMarkdownContainer"] h2,[data-testid="stMarkdownContainer"] h3 {color:#f1f5f9 !important;}
.workspace-header {display:flex;align-items:center;gap:16px;padding:12px 0 20px;border-bottom:1px solid #334050;margin-bottom:14px;}
.workspace-header h1 {font-size:22px;margin:0;color:#fff;}
.workspace-header p,.workspace-intro {font-size:13px;color:#94a3b8;margin:5px 0;}
.workspace-avatar {height:48px;width:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#14202b;font-weight:800;font-size:22px;flex-shrink:0;}
.workspace-badge {font-size:11px;padding:4px 8px;border-radius:6px;color:#38bdf8;background:#133443;vertical-align:middle;margin-left:8px;}
[data-testid="stSidebar"] [data-testid="stButton"] button {justify-content:flex-start;text-align:left;min-height:54px;border-radius:12px;background:transparent;border:1px solid transparent;color:#cbd5e1;}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {background:#2c3744;border-color:#334050;}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {background:#242d38;border-color:#38bdf866;color:white;}
[data-testid="stSidebar"] .block-container {padding-bottom:2rem !important;}
[data-testid="stChatMessage"] {background:transparent !important;border:0 !important;box-shadow:none !important;padding:16px 0 !important;}
[data-testid="stChatMessageContent"],[data-testid="stChatMessageContent"] p,[data-testid="stChatMessageContent"] li {color:#e2e8f0 !important;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {flex-direction:row-reverse; margin-left:auto;max-width:85%;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {background:#1d5485;border-radius:18px 4px 18px 18px;padding:14px 18px;}
[data-testid="stExpander"] {background:#242d38 !important;border:1px solid #334050 !important;border-radius:12px !important;}
[data-testid="stExpander"] summary {color:#cbd5e1 !important;}
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {background:#1b222b !important;}
[data-testid="stChatInput"] {background:#242d38 !important;border:1px solid #334050 !important;border-radius:14px !important;}
[data-testid="stChatInput"] textarea {color:#f1f5f9 !important;background:#242d38 !important;}
[data-testid="stChatInput"] textarea::placeholder {color:#94a3b8 !important;}
[data-testid="stButton"] button,[data-testid="stSegmentedControl"] button {color:#e2e8f0;}
div[class*="st-key-language-float"] {background:#242d38 !important;border-color:#334050 !important;}
.language-float-label {color:#94a3b8 !important;}
.tutor-welcome {background:#242d38 !important;color:#cbd5e1 !important;border-color:#334050 !important;}
.tutor-welcome-title {color:#38bdf8 !important;}
.tutor-thinking {background:#242d38 !important;color:#cbd5e1 !important;}
@media(max-width:767px){.block-container{padding-top:1rem !important;} .workspace-header h1{font-size:20px;} [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){max-width:95%;}}
</style>''', unsafe_allow_html=True)
