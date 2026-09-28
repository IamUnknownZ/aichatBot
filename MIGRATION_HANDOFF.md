# AI Chatbot Portable Migration Handoff

อัปเดต: 27 กันยายน 2026

โปรเจกต์: `ai-chat-bot`
วัตถุประสงค์: ย้ายไปเครื่องใหม่แล้วรับงานต่อได้ทันที โดยรักษา source, knowledge files, tests, เอกสาร และ Git history ที่จำเป็นไว้ครบ

## 1. สิ่งที่อยู่ใน ZIP และสิ่งที่จงใจไม่ใส่

ZIP นี้รวม source code, PDF ใน `real_data/`, schema, tests, research notes, handover เดิม,
ไฟล์ประกอบโปรเจกต์ และ `.git/` เพื่อเก็บประวัติ Git และ branch metadata ไว้ด้วย

จงใจไม่รวมเฉพาะสิ่งที่ทำให้ย้ายเครื่องไม่ปลอดภัยหรือไม่ portable:

- `.env`, `line3_his/.env`, `workaw_chatbot/workaw/.env` และ Streamlit secrets จริง
- `venv/`, `.venv/`, `node_modules/`, `__pycache__/`, `.pyc`, `.DS_Store` และ cache เครื่องเก่า
- `workaw_chatbot.zip` รุ่นเก่าซึ่งเป็น archive ซ้อนและมีไฟล์ลับ/ไฟล์ cache อยู่ภายใน
- legacy nested archive `workaw_chatbot/workaw/line3_his.zip`, temporary lock files such as `~$workaw_data.xlsx`, and macOS metadata

ไฟล์ source/data ที่ไม่ใช่ secret ยังเก็บไว้ทั้งหมด รวมถึง legacy folders ที่ยังอยู่ใน working
project เพื่อให้รับช่วงต่อได้ครบที่สุด

ข้อยกเว้นด้านความปลอดภัย: legacy source/history เดิมมี credential LINE แบบ hardcode และมี
Gemini key ในไฟล์ตรวจ model รุ่นเก่า จึงใช้สำเนาที่ redacted ใน ZIP โดยให้ LINE รับค่าจาก
`LINE_CHANNEL_ACCESS_TOKEN` กับ `LINE_CHANNEL_SECRET` และให้ Gemini รับจาก
`GEMINI_API_KEY_INSURVERSE` หรือ `GEMINI_API_KEY` แทน ค่าเดิมควรถูก rotate/revoke ก่อนนำ
legacy bot กลับมาใช้งาน

## 2. สถานะปัจจุบัน

ระบบหลักคือ Streamlit AI Tutor สำหรับบทเรียน Sorting ใช้ closed-source RAG:

~~~text
User
  -> Streamlit chat UI
  -> query normalization / clarification / topic routing
  -> Gemini text embedding
  -> PostgreSQL + pgvector + pg_trgm
  -> hybrid semantic + lexical retrieval
  -> topic / definition reranking + relevance gate
  -> grounded Gemini answer or extractive fast path
  -> page citation and source-only visual
~~~

กฎ runtime ที่สำคัญ:

- knowledge base ที่อนุญาตคือ `real_data/` เท่านั้น
- production ต้องใช้ PostgreSQL + pgvector; ถ้า DB ใช้ไม่ได้ production จะ fail closed
- ไม่มี web/external fallback
- user-facing visual อนุญาตเฉพาะ `figure_crop` และ `trace_crop`
- full-page render เก็บเป็น internal fallback ได้ แต่ไม่ควรแสดงให้ผู้ใช้
- curriculum หลักมี 6 หัวข้อตามลำดับที่อนุมัติ:
  1. หลักการเรียงลำดับข้อมูล
  2. Bubble Sort
  3. Selection Sort
  4. Insertion Sort
  5. Merge Sort
  6. Counting Sort
- Quick Sort, Shell Sort, Heap Sort, Radix Sort, Bucket Sort ฯลฯ เป็น reference-only ไม่ใช่หัวข้อหลัก

### Git baseline

ณ จุดแพ็ก โปรเจกต์อยู่บน branch `main` และมี commit handover ล่าสุด:

~~~text
295df4d docs: add portable project handover
~~~

branch local อยู่ข้างหน้า `origin/main` 1 commit ตามสถานะที่ตรวจบนเครื่องต้นทาง
การเก็บ `.git/` ใน ZIP ทำให้สามารถดู `git log`, `git show`, branch และ remote เดิมได้ต่อ

