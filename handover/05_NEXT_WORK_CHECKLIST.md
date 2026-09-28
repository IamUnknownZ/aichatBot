# Next Work Checklist

ลำดับนี้แนะนำสำหรับ agent/คนที่รับช่วงต่อ

## P0 — Image crop / label quality

เป้าหมาย:
ลด `vector_page_render` 71 รายการ และเพิ่ม crop ที่มี semantic label จริง

- [ ] ทำ visual audit CLI/UI
- [ ] แสดง page + candidate boxes + crop preview
- [ ] accept/reject/manual edit
- [ ] save manual clip ลง manifest
- [ ] เพิ่ม quality score
- [ ] detect blank/black crop
- [ ] IoU duplicate suppression
- [ ] caption-distance score
- [ ] nearest heading/caption label
- [ ] label confidence
- [ ] sequence/step metadata
- [ ] regression visual tests สำหรับ 6 curriculum topics

Definition of done:
- ทุกหัวข้อหลักมี visual ที่ audit แล้วอย่างน้อย 1 ชุด ถ้า source มี visual
- ไม่มี full page แสดงต่อ user
- label ตรง algorithm/step
- visual follow-up เลือก source เดียวกับ answer ได้

## P0 — Curriculum evaluation

Primary topics:
1. หลักการเรียงลำดับข้อมูล
2. Bubble Sort
3. Selection Sort
4. Insertion Sort
5. Merge Sort
6. Counting Sort

สร้าง test set:
- definition
- principle
- step/trace
- comparison
- visual request
- typo/thai transliteration
- follow-up
- out-of-scope Quick/Shell/Heap

## P1 — RAG evaluation

- [ ] Hit@1 / Hit@3 / Hit@5
- [ ] citation page accuracy
- [ ] faithfulness
- [ ] answer relevance
- [ ] negative rejection
- [ ] TTFT P50/P95
- [ ] total latency P50/P95
- [ ] retrieval latency

## P1 — Answer latency

Generation API ยังเป็น bottleneck หลัก

ทำต่อ:
- cache simple canonical answers?
- direct/extractive paths สำหรับ simple factual queries
- test Gemini model config
- log timeout rate
- ไม่ลด grounding เพื่อแลกความเร็ว

## P1 — Visual retrieval

ปัจจุบัน text → page → image

future:
- optional image embeddings
- semantic visual rerank
- visual query evaluator
- ยังต้อง source-only

## P1 — Step-by-step visual teaching

อิงแนว educational chatbot / visual learning

- [ ] group trace crops เป็น sequence
- [ ] prev/next step UI
- [ ] text explanation per source step
- [ ] source page visible
- [ ] no synthetic external algorithm states

## P2 — User study

- SUS/usability
- learning gain pre/post
- task completion
- qualitative feedback
- confusing answers / crop quality feedback

## Rules ที่ห้ามถอยกลับ

- ห้าม fallback web
- ห้าม local lexical ใน production
- ห้าม full page ต่อ user
- ห้าม raw embedded image ต่อ user
- ห้ามเพิ่ม curriculum topic นอก 6 ตัวโดยไม่มี approval
- ห้ามอ้าง zero hallucination
- ห้าม commit .env
