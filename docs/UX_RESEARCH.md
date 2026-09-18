# UX / Personalization Research Basis

อัปเดต: 18 กันยายน 2026

เอกสารนี้อธิบายว่าฟีเจอร์ UI, mascot, personalization และ performance ของ AI Tutor ไม่ได้เพิ่มเพราะความสวยอย่างเดียว แต่มีเหตุผลจากงานวิจัยและข้อจำกัดด้าน cognitive load

## 1. Chat-first, content-first interface

Kuhail et al. (2023) ทบทวนงาน educational chatbot 36 งาน และชี้ว่าการออกแบบควรเน้น interaction ที่จำเป็นต่อการเรียน หลีกเลี่ยงสิ่งรบกวน และควรประเมิน usability อย่างชัดเจน งานเดียวกันพบว่าประมาณ 27.77% ของระบบที่ทบทวนใช้ personalized learning และยกตัวอย่างการเก็บ interaction เพื่อปรับ instruction/feedback ให้เข้ากับผู้เรียน

Design decision:
- chat เป็นพื้นที่หลัก ไม่ใช้ dashboard ที่แน่น
- advanced/debug ถูกซ่อนไว้ใน expander
- quick prompts มีจำนวนน้อยและเกี่ยวกับงานเรียนโดยตรง
- ไม่มี popup/link ภายนอกที่รบกวน flow การเรียน

Reference:
Kuhail, M. A., Alturki, N., Alramlawi, S., & Alhejori, K. (2023). Interacting with educational chatbots: A systematic review. Education and Information Technologies, 28, 973–1018.
https://link.springer.com/article/10.1007/s10639-022-11177-3

## 2. Mascot / pedagogical agent

Liu & Su (2024) ทำ systematic review และ meta-analysis ของ facial anthropomorphism ใน learning materials จาก 33 experiments พบผลเชิงบวกต่อ transfer, retention และ comprehension แต่รายงานผลด้าน cognitive load ที่มีความซับซ้อนและเตือนว่าการออกแบบที่เพิ่มองค์ประกอบมากเกินอาจสร้าง extraneous load

Davis (2018) meta-analysis 20 experiments (N=3,841) พบ pedagogical-agent gesturing มีผลเล็กถึงปานกลางต่อ near transfer และ retention แต่ character agents บางแบบอาจเพิ่ม cognitive load

Design decision:
- mascot ขนาดเล็ก อยู่เฉพาะ hero ไม่ลอยทับเนื้อหา
- animation ช้าและ subtle
- ไม่มีเสียง / auto-play
- CSS only ไม่มี network asset
- ปิด animation อัตโนมัติด้วย prefers-reduced-motion
- mascot ไม่มีหน้าที่ให้ข้อมูลแทนเนื้อหา จึงไม่แย่ง attention จากคำตอบ

References:
Liu, K., & Su, P. (2024). Effectiveness of facial anthropomorphism design for improving multimedia learning outcomes: systematic review and meta-analysis. Smart Learning Environments, 11, 42.
https://link.springer.com/article/10.1186/s40561-024-00332-7

Davis, R. O. (2018). The impact of pedagogical agent gesturing in multimedia learning environments: A meta-analysis. Educational Research Review, 24, 193–209.
https://doi.org/10.1016/j.edurev.2018.05.002

## 3. Personalization and remembered interactions

Educational-chatbot reviews consistently identify personalized support as a central use case. Kuhail et al. describe systems that monitor prior learner interactions to provide customized instruction and feedback. A 2025 empirical study on personalization capabilities of tutor bots analyzed conversations of 51 graduate students and focused on how tutoring interactions can be tailored to individual needs.

Design decision:
- name-only onboarding provides a lightweight identity for a classroom prototype
- PostgreSQL remembers recent questions for continuity
- the generation model still receives only a bounded recent conversation window to control latency/context size
- profile history is not inserted into every prompt automatically; only current session history is used for conversational continuity
- no password/authentication is claimed
- no device fingerprinting is used