Portable ZIP มี commit chain ครบทั้ง 12 commits ตามลำดับเดิม แต่ Git object history ถูก
redact เฉพาะ credential ที่เคย hardcode ใน legacy LINE source ทำให้ SHA-1 ของ commit ใน
ZIP เปลี่ยนตามหลักของ Git; ไม่มี milestone หรือ source change อื่นถูกตัดออก รายการ SHA-1
ต้นฉบับและ subjects อยู่ใน GIT_HISTORY_REFERENCE.md

### ฐานข้อมูล snapshot ล่าสุดที่บันทึกไว้

ค่าต่อไปนี้เป็น snapshot จาก handover ก่อนแพ็ก ไม่ใช่ข้อมูลที่ฝังไว้ใน ZIP:

- documents: 3
- chunks: 119
- chunks with vectors: 119
- visuals: 130
- `embedded_image`: 8
- `figure_crop`: 2
- `trace_crop`: 49
- `vector_page_render`: 71

ถ้าต้องการยืนยันกับ Supabase จริง ให้ทำตามคำสั่งตรวจในหัวข้อ setup ด้านล่างโดยไม่พิมพ์
ค่า connection string ออกมา

## 3. ประวัติการพัฒนาที่สำคัญ

ประวัติเต็มอยู่ใน `.git/`; milestone หลักมีดังนี้:

1. `f3216c9`, `7b7e493` — prototype Streamlit chatbot รุ่นแรก
2. `c2a702f` — บังคับให้คำตอบมี Python code ตามประเภทคำถามและอ้างอิง physical PDF page
3. `fe4561e` — grounded RAG, source/page metadata, relevance gate, profile/history และ UI ต่อเนื่อง
4. `b10b63d` — query lexicon, alias, typo/transliteration handling และ adaptive routing
5. `d30099c` — two-sided messaging UI, chat bubble และ dark visual redesign
6. `015d0a7` — mixed-initiative clarification, follow-up context และแก้ contrast
7. `d1f50b5` — closed-source production RAG ด้วย PostgreSQL, pgvector, pg_trgm, HNSW และ fail-closed behavior
8. `020ed25` — structured answer formatting, trace visuals และ source-linked visual follow-up
9. `f102c55` — แก้ Streamlit ghost overlay/rerun และ lock curriculum
10. `3bd2363` — จัด curriculum ให้ตรงรูปอ้างอิง: เปลี่ยนเป็น Counting Sort และกำหนด 6 หัวข้อหลัก
11. `295df4d` — เพิ่ม handover สำหรับการย้ายเครื่อง

รายละเอียดราย phase อยู่ที่ `handover/01_DEVELOPMENT_HISTORY.md`

## 4. Research ที่ถูกใช้และผลที่นำมาใช้จริง

รายละเอียด bibliography เต็มอยู่ที่ `docs/RESEARCH_REFERENCES.md`, inventory ของไฟล์และ
การใช้งานอยู่ที่ docs/RESEARCH_INVENTORY.md และ mapping อยู่ที่ `docs/RESEARCH_MATRIX.md`
สรุปการนำมาใช้มีดังนี้:

| งาน/แนวคิด | สิ่งที่นำมาใช้ในโปรเจกต์ |
|---|---|
| Lewis et al. — RAG | retrieve evidence จาก knowledge base ก่อน generate |
| RAG survey / Naive–Advanced–Modular RAG | query normalization, hybrid retrieval, rerank, gate, clarification |
| Lost in the Middle | เลิกส่ง PDF ทั้งเล่ม; ใช้ chunk/page retrieval |
| Self-RAG / CRAG | relevance gate, abstention และไม่ตอบเมื่อ evidence ไม่พอ |
| RAGTruth / RGB / RAGChecker | ระวัง hallucination และแยกปัญหา retriever/generator |
| Hybrid retrieval research | semantic cosine + lexical/trigram เพื่อจับทั้งคำธรรมชาติและชื่อ algorithm |
| RAGAS / ARES | กรอบวัด context relevance, faithfulness และ answer relevance |
| VisRAG | เตรียม visual catalog ที่ผูก source/page กับ textual evidence |
| ColPali | วางทางต่อยอด image/page embedding; ยังไม่ได้เปิดเป็น default |
| VISA | source attribution ของภาพด้วย source id และ page |
| PDFFigures 2.0 / FigEx | แนวคิดแยก figure/caption และเก็บ bounding box; implementation ปัจจุบันยังเป็น heuristic PyMuPDF |
| Educational chatbot research | structured explanation, visual follow-up และแนวทางต่อยอด animation/interactive exercise |

