# Deployment — Streamlit + PostgreSQL/pgvector

## Production architecture

User
→ Streamlit Community Cloud
→ query embedding
→ PostgreSQL + pgvector hybrid retrieval
→ relevance gate
→ Gemini generation
→ streamed answer + page citation

PDF ทุกไฟล์ที่ได้รับอนุมัติภายใต้ `real_data/` จะถูก ingest เป็นรายไฟล์ และไม่ถูกส่งทั้งเล่มเข้า Gemini ในทุกคำถาม

**Closed-source rule:** runtime, retrieval และรูปประกอบใช้เฉพาะ `real_data/` เท่านั้น ไม่มี web/external fallback

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

    python -m scripts.ingest_pdf --force

กระบวนการนี้จะ:
1. scan เฉพาะ `real_data/**/*.pdf`
2. hash และ ingest แต่ละ PDF แยกกัน
3. แบ่งข้อความตาม physical PDF page
4. สร้าง text embedding
5. เก็บ text + source_id + page metadata + vector ลง PostgreSQL
6. ดึง embedded images และ render diagram/vector pages จาก PDF จริงไว้เป็น internal visuals
7. สร้าง HNSW / trigram indexes ผ่าน schema

ใช้ `--text-only` เฉพาะเมื่อจงใจไม่ต้องการเตรียมภาพภายใน PDF

ถ้า API ติด rate limit ตัว embedder มี bounded exponential backoff แต่หากเป็น daily quota ต้องใช้ quota ที่พร้อมก่อน ingest

## 4. ตั้ง Streamlit Community Cloud Secrets

เพิ่มค่าที่ App settings → Secrets:

    GEMINI_API_KEY = "..."
    DATABASE_URL = "postgresql://..."

ตัวอย่างอยู่ที่ .streamlit/secrets.toml.example

ห้ามนำ secrets.toml จริงขึ้น Git

## 5. Cold start หลัง ingest

เมื่อ app เปิด:
1. scan รายชื่อ PDF ใน `real_data/`
2. คำนวณ SHA-256 ของทุกไฟล์
3. จำกัด retrieval scope ให้เฉพาะ source_id ที่ยังอยู่ใน `real_data/`
4. เช็กแต่ละ hash ใน PostgreSQL
5. ถ้าทุกไฟล์มี index แล้ว จะข้าม PDF extraction/document embeddings
6. สร้าง embedding เฉพาะคำถามของผู้ใช้
7. retrieve top chunks แล้วตอบ

นี่คือ path ที่ควรใช้ใน production

## 6. การอัปเดต PDF

เมื่อเปลี่ยนเนื้อหา PDF:
1. commit PDF เวอร์ชันใหม่
2. รัน python -m scripts.ingest_pdf --force ด้วย DATABASE_URL เดิม
3. ระบบจะบันทึก index ของ hash ใหม่และลบ version เก่าของ source_file เดียวกัน
4. deploy/reboot Streamlit

## 7. Image / diagram mode — internal only

คำสั่ง `python -m scripts.ingest_pdf --force` เตรียมภาพจาก PDF ภายใน `real_data/` ให้อัตโนมัติ:
- embedded raster image จาก PDF จริง
- `figure_crop` ที่ isolate จาก caption + vector bounds
- page render ภายในใช้เป็น extraction fallback เท่านั้น

**User-facing rule:** UI แสดงเฉพาะ `figure_crop` ที่ isolate แล้วเท่านั้น ไม่แสดง full-page render หรือ raw embedded image เพื่อป้องกันหน้ากระดาษเต็ม/ภาพดำหลุดมาถึงผู้ใช้

ค่า config ที่เทียบเท่าคือ:

    RAG_EXTRACT_IMAGES=true
    RAG_RENDER_VECTOR_PAGES=true
    RAG_INDEX_IMAGES=false

`RAG_INDEX_IMAGES` เป็น optional multimodal vector; retrieval ปกติผูกรูปตาม text hit จึงไม่จำเป็นต้องเปิด

ภาพถูกเลือกด้วยคู่ `source_id + page_number` เพื่อป้องกันรูปหน้าเดียวกันจากคนละ PDF ปะปนกัน

**ห้าม** web image search, stock image, AI-generated image หรือ external image fallback

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

Streamlit runtime เป็น **pgvector-only** และ fail-closed:
- DATABASE_URL ต้องมี
- PostgreSQL ต้องเปิด pgvector + pg_trgm
- ต้อง ingest `real_data/` เข้า DATABASE_URL เดียวกันก่อน deploy
- ถ้า DB ต่อไม่ได้หรือ index ไม่ครบ แอปจะ disable chatbot และไม่ fallback ไป local lexical
- RAG_AUTO_INGEST=false
- RAG_ALLOW_MEMORY_FALLBACK=false

การใช้ local lexical ยังอนุญาตเฉพาะ unit test / developer utility ที่เรียก `build_rag_service(..., require_database=False)` โดยตรง ไม่ใช่ runtime ของ Streamlit.
