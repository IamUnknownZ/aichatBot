# Development History — ตั้งแต่เริ่มจนถึงปัจจุบัน

เอกสารนี้สรุปทั้ง Git history และ milestone ที่เกิดขึ้นจริงในโปรเจกต์

## Phase 0 — Prototype เดิม

โปรเจกต์เริ่มจาก Streamlit chatbot สำหรับตอบคำถามเรื่อง Sorting

แนวทางช่วงแรก:
- ส่ง context จาก PDF ให้ LLM มาก
- RAG ยังไม่เข้ม
- ภาพและ citation ยังไม่เป็นระบบ
- คำถามกำกวม / คำทับศัพท์ / ภาษาไทยสะกดผิดยังรับมือไม่ดี
- UI ยังเป็น chatbot ทั่วไป

ปัญหาที่พบ:
- long context ช้า
- ความเสี่ยง hallucination
- citation ไม่แน่นอน
- retrieval ยังไม่แยกแหล่งข้อมูลชัด
- ไม่เหมาะกับ deployment ที่ต้องเปิดใช้ต่อเนื่อง

## Phase 1 — Citation + Python answer rules

Git:
- `c2a702f feat: enforce Python code inclusion and PDF page citations`

พัฒนา:
- citation ผูกกับเลข physical PDF page
- แยกหน้าที่ของ generator กับ citation renderer
- ตั้ง rule เรื่อง code/pseudocode ให้ตอบตามประเภทคำถาม

## Phase 2 — Grounded RAG + Profile + UI

Git:
- `fe4561e feat: upgrade tutor with grounded RAG, profiles, and seamless UI`

พัฒนา:
- RAG pipeline จริง
- source/page metadata
- relevance gate / abstention
- profile/history เบื้องต้น
- Streamlit UI ต่อเนื่องขึ้น
- เก็บ performance/retrieval logs ใน schema

## Phase 3 — Query lexicon / Adaptive routing

Git:
- `b10b63d feat: add robust query lexicon and adaptive routing`

พัฒนา:
- dictionary/alias สำหรับคำไทย อังกฤษ คำทับศัพท์ และคำสะกดหลายแบบ
- topic / concept / action matching
- query expansion
- รองรับคำสั้น เช่น sort / ซอร์ท / บับเบิลซอร์ท
- ลดการเรียก LLM ใน intent ที่ตอบตรงได้

ข้อควรระวัง:
- fuzzy matching เคยทำให้ Heap Sort ไปใกล้ Shell Sort
- ภายหลังเพิ่ม non-curriculum guard ป้องกัน fuzzy ข้ามขอบเขต

## Phase 4 — Two-sided messaging UI

Git:
- `d30099c feat: redesign tutor chat as two-sided messaging UI`

พัฒนา:
- user / assistant อยู่คนละฝั่งแบบ messaging app
- chat bubble
- dark UI
- profile / recent question UX

## Phase 5 — Mixed-initiative clarification

Git:
- `015d0a7 feat: add mixed-initiative clarification and fix chat contrast`

พัฒนา:
- ถ้าถามคำกว้าง เช่น `sort` ระบบถามกลับก่อน
- รองรับ follow-up เช่น “ภาพ”, “โค้ด”, “ทำงานยังไง”
- ใช้ previous topic/history resolve คำสั้น
- social intent เช่น greeting / thanks ไม่ต้องผ่าน RAG

## Phase 6 — Closed-source RAG + pgvector production

Git:
- `d1f50b5 feat: harden closed-source vector RAG for deployment`

เปลี่ยนใหญ่:
- Knowledge base = `real_data/` เท่านั้น
- ไม่มี external/web fallback
- PostgreSQL + pgvector + pg_trgm
- hybrid semantic + lexical retrieval
- HNSW vector index
- source hash / source_id
- production fail-closed
- Streamlit Cloud ใช้ DATABASE_URL
- local lexical เหลือสำหรับ test/developer utility เท่านั้น

Supabase ถูกใช้เป็น managed PostgreSQL