ข้อจำกัด: งานวิจัยใช้เพื่อออกแบบระบบ ไม่ใช่ source เนื้อหาที่ chatbot เอาไปตอบนักเรียน
runtime content และภาพต้องมาจาก `real_data/` เท่านั้น

## 5. Architecture และไฟล์หลัก

- `app.py` — Streamlit UI, session/chat lifecycle, source citation และ image rendering
- `prompt.py` — grounded tutor prompt
- `rag/config.py` — environment/config defaults
- `rag/bootstrap.py` — source scan, service construction, production store selection
- `rag/embeddings.py` — Gemini text/image embedding adapter
- `rag/pdf_ingest.py` — PDF parsing, chunking, image extraction, crop generation และ metadata
- `rag/store.py` — local test store และ PostgreSQL/pgvector store
- `rag/service.py` — normalization, clarification, retrieval, rerank, generation, visual policy
- `rag/query_lexicon.py` — Thai/English alias และ primary curriculum taxonomy
- `rag/clarifications.py` — mixed-initiative intent/clarification logic
- `db/schema.sql` — PostgreSQL schema, pgvector/pg_trgm indexes
- `scripts/ingest_pdf.py` — initial ingest, `--force`, `--text-only`, `--images-only`
- `real_data/` — approved source PDFs และ manifest; ห้ามเปลี่ยน source โดยไม่ re-index

## 6. Feature ที่พัฒนาแล้ว

- grounded RAG จาก PDF จริง พร้อม physical page citation
- PostgreSQL + pgvector semantic retrieval และ pg_trgm lexical retrieval
- source hash/source id binding ป้องกันข้าม PDF/ข้ามหน้า
- topic, definition และ algorithm reranking
- relevance threshold, abstention และ production fail-closed
- Thai/English aliases, transliteration, typo tolerance และ out-of-scope guard
- clarification เมื่อ query กว้าง เช่น `sort`; follow-up เช่น `ภาพ` ใช้ topic ก่อนหน้า
- fast extractive path สำหรับ definition ง่าย ๆ ลด generation latency
- Gemini generation timeout และ grounded fallback ที่อ่านง่าย
- two-sided chat UI, profile/recent question และ dark theme
- structured tutor answers: ความหมาย, หลักการทำงาน, bullets/numbered steps
- source-only visual retrieval สำหรับ figure/trace
- visual catalog refresh แยกจาก text embedding ผ่าน `--images-only`
- curriculum lock ตาม 6 หัวข้อที่อนุมัติ
- tests ครอบคลุม clarification, query lexicon, real-data scope และ crop behavior

## 7. Image crop + label pipeline แบบละเอียด

### 7.1 Source binding

ทุก visual ผูกกับ `source_id` ซึ่งเป็น SHA-256 ของ PDF, `source_file`, `page_number`,
`image_index`, image SHA-256 และ metadata อื่น ๆ การ map จาก text hit ไปภาพใช้คู่
`(source_id, page_number)` จึงไม่ควรหยิบหน้าเลขเดียวกันจากคนละ PDF

### 7.2 Embedded image

`page.get_images(full=True)` และ `doc.extract_image(xref)` ใช้ดึงภาพ raster ที่ฝังใน PDF
โดยกรองขั้นต่ำประมาณ width 180 และ height 120 และ dedupe ด้วย SHA-256
แต่ `embedded_image` ไม่แสดงตรงต่อผู้ใช้ เพราะบางไฟล์เป็น mask, layer ดำ หรือภาพที่ไม่ใช่
visual ที่สื่อความหมาย

### 7.3 figure_crop

ใช้เมื่อเจอ caption ที่ชัด เช่น `รูปที่ 8.2`, `Figure 1`, `Fig. 2`:

1. อ่าน text blocks ของหน้า
2. หา caption ด้วย regex `^\\s*(รูปที่|figure|fig\\.)\\s*\\d`
3. ใช้ตำแหน่ง y ของ caption เป็น anchor
4. มองหา vector drawings ที่อยู่เหนือ caption ไม่เกินประมาณ 280 PDF points
5. ตัด candidate ที่กว้างน้อยกว่า 120 หรือสูงน้อยกว่า 45 points
6. เลือก candidate ที่ area ใหญ่ที่สุด
7. เติม padding 8 points แล้ว render ที่ 2x
8. เก็บ `kind=figure_crop` และ label เป็น caption จริงจาก PDF

