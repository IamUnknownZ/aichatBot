# Data Dictionary — AI Sorting Tutor RAG

เอกสารนี้กำหนดโครงสร้างข้อมูลสำหรับ PostgreSQL + pgvector เพื่อให้ระบบขยายต่อได้โดยไม่ต้องเปลี่ยนสถาปัตยกรรมหลัก

## Source-of-truth policy

- ฐานความรู้จริงอ่านจาก `real_data/` เท่านั้น
- ห้าม fallback ไปยัง PDF ทดลอง/legacy
- ห้ามเติมข้อมูลหรือรูปจากเว็บ แหล่งภายนอก หรือความจำของโมเดล
- ภาพต้องผูกด้วย `source_id + page_number` ของ retrieval hit เดียวกัน
- ถ้าหลักฐานใน `real_data/` ไม่พอ ระบบต้อง abstain แทนการเดา
- Page audit และ content/visual map ของหัวข้อ 1 อยู่ที่ `docs/REAL_DATA_TOPIC1_DATA_DICTIONARY.md`

## 1. rag_documents

| Field | Type | Meaning |
|---|---|---|
| source_id | TEXT PK | SHA-256 ของไฟล์ ใช้เป็น version identity |
| source_file | TEXT | ชื่อไฟล์ต้นฉบับ |
| sha256 | TEXT | hash สำหรับตรวจว่าเอกสารถูกแก้หรือไม่ |
| page_count | INTEGER | จำนวนหน้า |
| embedding_model | TEXT | โมเดล embedding ที่ใช้สร้าง index |
| embedding_dim | INTEGER | dimension ของ vector |
| created_at | TIMESTAMPTZ | เวลาสร้าง |
| updated_at | TIMESTAMPTZ | เวลาปรับ index ล่าสุด |

## 2. rag_document_chunks

| Field | Type | Meaning |
|---|---|---|
| id | BIGSERIAL PK | รหัส chunk |
| source_id | TEXT FK | อ้างไปยัง rag_documents |
| source_file | TEXT | ชื่อเอกสาร |
| page_number | INTEGER | เลขหน้าจริง ใช้ทำ citation |
| chunk_index | INTEGER | ลำดับ chunk ภายในหน้า |
| content | TEXT | ข้อความที่ใช้ retrieval |
| metadata | JSONB | section/chapter และ metadata อื่น |
| embedding | vector(768) | semantic vector |
| created_at | TIMESTAMPTZ | เวลา ingest |

สำหรับไฟล์ที่มี machine-readable manifest ใน `real_data/` ค่า `metadata` จะมีอย่างน้อย `topic_id`, `topic_name`, `source_part`, `knowledge_scope=real_data`, `physical_page`, `section`, `subtopic`, `content_types`, `keywords`, `visual_mode`, `slide_labels`, `manifest_file` และ `source_only=true`. Manifest ถูกตรวจด้วย SHA-256 ก่อนนำ metadata มาใช้เพื่อป้องกัน page map เก่าไปจับกับ PDF revision ใหม่

Index ที่ใช้:
- HNSW cosine index บน embedding สำหรับ semantic retrieval
- GIN trigram index บน content สำหรับ lexical retrieval
- B-tree บน source_id และ page_number สำหรับดึงข้อมูลตามหน้า

## 3. rag_document_images — Prepared Visual Catalog

ตารางนี้เป็นสารานุกรมภาพภายในของ RAG: เก็บเฉพาะ embedded image, `figure_crop` และ page render fallback ที่มาจาก `real_data/` พร้อมตำแหน่งอ้างอิงกลับไปยังเอกสารจริง เพื่อให้ visual request ดึงภาพได้โดยไม่ต้องค้นเว็บหรือเรียก LLM เพื่อสร้างภาพ. ถ้าตรวจพบ caption/figure region ระบบต้องใช้ `figure_crop` และไม่เก็บ full-page render ของหน้านั้น

| Field | Type | Meaning |
|---|---|---|
| id | BIGSERIAL PK | รหัสภาพ |
| source_id | TEXT FK | เอกสารเจ้าของภาพ |
| source_file | TEXT | ชื่อเอกสาร |
| page_number | INTEGER | หน้าที่ภาพอยู่ |
| image_index | INTEGER | ลำดับภาพในหน้า |
| mime_type | TEXT | ชนิดไฟล์ภาพ |
| image_bytes | BYTEA | ข้อมูลภาพ |
| width / height | INTEGER | ขนาดภาพ |
| sha256 | TEXT | hash ป้องกันภาพซ้ำ |
| metadata | JSONB | topic, section, subtopic, visual_mode, source_only และ page metadata |
| embedding | vector(768) | multimodal embedding แบบ optional |

