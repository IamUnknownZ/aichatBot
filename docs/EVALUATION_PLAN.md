# Evaluation Plan — RAG Sorting Tutor

เป้าหมายคือวัดทั้งความถูกต้อง การไม่ hallucinate คุณภาพ retrieval และความเร็ว ไม่ใช่วัดแค่ว่า chatbot ตอบได้หรือไม่

## A. ชุดคำถามทดสอบ

ควรสร้างอย่างน้อย 80-120 คำถาม แบ่งเป็นกลุ่มดังนี้

1. Direct in-domain เช่น Bubble Sort คืออะไร
2. Concept explanation ที่ต้องอธิบายให้เห็นภาพ
3. Comparison เช่น Bubble Sort เทียบ Selection Sort
4. Procedure หรือ trace
5. Code-requested คือผู้ใช้ขอโค้ดจริง
6. No-code-requested เพื่อตรวจว่าระบบไม่ยัดโค้ดมาเอง
7. Out-of-scope คือคำถามคนละเรื่องกับเอกสาร
8. In-domain but absent คืออยู่เรื่อง sorting แต่ข้อมูลนั้นไม่มีในเอกสาร
9. Follow-up เช่น แล้วตัวเมื่อกี้ต่างกันยังไง
10. Figure-based สำหรับเวอร์ชันที่เอกสารมีภาพ
11. Social intent เช่น ไง, สวัสดี, ขอบคุณ, help
12. Topic-only short query เช่น บับเบิลซอร์ท, quick sort
13. Transliteration variants เช่น บับเบิลซอร์ต / บับเบิ้ลซอร์ท
14. Typo / noisy query เช่น บับเบิ้ลซอท, seletion sort
15. Ambiguous short follow-up ที่ต้องใช้บริบท เช่น แล้วตัวนี้ล่ะ

แต่ละข้อควรมี question, category, expected_pages, reference_answer, should_abstain, needs_code และ notes

## B. Metrics

### Retrieval
- Hit@K หรือ Recall@K
- Context Precision
- Mean top relevance score
- Retrieval latency

### Generation
- Faithfulness หรือ Groundedness
- Answer relevance
- Citation accuracy
- Conciseness
- Explanation clarity จากผู้ประเมิน

### Anti-hallucination และ Abstention
- Out-of-scope rejection rate
- Unsupported-question rejection rate
- False-answer rate: ควรปฏิเสธแต่กลับตอบ
- False-rejection rate: เอกสารมีคำตอบแต่ระบบปฏิเสธ
- Adaptive-gate false-positive rate
- Adaptive-gate false-negative rate

### Conversational robustness
- Alias coverage count
- Clarification dictionary coverage count
- Exact alias recognition accuracy
- Substring alias recognition accuracy
- Fuzzy alias recognition accuracy
- Social-intent accuracy
- Topic normalization accuracy
- Concept-only query acceptance rate
- Typo / transliteration recovery rate
- Follow-up rewrite success rate
- Clarification trigger precision
- Unnecessary-clarification rate
- Clarification resolution rate
- Average clarification turns before retrieval
- Context-resolved clarification accuracy
- Short-query retrieval Hit@K
- False topic mapping rate
- Query-understanding P50/P95 latency
- Clarification-router P50/P95 latency
- Raw query vs normalized/expanded query Hit@K

ควรมี negative questions อย่างน้อย 20-30 ข้อเพื่อ tune ค่า RAG_MIN_SCORE

### Performance
- End-to-end latency: P50 และ P95
- Time to first token (TTFT)
- Retrieval latency
- Input context size
- Output length
- Cold start เทียบ warm start
- PostgreSQL mode เทียบ in-memory mode
- Profile/history enabled เทียบ disabled
- DB persistence overhead หลัง response

### UX / Personalization
- SUS หรือ usability scale ที่กำหนดไว้ล่วงหน้า
- ความอ่านง่ายบนมือถือ/แท็บเล็ต/PC
- ความมีประโยชน์ของ recent questions
- perceived distraction ของ mascot
- perceived friendliness / teaching presence
- task completion time
- name-collision error ใน pilot

## C. Experiment สำหรับบทที่ 4

| Variant | Retrieval | Context |
|---|---|---|
| Baseline | ไม่มี RAG | PDF ทั้งเล่ม |
| RAG-A | Vector only | top-k |
| RAG-B | Hybrid vector + lexical | top-k |
| RAG-C | Hybrid + relevance gate | top-k + abstention |

สำหรับ UX ให้เพิ่ม A/B หรือ within-subject pilot:
- UI-A: chat UI แบบเรียบ ไม่มี profile/mascot
- UI-B: seamless UI + name profile + recent questions + subtle mascot

วัด usability, task time, perceived distraction และ latency โดยไม่สรุปว่า mascot ช่วยการเรียนจนกว่าจะมีผลการทดลองจริง

จากนั้นทดลอง parameter เช่น
- chunk size: 700, 1000, 1200, 1500 chars
- overlap: 10%, 15%, 20%
- top-k: 3, 5, 8
- relevance threshold หลายค่า

เลือก configuration จาก balance ของ retrieval recall, hallucination และ latency ไม่เลือกจาก accuracy เพียงตัวเดียว

## D. Engineering target รุ่นแรก

ค่าเหล่านี้เป็นเป้าหมายที่ต้องวัดจริงก่อนเขียนเป็นผลวิจัย
- In-domain retrieval Hit@5 อย่างน้อย 90%
- Citation accuracy อย่างน้อย 95%
- Unsupported-question rejection อย่างน้อย 90%
- False-answer rate ไม่เกิน 5%
- P50 end-to-end latency ไม่เกิน 4 วินาทีบน warm app
- TTFT ไม่เกิน 1.5 วินาทีเมื่อ network และ API ปกติ