ปัญหาที่แก้ระหว่างทำ:
- DATABASE_URL password มี special characters ต้อง URL encode
- ingest script เดิม fallback local แบบเงียบ
- เปลี่ยน ingest เป็น strict pgvector
- เพิ่ม `python -m scripts.ingest_pdf`

## Phase 7 — Definition reranking + latency

ปัญหา:
- “การเรียงลำดับข้อมูลคือ” ดึงหน้าวัตถุประสงค์/หัวกระดาษ
- Gemini generation เคย TTFT > 100 วินาที
- หลัง timeout fallback เดิมเอา raw chunk มาวาง ทำให้อ่านยาก

พัฒนา:
- definition-aware query expansion
- definition reranking
- algorithm topic reranking
- candidate retrieval ก่อนตัด top-k
- simple definition ใช้ extractive grounded fast path ไม่เรียก Gemini
- generation timeout + grounded fallback
- Gemini thinking MINIMAL

ผลที่เคยวัด:
- retrieval ~10 ms ใน local lexical
- Gemini generation เคย ~100s
- after timeout guard/fallback ลด user wait ลงมาก
- definition fast path answer stage แทบไม่เพิ่ม latencyหลัง retrieval

## Phase 8 — Visual RAG / crop image

Git:
- `020ed25 fix: structure tutor answers and add trace visuals`

ก่อนแก้:
- PDF diagram แสดงเป็น full A4 page
- บาง embedded image เป็นดำ/ใช้ไม่ได้
- visual follow-up หาไม่ตรง topic

พัฒนา:
- `figure_crop`: หา caption “รูปที่ / Figure / Fig.” แล้ว crop vector region เหนือ caption
- `trace_crop`: หา cluster ของ vector drawings เช่น array/trace/table แม้ไม่มี caption
- full page เก็บ internal fallback แต่ UI ห้ามแสดง
- visual follow-up “ภาพ” ใช้ previous topic
- previous source references มี priority ก่อน current retrieval refs
- เพิ่ม `--images-only` เพื่อ refresh image catalog โดยไม่ re-embed text

Selection Sort audit:
- textbook หน้า 4 ได้ trace crop ประมาณ 553×176
- หน้า 5 ได้ trace หลายช่วง
- English PDF หน้า 15 ได้ trace crop ประมาณ 545×240

Supabase หลัง refresh:
- visual 130
- trace_crop 49
- figure_crop 2

## Phase 9 — Structured answer formatting

อยู่ใน commit `020ed25`

พัฒนา:
- Markdown heading
- ความหมาย
- numbered หลักการทำงาน
- bullet spacing
- fallback ที่อ่านง่าย ไม่ dump raw chunk

## Phase 10 — Ghost overlay fix + curriculum locking

Git:
- `f102c55 fix: stabilize chat reruns and lock six-topic curriculum`

Ghost overlay:
- Streamlit streamed message เดิมกลายเป็น stale/faded element ตอน rerun
- เพิ่ม `st.rerun()` หลัง persist คำตอบ เพื่อให้ DOM กลับมา render จาก session history

Curriculum:
- เริ่มแรก lock ผิดเป็น 6 algorithms คนละชุด
- ภายหลังแก้ตามรูปที่อนุมัติจริง

## Phase 11 — Final approved curriculum

Git:
- `3bd2363 fix: match curriculum topics to approved source`

บังคับ:
1. หลักการเรียงลำดับข้อมูล
2. Bubble Sort
3. Selection Sort
4. Insertion Sort
5. Merge Sort
6. Counting Sort

Counting Sort แทน Quick Sort

Quick/Shell/Heap/Radix/Bucket เป็น reference-only

## Git history ที่สำคัญ

```
f3216c9 main
7b7e493 main
c2a702f enforce Python code inclusion and PDF page citations
fe4561e grounded RAG, profiles, UI
b10b63d robust query lexicon and adaptive routing
d30099c two-sided messaging UI
015d0a7 mixed-initiative clarification
d1f50b5 closed-source pgvector production hardening
020ed25 structured answers + trace visuals
f102c55 ghost rerun fix + curriculum lock
3bd2363 exact approved curriculum
```

ประวัติเต็มยังอยู่ใน `.git/`:
```bash
git log --oneline --decorate --all
git show <commit>
```