### 7.4 trace_crop

เพิ่มเพื่อจับ array/trace/table ที่ไม่มี caption:

1. อ่าน `page.get_drawings()`
2. ตัด rect ใกล้ header/footer
3. ตัด rect เล็กเกินและ horizontal line ที่เกือบเต็มหน้า
4. ต้องเหลืออย่างน้อย 5 rect
5. เรียงตาม y/x และ group เมื่อระยะจาก bottom ของกลุ่มเดิมไม่เกิน 35 points
6. group ต้องมีอย่างน้อย 5 rect
7. crop เป็น union bounding box
8. reject เมื่อ width < 180, height < 25 หรือ crop area มากกว่า 35% ของหน้า
9. เติม padding x=14, y=18, render 2x
10. เก็บ `kind=trace_crop`

### 7.5 Label logic

สำหรับ `figure_crop` ใช้ caption จริงจาก PDF

สำหรับ `trace_crop`, `_trace_caption()` ใช้ลำดับ:

1. `visual_metadata.subtopic`
2. `visual_metadata.section`
3. scan text line หา algorithm name เช่น Selection/Insertion/Bubble/Shell/Quick/Merge/Heap/Cocktail/Counting/Radix/Bucket + `sort`
4. fallback `ภาพขั้นตอนจากหน้า N`

manifest metadata ต้อง match PDF SHA-256 จึงจะถูกนำมาใช้ ถ้าไม่มี metadata ที่ดี label อาจ
กว้างหรือผิด algorithm ได้

### 7.6 User-facing selection และภาพต่อเนื่อง

`RAGService.select_user_visible_images()` อนุญาตแค่ `figure_crop`/`trace_crop`; ห้าม
`embedded_image`/`vector_page_render`

flow ของคำถามต่อเนื่อง:

1. ผู้ใช้ถามหัวข้อ เช่น `selection sort`
2. answer เก็บ source refs และ previous user query
3. ผู้ใช้ถาม `ภาพ`
4. clarification resolve topic จาก previous turn
5. retrieval ใช้ topic เดิม
6. previous answer refs มี priority ก่อน current refs
7. query ภาพตาม `(source_id, page_number)` แล้ว filter crop kinds
8. แสดงภาพพร้อม label, source และ page

### 7.7 Inefficiencies / known limitations ตอนนี้

- heuristic grouping ด้วย y-gap อาจรวม visual กับ decoration, crop กว้างเกิน หรือแยก step ที่ควรรวม
- figure association เลือก drawing area ใหญ่สุดเหนือ caption จึงอาจจับผิดเมื่อมีหลาย figure ในหน้าเดียว
- label จาก section/subtopic อาจกว้าง; regex อาจเจอชื่อ algorithm อื่นก่อน
- fallback `ภาพขั้นตอนจากหน้า N` semantic ไม่ดีพอ
- ยังไม่มี visual quality score: black/blank ratio, edge density, text-only detection, aspect sanity, duplicate IoU หรือ caption confidence
- `RAG_INDEX_IMAGES=false` เป็น default; ตอนนี้ image retrieval คือ text hit -> page -> visual ยังไม่ใช่ query-to-image semantic retrieval
- ยังไม่มี manual clip override/visual audit UI
- มี `vector_page_render` 71 รายการเป็นสัญญาณว่า crop coverage ยังไม่ครบ
- ยังไม่มี step sequence/prev-next teaching UI และ animation จริง

ไฟล์ที่ต้องเริ่มทำต่อ: `rag/pdf_ingest.py`, `rag/service.py`,
`real_data/topic_01_manifest.json`, `scripts/ingest_pdf.py` และ tests ใน `tests/`

## 8. Setup บนเครื่องใหม่

### 8.1 แตกไฟล์และสร้าง environment

หลังแตก ZIP จะได้โฟลเดอร์ `ai-chat-bot/`:

~~~bash
cd ai-chat-bot
cp .env.example .env
# แก้ .env ในเครื่องใหม่ ใส่ GEMINI_API_KEY และ DATABASE_URL
bash handover/setup_new_machine.sh
source venv/bin/activate
~~~

สคริปต์จะสร้าง venv ใหม่, install `requirements.txt`, ตรวจว่ามี environment values,
ตรวจ PostgreSQL extensions และรัน tests

ถ้าเป็น Windows:

