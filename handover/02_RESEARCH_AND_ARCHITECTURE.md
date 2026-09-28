# Research + Architecture Handover

รายละเอียด bibliography เต็มอยู่ที่:
- `docs/RESEARCH_REFERENCES.md`
- `docs/RESEARCH_MATRIX.md`

ไฟล์นี้อธิบายว่า “งานไหนถูกเอามาใช้ทำอะไร”

## 1. RAG foundation

### Lewis et al. (2020) — Retrieval-Augmented Generation
ใช้เป็นฐานของ architecture:
- LLM ไม่ควรเป็น knowledge source หลัก
- retrieve evidence ก่อน generate
- external non-parametric memory

ในโปรเจกต์:
- `real_data/` → chunks → embeddings → pgvector
- query → retrieval → top evidence → Gemini

### Gao et al. — RAG Survey
ใช้กรอบ Naive / Advanced / Modular RAG

ในโปรเจกต์พัฒนาเลย naive ไปแล้ว:
- query normalization
- hybrid retrieval
- rerank
- relevance gate
- clarification
- visual retrieval

## 2. Long context problem

### Liu et al. — Lost in the Middle
เหตุผลที่เลิกส่ง PDF ทั้งเล่มทุกคำถาม

ในระบบ:
- chunk/page retrieval
- top-k context
- citation physical page

## 3. Retrieval correctness / abstention

### Self-RAG
แนวคิดไม่ retrieve/generate แบบตายตัว

### CRAG
แนวคิด confidence/relevance gate

### RAGTruth / RGB / RAGChecker
ยืนยันว่า RAG ยัง hallucinate ได้

ในระบบ:
- answerable threshold
- insufficient evidence → abstain
- production ไม่มี external fallback
- logging retrieval score

## 4. Hybrid retrieval

Research/thesis หลายงาน academic chatbot ใช้ semantic + lexical

ในระบบ:
- pgvector semantic cosine search
- pg_trgm lexical search
- fuse score
- topic/definition reranking

เหตุผล:
- ชื่อ algorithm และคำเฉพาะต้อง lexical match
- คำอธิบายธรรมชาติได้ประโยชน์จาก semantic match

## 5. RAG evaluation

### RAGAS
- context relevance
- faithfulness
- answer relevance

### ARES
- context relevance
- faithfulness
- answer relevance

### RAGChecker
แยก retriever vs generator error

ยังควรทำต่อ:
- สร้าง evaluation set ของ 6 หัวข้อหลัก
- Hit@K
- faithfulness
- citation accuracy
- out-of-scope rejection
- P50/P95 latency
- TTFT

## 6. Visual / Multimodal research

### VisRAG
แนวคิด retrieve visual/page representation โดยไม่ทิ้ง layout

สิ่งที่นำมาใช้:
- เตรียม visual catalog คู่กับ textual RAG
- source/page binding

### ColPali
แนวคิด visual document retrieval ด้วย page-image representation + late interaction

สิ่งที่นำมาใช้:
- architecture พร้อมมี image embedding column
- current implementation ยังไม่ได้เปิด multimodal vector by default

### VISA
Visual Source Attribution

สิ่งที่นำมาใช้:
- ทุกภาพต้องย้อนกลับ source_id + page_number
- caption และ source file แสดงกับ user

## 7. Figure extraction research

### PDFFigures 2.0 — Clark & Divvala
แนวคิด:
- figure + caption extraction
- แยก figure region แทน screenshot ทั้งหน้า

นำมาใช้:
- `figure_crop`
- caption-driven vector region

### FigEx
แนวคิด:
- aligned figure/subfigure + caption
- bounding-box extraction

นำมาใช้:
- บันทึก `clip=[x0,y0,x1,y1]`
- visual region metadata

ข้อสำคัญ:
implementation ปัจจุบัน “inspired by” research แต่ยังเป็น heuristic PyMuPDF ไม่ใช่โมเดล FigEx/PDFFigures เต็มระบบ

## 8. Educational chatbot / programming learning

### Nantha Kumar Subramaniam — Enabling Learning of Programming through Educational Chatbot
แนวคิด:
- multimodal content
- animation
- visualization
- interactive exercises
- context-sensitive hints
- ลด cognitive load

สิ่งที่ทำแล้ว:
- source-only diagram/trace
- structured explanation
- follow-up visual

ยังไม่ได้ทำ:
- true step-by-step animation
- interaction ที่ให้ผู้เรียนกดทีละ step

## 9. Thesis systems ใกล้โปรเจกต์

ดูรายการเต็มใน RESEARCH_REFERENCES / MATRIX

กลุ่มที่ใช้มาก:
- academic RAG chatbot
- AI Tutor with local curriculum
- Streamlit + RAG
- Gemini + vector database
- PDF preprocessing + chunking
- controlled knowledge / out-of-context rejection
- RAGAS evaluation
- hyperparameter testing chunk/top-k

## 10. Current architecture files

- `app.py`: Streamlit UI + chat lifecycle + source/image rendering
- `rag/bootstrap.py`: source scan / production store setup
- `rag/config.py`: env config
- `rag/embeddings.py`: Gemini embedding
- `rag/pdf_ingest.py`: PDF text/image parsing + crop
- `rag/store.py`: local test store + PgVectorStore
- `rag/service.py`: routing/retrieval/rerank/generation/visual policy
- `rag/query_lexicon.py`: aliases + primary curriculum taxonomy
- `rag/clarifications.py`: mixed-initiative clarification
- `prompt.py`: grounded tutor prompt
- `db/schema.sql`: pgvector DB schema

## 11. Research rule

Research ภายนอกใช้เพื่อ “ออกแบบระบบ” ได้

แต่ runtime content rule:
- ห้ามเอาเนื้อหางานวิจัยมาเป็นคำตอบของนักเรียน
- ห้ามใช้รูปจากงานวิจัยเป็นภาพประกอบ
- chatbot evidence ต้องมาจาก `real_data/` เท่านั้น