ค่าเริ่มต้น localhost เปิดการ extract รูปและ render หน้า vector แล้ว เพื่อสร้าง prepared visual catalog ตั้งแต่ตอน build service. การค้นปกติยังใช้ text retrieval ที่เร็วกว่า จากนั้น map ไปยังภาพด้วย `source_id + page_number`. `RAG_INDEX_IMAGES` ยังเป็น optional สำหรับ phase semantic visual retrieval เต็มรูปแบบ

## 4. rag_user_profiles

โปรไฟล์แบบชื่อเดียวสำหรับงานทดลองในชั้นเรียน ไม่ใช่ระบบ authentication

| Field | Type | Meaning |
|---|---|---|
| user_id | TEXT PK | UUID ที่ระบบสร้าง |
| display_name | TEXT | ชื่อ/ชื่อเล่นที่แสดง |
| normalized_name | TEXT UNIQUE | ชื่อที่ผ่าน NFKC + casefold ใช้ค้น profile เดิม |
| created_at | TIMESTAMPTZ | เวลาสร้าง profile |
| last_seen_at | TIMESTAMPTZ | เวลาใช้งานล่าสุด |

ข้อจำกัด: ถ้านักศึกษาสองคนใช้ชื่อเดียวกันจะชน profile เดียวกัน จึงควรใช้ชื่อเล่นที่ไม่ซ้ำกันในงานทดลอง และไม่ควรใช้ profile แบบนี้กับข้อมูลที่ต้องยืนยันตัวตนจริง

## 5. rag_chat_sessions

| Field | Type | Meaning |
|---|---|---|
| session_id | TEXT PK | รหัส session ที่ application สร้าง |
| user_id | TEXT FK | profile เจ้าของ session |
| created_at | TIMESTAMPTZ | เวลาเริ่ม session |
| last_seen_at | TIMESTAMPTZ | เวลาใช้งานล่าสุด |
| metadata | JSONB | metadata เท่าที่จำเป็น |

## 6. rag_chat_messages

| Field | Type | Meaning |
|---|---|---|
| id | BIGSERIAL PK | รหัสข้อความ |
| session_id | TEXT FK | session |
| role | TEXT | user หรือ assistant |
| content | TEXT | เนื้อหาข้อความ |
| created_at | TIMESTAMPTZ | เวลา |
| metadata | JSONB | model, citation pages, latency ฯลฯ |

ก่อนเปิดเก็บประวัติจริงควรกำหนด retention policy และไม่เก็บข้อมูลส่วนบุคคลเกินความจำเป็น

## 7. rag_retrieval_logs

ใช้เก็บผล retrieval เพื่อทำ performance tuning และใช้เป็นข้อมูลในบทที่ 4

| Field | Type | Meaning |
|---|---|---|
| id | BIGSERIAL PK | รหัส log |
| query_text | TEXT | คำถาม |
| elapsed_ms | DOUBLE PRECISION | เวลา retrieval |
| top_score | DOUBLE PRECISION | relevance สูงสุด |
| hit_pages | JSONB | หน้าที่ค้นคืนได้ |
| hit_scores | JSONB | score ของ top-k |
| created_at | TIMESTAMPTZ | เวลา |

## 8. rag_answer_logs

ใช้เก็บประสิทธิภาพ end-to-end เพื่อวิเคราะห์ผลในบทที่ 4

| Field | Type | Meaning |
|---|---|---|
| id | BIGSERIAL PK | รหัส log |
| query_text | TEXT | คำถาม |
| retrieval_ms | DOUBLE PRECISION | เวลา retrieval |
| ttft_ms | DOUBLE PRECISION | Time To First Token |
| total_ms | DOUBLE PRECISION | เวลาตั้งแต่เริ่มค้นจน stream จบ |
| top_score | DOUBLE PRECISION | relevance สูงสุด |
| answered | BOOLEAN | true=ตอบ, false=abstain/reject |
| model_name | TEXT | generation model |
| hit_pages | JSONB | หน้าที่ retrieve ได้ |
| answer_chars | INTEGER | ความยาวคำตอบ |
| created_at | TIMESTAMPTZ | เวลา |

## Retrieval flow

1. รับคำถามผู้ใช้
2. สร้าง query embedding แบบ 768 dimensions
3. Semantic search ด้วย pgvector HNSW
4. Lexical search ด้วย PostgreSQL pg_trgm
5. Lightweight fusion ของผลค้นหา
6. Relevance gate ด้วย RAG_MIN_SCORE
7. ถ้า score ต่ำ ระบบหยุดและตอบว่าไม่มีข้อมูล โดยไม่เรียก generative model
8. ถ้า score ผ่าน ส่งเฉพาะ top-k chunks เข้า Gemini
9. Stream คำตอบกลับ Streamlit
10. Citation ใช้เลขหน้าจาก metadata จริง ไม่ให้โมเดลเดาเลขหน้า
