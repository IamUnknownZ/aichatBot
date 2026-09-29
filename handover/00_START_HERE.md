# AI Sorting Tutor — Handover / Start Here

อัปเดตสำหรับการย้ายเครื่อง: 30 กันยายน 2026

เอกสารชุดนี้ทำขึ้นเพื่อให้เปิดโปรเจกต์บนอีกเครื่องแล้วรับช่วงต่อได้โดยไม่ต้องไล่อ่านแชตเก่า

## 1. สถานะล่าสุด

โปรเจกต์เป็น Streamlit AI Tutor สำหรับวิชา Sorting โดยใช้ Closed-source RAG

Production path:

```
User
  ↓
Streamlit
  ↓
Query normalization / clarification / topic routing
  ↓
Gemini query embedding
  ↓
PostgreSQL + pgvector + pg_trgm
  ↓
Hybrid semantic + lexical retrieval
  ↓
Topic/definition reranking + relevance gate
  ↓
Top evidence from real_data/ only
  ↓
Gemini grounded answer OR extractive fast path
  ↓
Citation + source-only visual
```

กฎสำคัญ:
- คำตอบและภาพต้องมาจาก `real_data/` เท่านั้น
- ไม่มี web/external fallback
- Streamlit production ต้องใช้ PostgreSQL + pgvector
- ถ้า DB ใช้ไม่ได้ แอป fail-closed ไม่ fallback ไป local lexical
- user-facing image แสดงเฉพาะ `figure_crop` / `trace_crop`

## 2. Curriculum ที่อนุมัติ

บังคับตามรูปอ้างอิงล่าสุดเท่านั้น และต้องเรียงลำดับนี้:

1. หลักการเรียงลำดับข้อมูล
2. Bubble Sort
3. Selection Sort
4. Insertion Sort
5. Merge Sort
6. Counting Sort

Counting Sort ใช้แทน Quick Sort

Shell Sort, Quick Sort, Heap Sort, Radix Sort, Bucket Sort ฯลฯ อาจมีอยู่ใน PDF ต้นฉบับ แต่เป็น reference-only ไม่ใช่หัวข้อหลัก

## 3. Git status ตอนแพ็ก

- Branch: `main`
- Code baseline ก่อนเพิ่มเอกสาร handover: `3bd2363 fix: match curriculum topics to approved source`
- ตอนเริ่มทำ handover: `main` ตรงกับ `origin/main`
- Archive อาจมี commit handover เพิ่มจาก baseline นี้
- ต้องเก็บโฟลเดอร์ `.git/` ใน archive เพื่อให้ประวัติ commit อยู่ครบ

## 4. Database status ที่ตรวจจริง

Supabase PostgreSQL + pgvector:

- documents: 13
- physical pages: 204
- chunks: 243
- chunks with vectors: 243
- visuals: 256

ชนิดภาพใน `rag_document_images`:
- embedded_image: 50
- figure_crop: 23
- trace_crop: 70
- vector_page_render: 113

หมายเหตุสำคัญ:
- 113 full-page renders ยังเก็บเป็น internal fallback
- UI ไม่แสดง full-page render
- full-page renders ยังเป็น internal only; UI เลือกเฉพาะภาพที่ได้รับ user_visible review
- หนังสือ Merge Sort ใหม่เพิ่ม 32 chunks, 31 หน้า และ 16 figure crops ที่ตรวจแล้ว

## 5. เอกสารที่ต้องอ่านต่อ

อ่านตามลำดับ:
1. `handover/01_DEVELOPMENT_HISTORY.md`
2. `handover/02_RESEARCH_AND_ARCHITECTURE.md`
3. `handover/03_IMAGE_CROP_LABEL_PIPELINE.md`
4. `handover/04_NEW_MACHINE_SETUP.md`
5. `handover/05_NEXT_WORK_CHECKLIST.md`

เอกสารเดิมที่มีรายละเอียดเพิ่ม:
- `docs/RESEARCH_REFERENCES.md`
- `docs/RESEARCH_MATRIX.md`
- `docs/QUERY_FLEXIBILITY_RESEARCH.md`
- `docs/DATA_DICTIONARY.md`
- `docs/REAL_DATA_TOPIC1_DATA_DICTIONARY.md`
- `docs/DEPLOYMENT.md`

## 6. Security

Portable archive **ไม่เก็บ `.env` และ credential จริง** เพื่อไม่ให้ secret หลุดไปกับไฟล์ ZIP

บนเครื่องใหม่ให้สร้าง `.env` จาก `.env.example` แล้วกรอกค่า `GEMINI_API_KEY` และ
`DATABASE_URL` ในเครื่องนั้นเองเท่านั้น

ข้อควรระวัง:
- ห้าม commit `.env`
- ห้ามอัปโหลด ZIP ไปยัง public GitHub/Drive ที่แชร์สาธารณะ
- ห้ามส่ง DATABASE_URL / GEMINI_API_KEY ลงแชตหรือ screenshot
- legacy LINE credentials ต้องใช้ environment variables และควร rotate/revoke ค่าเก่าก่อนนำกลับมาใช้

## 7. Environment ที่ไม่ควรย้ายข้ามเครื่อง

Archive ไม่ควรใช้ Python `venv/` เดิม เพราะ path และ binary ผูกกับเครื่องเก่า

ให้สร้างใหม่ด้วย:

```bash
bash handover/setup_new_machine.sh
```

จากนั้น:

```bash
source venv/bin/activate
python -m streamlit run app.py
```

ถ้าเป็น Windows ให้อ่าน `handover/04_NEW_MACHINE_SETUP.md`
