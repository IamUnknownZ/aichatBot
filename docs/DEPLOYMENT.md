# Deployment — Streamlit + PostgreSQL/pgvector

## Production architecture

User
→ Streamlit Community Cloud
→ query embedding
→ PostgreSQL + pgvector hybrid retrieval
→ relevance gate
→ Gemini generation
→ streamed answer + page citation

PDF ทั้งเล่มจะถูก ingest เพียงครั้งเดียว ไม่ถูกส่งเข้า Gemini ในทุกคำถาม

## 1. เตรียม PostgreSQL

ใช้ PostgreSQL ที่รองรับ extensions:
- vector (pgvector)
- pg_trgm

Schema อยู่ที่ db/schema.sql และระบบสามารถสร้าง schema ให้อัตโนมัติเมื่อเชื่อมต่อด้วย user ที่มีสิทธิ์

ถ้า managed PostgreSQL ไม่อนุญาต CREATE EXTENSION ให้เปิด pgvector และ pg_trgm จากหน้า provider ก่อน

## 2. ตั้งค่า .env บนเครื่องสำหรับ ingest

อย่า commit ไฟล์ .env

ค่าที่จำเป็น:

GEMINI_API_KEY=...
DATABASE_URL=postgresql://...

ค่าที่แนะนำ:
- GEMINI_EMBEDDING_MODEL=gemini-embedding-001
- RAG_EMBEDDING_DIM=768
- RAG_AUTO_INGEST=false
- RAG_ALLOW_MEMORY_FALLBACK=false
- PROFILE_ENABLED=true
- RECENT_QUESTION_LIMIT=6

Course identity ปรับได้โดยไม่แก้ UI code:
- COURSE_TITLE
- COURSE_LEVEL
- TUTOR_NAME
- MASCOT_EMOJI

## 3. Ingest เอกสารครั้งเดียว

ติดตั้ง dependency:

    pip install -r requirements.txt

สร้าง/อัปเดต index:

    python scripts/ingest_pdf.py --force

กระบวนการนี้จะ:
1. อ่าน PDF
2. แบ่งข้อความตามหน้า
3. สร้าง embedding
4. เก็บ text + page metadata + vector ลง PostgreSQL
5. สร้าง HNSW / trigram indexes ผ่าน schema

ถ้า API ติด rate limit ตัว embedder มี bounded exponential backoff แต่หากเป็น daily quota ต้องใช้ quota ที่พร้อมก่อน ingest

## 4. ตั้ง Streamlit Community Cloud Secrets

เพิ่มค่าที่ App settings → Secrets:

    GEMINI_API_KEY = "..."
    DATABASE_URL = "postgresql://..."

ตัวอย่างอยู่ที่ .streamlit/secrets.toml.example

ห้ามนำ secrets.toml จริงขึ้น Git

## 5. Cold start หลัง ingest

เมื่อ app เปิด:
1. คำนวณ SHA-256 ของ PDF
2. เช็ก hash ใน PostgreSQL
3. ถ้ามี index แล้ว จะข้าม PDF text extraction และข้าม document embeddings
4. สร้าง embedding เฉพาะคำถามของผู้ใช้
5. retrieve top chunks แล้วตอบ

นี่คือ path ที่ควรใช้ใน production

## 6. การอัปเดต PDF

เมื่อเปลี่ยนเนื้อหา PDF:
1. commit PDF เวอร์ชันใหม่
2. รัน python scripts/ingest_pdf.py --force ด้วย DATABASE_URL เดิม
3. ระบบจะบันทึก index ของ hash ใหม่และลบ version เก่าของ source_file เดียวกัน
4. deploy/reboot Streamlit

## 7. Image / diagram mode

ค่าเริ่มต้นปิดเพราะเอกสารปัจจุบันเน้นข้อความ

เปิดเมื่อ PDF รุ่นใหม่มีภาพประกอบ:

    RAG_EXTRACT_IMAGES=true
    RAG_RENDER_VECTOR_PAGES=true
    RAG_INDEX_IMAGES=true

- RAG_EXTRACT_IMAGES: ดึงรูป raster ที่ฝังใน PDF
- RAG_RENDER_VECTOR_PAGES: render หน้าที่มี vector drawing เป็น PNG
- RAG_INDEX_IMAGES: สร้าง multimodal embedding

ระบบผูกภาพกับเลขหน้า เพื่อให้ UI แสดงภาพจากหน้าที่ retrieval พบได้

## 8. Debug / performance

เปิด checkbox "แสดงข้อมูล RAG สำหรับทดสอบ" ใน sidebar เพื่อดู:
- retrieval query
- retrieval latency
- top relevance score
- answerable / rejected
- page / vector / lexical score ของ top chunks

PostgreSQL เก็บ answer/performance logs ใน rag_answer_logs สำหรับคำนวณ P50/P95 และ TTFT ภายหลัง

Profile/history ใช้ rag_user_profiles, rag_chat_sessions และ rag_chat_messages โดยเขียนข้อมูลหลังคำตอบแสดงผลแล้ว จึงไม่อยู่ใน critical path ของ TTFT

PgVectorStore ใช้ Psycopg ConnectionPool ขนาดเล็ก (1-6 connections) เพื่อลด overhead การสร้าง connection ใหม่ทุก query

## 9. Production rule

บน Streamlit Cloud ไม่แนะนำ in-memory fallback เพราะ cold start จะต้องสร้าง document embeddings ใหม่ทั้งหมดและอาจชน quota

Production:
- DATABASE_URL ต้องมี
- ingest ก่อน deploy
- RAG_AUTO_INGEST=false
- RAG_ALLOW_MEMORY_FALLBACK=false

Development local:
- ไม่มี DATABASE_URL ก็ใช้ in-memory ได้
- เหมาะสำหรับทดสอบสั้น ๆ เท่านั้น