Reference:
Personalization capabilities of current technology chatbots in a learning environment: An analysis of student-tutor bot interactions. Education and Information Technologies (2025).
https://link.springer.com/article/10.1007/s10639-025-13369-z

## 4. Why name-only is a profile, not authentication

The requirement is deliberately lightweight: one display name and no password. This supports continuity in a classroom prototype but cannot securely prove identity.

Implementation:
- display name is normalized with Unicode NFKC + casefold
- same normalized name restores the same profile
- duplicate human names can collide, so users should choose a classroom-unique nickname
- system does not use hidden fingerprinting to disambiguate users
- if PostgreSQL is unavailable, profile falls back to current-session behavior rather than slowing or breaking tutoring

Research/ethics implication:
Chapter 5 should explicitly list name collision and lack of strong authentication as limitations. If the project later stores sensitive/graded information, replace name-only profile with proper authentication.

## 5. Streaming and perceived speed

The system streams generation with Streamlit instead of waiting for a complete answer. Streamlit provides native chat containers and streaming support, while current Streamlit caching APIs allow the RAG service/database resources to be reused across reruns.

Implementation:
- st.cache_resource for the RAG service
- retrieval logging removed from the pre-generation critical path
- profile/history writes happen after the visible response completes
- PostgreSQL uses a connection pool
- only top-k chunks and bounded recent chat history are sent to the LLM

Streamlit documentation:
https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource
https://docs.streamlit.io/develop/concepts/architecture/fragments

Psycopg pooling documentation:
https://www.psycopg.org/psycopg3/docs/advanced/pool.html

## 6. Why connection pooling

Psycopg documentation notes that establishing database connections can be relatively expensive and a pool can reduce latency by keeping connections available.

Design decision:
- PgVectorStore owns one shared ConnectionPool
- st.cache_resource means the RAG service/store is reused across Streamlit reruns
- pool is intentionally small (1–6 connections) because this is a classroom chatbot, not a high-throughput backend

## 7. Streamlit interaction optimization

Streamlit reruns the script on widget interaction. Current Streamlit versions provide cache_resource, forms, dialogs and fragments to control reruns.

Applied choices:
- onboarding uses st.dialog + st.form so typing does not run expensive RAG work on every keystroke
- model/debug controls are tucked into Advanced
- old assistant messages do not each create a custom iframe copy-button; only the newest answer creates one
- recent questions are loaded once on profile registration and then updated in Session State
- no database read is performed on every app rerun merely to redraw history

## 8. Conversational flexibility: intent routing + query rewriting

ปัญหาที่ผู้ใช้พิมพ์สั้น ๆ เช่น "ไง", "บับเบิลซอร์ท", "แล้วมันต่างกันยังไง" ไม่ควรถูกปฏิบัติเป็น document-search query แบบเดียวกันทั้งหมด

งาน CONQRR (Wu et al., EMNLP 2022) แสดงแนวคิด conversational query rewriting โดยเปลี่ยน utterance ที่ขึ้นกับบริบทให้เป็น standalone query ก่อนส่งเข้า retriever เพื่อให้ retrieval เข้าใจความต้องการได้ดีขึ้น

งาน MaFeRw (AAAI 2025) ระบุชัดว่า query ในระบบ RAG จริงมักมี ellipsis และ reference ที่กำกวมจากบทสนทนา จึงต้องมี query rewriting ก่อน retrieval

Review เรื่อง university chatbots ปี 2025 ระบุว่า greeting/farewell เป็น intent พื้นฐานของ chatbot และคำ intent เดียวกันสามารถถูกพูดได้หลายรูปแบบ เช่น Hello, Hi, Hey

Query Understanding for Search Engines (2020) แยก query understanding ออกเป็น query classification, intent understanding, spelling correction และ query rewriting ซึ่งตรงกับปัญหาคำทับศัพท์/พิมพ์ผิดของระบบนี้

