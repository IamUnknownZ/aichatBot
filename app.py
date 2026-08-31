import os
import json
import io
import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader
import google.generativeai as genai
from dotenv import load_dotenv
from prompt import PROMPT_SORTING_TUTOR

# 1. โหลด Environment Variables
load_dotenv()

# ตั้งค่าหน้าเว็บ Streamlit
st.set_page_config(
    page_title="AI Chatbot ประจำกลุ่ม - อัลกอริทึมการเรียงลำดับข้อมูล",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS เพื่อรองรับการแสดงผลแบบ Responsive บน iPad และ Mobile
st.markdown("""
<style>
    /* ซ่อน Header และ Footer ส่วนเกินของ Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ควบคุมขนาด Container ให้พอดีทุกขนาดหน้าจอ (Desktop, iPad, Mobile) */
    .block-container {
        max-width: 860px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        margin: auto !important;
    }
    
    /* สไตล์หัวเรื่องแบบ Responsive */
    .main-title {
        font-size: clamp(1.3rem, 4vw, 1.85rem);
        font-weight: 700;
        color: #1a73e8;
        margin-bottom: 0.2rem;
        line-height: 1.3;
    }
    .sub-title {
        font-size: clamp(0.82rem, 2.5vw, 0.95rem);
        color: #5f6368;
        margin-bottom: 1.2rem;
        line-height: 1.4;
    }
    
    /* ปรับแต่งกล่องข้อความแชต */
    .stChatMessage {
        padding: clamp(0.6rem, 2vw, 0.9rem) clamp(0.8rem, 2.5vw, 1.2rem);
        border-radius: 12px;
        margin-bottom: 0.6rem;
        font-size: clamp(0.9rem, 2.5vw, 1rem);
        line-height: 1.6;
    }

    /* ปรับแต่งโค้ดบล็อกให้เลื่อนในแนวนอนได้ดีบนมือถือ ไม่ล้นจอ */
    pre, code {
        max-width: 100%;
        overflow-x: auto;
        border-radius: 8px;
    }

    /* สไตล์สำหรับแท็บเล็ตและไอแพด (iPad / Tablet: 768px - 1024px) */
    @media (max-width: 1024px) {
        .block-container {
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
        }
    }

    /* สไตล์สำหรับมือถือ (Mobile: ต่ำกว่า 768px) */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 4.5rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        .stChatMessage {
            border-radius: 8px;
        }
    }
</style>
""", unsafe_allow_html=True)

# 2. ดึง API Key จาก .env หรือ Secrets อย่างปลอดภัย
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

# 3. แถบเมนูด้านข้าง (Sidebar แบบ Minimal)
with st.sidebar:
    st.title("⚙️ เมนูและการตั้งค่า")
    
    if not api_key:
        api_key = st.text_input("🔑 Gemini API Key:", type="password", help="ใส่ API Key ที่ได้จาก Google AI Studio")
        if not api_key:
            st.warning("⚠️ กรุณาระบุ API Key เพื่อเริ่มใช้งาน")
    else:
        st.success("✅ เชื่อมต่อระบบ AI สำเร็จ")

    selected_model = st.selectbox(
        "โมเดล AI ที่ใช้:",
        options=["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.6-flash"],
        index=0
    )

    st.markdown("---")
    if st.button("🗑️ ล้างการสนทนา (Clear Chat)", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# 4. ฟังก์ชันดึงเนื้อหาจาก PDF อัตโนมัติในเบื้องหลัง (Cache ไว้ไม่ให้อ่านซ้ำ)
@st.cache_data(show_spinner=False)
def load_group_pdf_content() -> str:
    """โหลดเนื้อหาจากไฟล์ PDF ของกลุ่มโดยอัตโนมัติ"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "docs", "อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf"),
        os.path.join(base_dir, "อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                reader = PdfReader(path)
                pages_text = []
                for idx, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        pages_text.append(f"[หน้า {idx+1}]\n{text.strip()}")
                return "\n\n".join(pages_text)
            except Exception as e:
                return f"Error reading PDF: {e}"
    return ""

pdf_knowledge_base = load_group_pdf_content()

# 5. ฟังก์ชันสร้างปุ่ม Copy to Clipboard
def render_copy_button(text_to_copy: str, element_id: str):
    """สร้างปุ่มคัดลอกข้อความลง Clipboard ผ่าน JavaScript โดยตรง"""
    escaped_text = json.dumps(text_to_copy)
    html_code = f"""
    <div style="display: flex; justify-content: flex-end; margin-top: 2px; margin-bottom: 6px;">
        <button id="copy_btn_{element_id}" onclick='
            navigator.clipboard.writeText({escaped_text}).then(() => {{
                var btn = document.getElementById("copy_btn_{element_id}");
                btn.innerHTML = "✅ คัดลอกสำเร็จ!";
                btn.style.backgroundColor = "#e6f4ea";
                btn.style.color = "#137333";
                setTimeout(() => {{
                    btn.innerHTML = "📋 คัดลอกคำตอบ";
                    btn.style.backgroundColor = "#f8f9fa";
                    btn.style.color = "#3c4043";
                }}, 2000);
            }}).catch(err => {{
                console.error("Copy error:", err);
            }});
        ' style="
            background-color: #f8f9fa;
            color: #3c4043;
            border: 1px solid #dadce0;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-family: inherit;
            cursor: pointer;
            transition: all 0.2s ease;
        " onmouseover="this.style.backgroundColor='#e8eaed'" onmouseout="this.style.backgroundColor='#f8f9fa'">
            📋 คัดลอกคำตอบ
        </button>
    </div>
    """
    components.html(html_code, height=35)

# 6. ส่วนหัวของหน้าเว็บ (Header)
st.markdown('<div class="main-title">🎓 AI Chatbot ประจำกลุ่ม</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">ระบบตอบคำถามตรงประเด็นจากเอกสาร: <b>อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf</b></div>', unsafe_allow_html=True)

# 7. จัดการประวัติการสนทนา (Session State)
if "messages" not in st.session_state or len(st.session_state["messages"]) == 0:
    st.session_state["messages"] = [
        {
            "role": "model",
            "content": "สวัสดีครับ! ผมคือ AI Chatbot ประจำกลุ่ม พร้อมตอบคำถามเรื่อง **อัลกอริทึมการเรียงลำดับข้อมูล (Sorting Algorithms)** จากเอกสารประกอบการเรียน พิมพ์คำถามที่ต้องการได้เลยครับ"
        }
    ]

# 8. แสดงข้อความในแชต พร้อมปุ่ม Copy สำหรับข้อความของ AI
for idx, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "model" and idx > 0:
            render_copy_button(msg["content"], f"msg_{idx}")

# 9. การรับคำถามจากผู้ใช้
if user_query := st.chat_input("พิมพ์คำถามที่ต้องการสอบถามที่นี่..."):
    if not api_key:
        st.error("กรุณาระบุ Gemini API Key ในแถบด้านซ้ายก่อนส่งคำถามครับ")
        st.stop()

    # แสดงข้อความของผู้ใช้
    st.session_state["messages"].append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.write(user_query)

    # กำหนดคำสั่งเฉพาะเจาะจง เน้นสั้น ตรงประเด็น ได้ใจความครบ
    system_instruction_with_context = f"""{PROMPT_SORTING_TUTOR}

=== ฐานข้อมูลเอกสาร PDF ของกลุ่ม (PDF KNOWLEDGE BASE) ===
{pdf_knowledge_base if pdf_knowledge_base.strip() else "ไม่มีเอกสารเพิ่มเติม ให้ตอบตามหลักการอัลกอริทึมทั่วไป"}
======================================================
"""

    genai.configure(api_key=api_key)
    generation_config = {
        "temperature": 0.1,  # ค่าต่ำเพื่อให้ตอบตรงประเด็น ไม่เยิ่นเย้อ
        "top_p": 0.95,
        "max_output_tokens": 2048,
    }

    model = genai.GenerativeModel(
        model_name=selected_model,
        generation_config=generation_config,
        system_instruction=system_instruction_with_context,
    )

    # สร้างและแสดงคำตอบของ AI
    with st.chat_message("model"):
        with st.spinner("กำลังค้นหาคำตอบ..."):
            try:
                gemini_history = [
                    {
                        "role": "user" if m["role"] == "user" else "model",
                        "parts": [m["content"]]
                    }
                    for m in st.session_state["messages"][:-1]
                ]

                chat_session = model.start_chat(history=gemini_history)
                response = chat_session.send_message(user_query)
                
                response_text = response.text.strip()
                st.write(response_text)
                
                # แสดงปุ่ม Copy สำหรับข้อความล่าสุด
                new_msg_idx = len(st.session_state["messages"])
                render_copy_button(response_text, f"msg_{new_msg_idx}")

                st.session_state["messages"].append({"role": "model", "content": response_text})
            except Exception as e:
                error_msg = f"เกิดข้อผิดพลาด: {e}"
                st.error(error_msg)
                st.session_state["messages"].append({"role": "model", "content": error_msg})