~~~powershell
py -m venv venv
.\\venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py'
~~~

ห้าม copy `venv/` ของ Linux ไป Windows หรือ copy `.venv/` เดิมข้ามเครื่อง

### 8.2 ตรวจ environment แบบไม่เปิดเผยค่า

~~~bash
python - <<'PY'
from dotenv import load_dotenv
load_dotenv()
from rag.config import Settings
s = Settings.from_env()
print("Gemini configured:", bool(s.gemini_api_key))
print("Database configured:", bool(s.database_url))
PY
~~~

### 8.3 ตรวจ Supabase/pgvector

~~~bash
python - <<'PY'
from dotenv import load_dotenv
load_dotenv()
from rag.config import Settings
import psycopg
s = Settings.from_env()
with psycopg.connect(s.database_url, connect_timeout=10) as conn:
    with conn.cursor() as cur:
        cur.execute("select extname from pg_extension where extname in ('vector','pg_trgm') order by extname")
        print("extensions:", [row[0] for row in cur.fetchall()])
        cur.execute("select count(*) from rag_document_chunks")
        print("chunks:", cur.fetchone()[0])
        cur.execute("select count(*) from rag_document_images")
        print("images:", cur.fetchone()[0])
PY
~~~

ไม่ต้อง re-ingest ถ้า source PDF hash เหมือนเดิมและ DB ยังมี index เดิม

### 8.4 Run

~~~bash
python -m streamlit run app.py
~~~

ทดสอบอย่างน้อย:

- `การเรียงลำดับข้อมูลคือ`
- `selection sort`
- follow-up `ภาพ`
- typo/transliteration ของชื่อหัวข้อ
- out-of-scope `Quick Sort`

ถ้า source PDF เปลี่ยน:

~~~bash
python -m scripts.ingest_pdf --force
~~~

ถ้าแก้ crop/label อย่างเดียว:

~~~bash
python -m scripts.ingest_pdf --images-only
~~~

สำหรับ Streamlit Cloud ให้ตั้ง `GEMINI_API_KEY` และ `DATABASE_URL` ใน Secrets ของ app
เท่านั้น ไม่ใส่ secret ลง Git หรือ ZIP

## 9. Next steps ที่ควรทำต่อ

### P0 — Crop/label quality

- ทำ visual audit CLI/UI แสดง page, candidate boxes, crop preview และ label
- รองรับ accept/reject/edit clip แล้วบันทึก manifest override
- เพิ่ม black/blank/text-only/edge-density/area quality score
- เพิ่ม duplicate IoU suppression และ caption-distance confidence
- ใช้ connected/overlap graph แทน y-gap อย่างเดียว
- ตรวจ regression สำหรับ visual ของ 6 หัวข้อหลัก

### P0 — Curriculum/RAG evaluation

- สร้าง test set definition, principle, trace, comparison, visual, typo, follow-up และ OOS
- วัด Hit@1/3/5, citation accuracy, faithfulness, answer relevance และ rejection rate

### P1 — Latency

- วัด retrieval, TTFT และ total latency P50/P95
- ตรวจ Gemini timeout rate และเพิ่ม canonical/extractive cache อย่างมีหลักฐาน

### P1 — Visual retrieval/teaching

- optional image embedding + visual rerank
- group trace crops เป็น step sequence
- ทำ prev/next explanation ต่อ step
- ยังต้องรักษา source-only rule และห้ามใช้ synthetic/external image

### P2 — User study

- SUS/usability
- learning gain pre/post
- task completion
- qualitative feedback เรื่องคำตอบและ crop quality

## 10. Rules ที่ห้ามถอยกลับ

- ห้าม fallback web/external content ใน runtime
- ห้าม local lexical เป็น production fallback เมื่อ PostgreSQL ใช้ไม่ได้
- ห้ามแสดง full-page render หรือ raw embedded image ต่อ user
- ห้ามเพิ่ม curriculum topic นอก 6 หัวข้อโดยไม่มี approval
- ห้ามอ้างว่า zero hallucination
- ห้าม commit `.env` หรือ live credential

## 11. Verification ที่ควรทำหลังย้าย

~~~bash
git status -sb
git log --oneline -10
python -m unittest discover -s tests -p 'test_*.py'
python -m compileall -q app.py prompt.py rag scripts tests ui
~~~

จากนั้นเปิด Streamlit และทดสอบคำถามในหัวข้อ 8.4 ก่อนเริ่มแก้ crop pipeline