Design decision:
- greeting / thanks / farewell / help ตอบด้วย local intent router ไม่เรียก RAG และไม่เรียก Gemini
- topic-only query เช่น "บับเบิลซอร์ท" rewrite เป็น standalone query ที่มี canonical term "Bubble Sort"
- เก็บ alias ไทย/อังกฤษ/คำทับศัพท์หลายรูป
- short typo ใช้ conservative fuzzy matching เฉพาะข้อความสั้น เพื่อลด false mapping
- follow-up context ถูกพ่วงเฉพาะเมื่อมี marker เช่น "แล้ว", "มัน", "ตัวนี้" แทนการพ่วงคำถามก่อนหน้ากับทุก short query
- out-of-domain ยังต้องผ่าน relevance gate เหมือนเดิม

References:
Wu, Z. et al. (2022). CONQRR: Conversational Query Rewriting for Retrieval with Reinforcement Learning. EMNLP 2022.
https://aclanthology.org/2022.emnlp-main.679/

Wang, Y. et al. (2025). MaFeRw: Query Rewriting with Multi-Aspect Feedbacks for Retrieval-Augmented Large Language Models. AAAI 2025.
https://ojs.aaai.org/index.php/AAAI/article/view/34732

A review of university chatbots for student support: FAQs and beyond. Discover Education (2025).
https://link.springer.com/article/10.1007/s44217-025-00397-7

Deng, H. & Chang, Y. (eds.) (2020). Query Understanding for Search Engines. Springer.
https://link.springer.com/book/10.1007/978-3-030-58334-7

## 9. Educational chatbot UX evaluation

A 2025 study proposed evaluating educational-chatbot UX by combining Chatbot Usability Questionnaire (CUQ), User Engagement Scale short form (UES-SF), error rate and response time rather than judging visual appeal alone.

Design decision:
- UI evaluation must include usability + engagement + objective task performance
- compare conversational success/error rate before and after query router
- collect perceived readability and distraction, not only "สวย/ไม่สวย"
- measure response time for local social intent separately from RAG questions

Reference:
A Weighted Composite Metric for Evaluating User Experience in Educational Chatbots: Balancing Usability, Engagement, and Effectiveness. Future Internet, 17(2), 64 (2025).
https://www.mdpi.com/1999-5903/17/2/64

## 10. Pedagogical-agent cognitive-load caution

Li et al. (2025) meta-analysis จาก 24 studies พบว่า pedagogical agents ลด cognitive load โดยรวมเพียงเล็กน้อย และผลขึ้นกับ appearance, role, subject domain, media form และ learning pace งานทบทวนยังกล่าวถึงกรณีที่ agent ดึง visual attention จากงานเรียนได้

Design decision:
- mascot ทำหน้าที่เป็น guide cue ขนาดเล็ก
- sorting-bar animation ใช้เฉพาะ hero และเคลื่อนไหวช้า
- prefers-reduced-motion ปิด animation ได้
- ไม่ใช้ full-screen character หรือ animation ต่อเนื่องในพื้นที่คำตอบ

Reference:
Li, H., Wang, Z., Ding, L., Zhang, J., & Wang, G. (2025). The facts about the effects of pedagogical agents on learners' cognitive load: a meta-analysis based on 24 studies. Frontiers in Psychology, 16.
https://doi.org/10.3389/fpsyg.2025.1635465

## 11. Evaluation additions for Chapter 4

UI/profile experiment should measure:
- SUS or another usability instrument
- perceived readability
- usefulness of recent-question memory
- perceived distraction from mascot (Likert item)
- task completion time
- TTFT / total latency with profile enabled vs disabled
- DB persistence overhead after response
- mobile/tablet readability
- error rate for name collision during pilot testing

Do not claim mascot or personalization improves learning in this project unless the project actually measures learning outcomes. Research supports the design rationale, but our Chapter 4 must report our own measured results.
