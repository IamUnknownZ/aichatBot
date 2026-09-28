# Research Inventory — Everything Referenced by the Project

ไฟล์นี้เป็น index สำหรับงานวิจัยและเอกสารประกอบทั้งหมดที่ถูกอ้างถึงในประวัติการออกแบบ
ระบบ ไม่ใช่การแทนที่ bibliography ฉบับเต็ม

## 1. Full bibliography and research mapping

- docs/RESEARCH_REFERENCES.md
  - theses/degree projects ที่ใกล้กับระบบ 15 รายการ
  - core papers 20 รายการ
  - mapping จากงานวิจัยไปยัง feature
  - URL/DOI/รายละเอียดการใช้งานเมื่อมี
- docs/RESEARCH_MATRIX.md
  - งาน 5 บทที่ใช้เป็นต้นแบบโดยตรง
  - งานสนับสนุนด้าน RAG, vector DB, multimodal PDF, latency และ education
  - repository URLs
  - feature-to-research mapping และโครงอ้างอิงบทที่ 1–5

## 2. Research-backed implementation notes

- docs/QUERY_FLEXIBILITY_RESEARCH.md
  - conversational query rewriting
  - query expansion
  - Thai/English typo and transliteration handling
  - clarification for ambiguous requests
  - implementation and evaluation additions
- docs/UX_RESEARCH.md
  - chat-first interface
  - pedagogical agent/mascot
  - remembered interactions and profile limits
  - streaming/perceived speed
  - Streamlit interaction optimization
  - conversational routing and UX evaluation
- docs/EVALUATION_PLAN.md
  - definition/principle/visual/follow-up test set
  - Hit@K, faithfulness, relevance, citation and rejection metrics
  - latency/TTFT, usability and experiment plan
- docs/UI_REDESIGN_PLAN.md
  - rationale and target behavior for the two-sided tutor UI

## 3. Local reference PDFs and project summaries

- docs/Enabling Learning of Programming through Educational Chatbot.pdf
  - local reference for multimodal learning, visualization, animation and interactive exercise
- AI_Chatbot_Project_Summary.pdf
  - project summary artifact carried with the source package
- อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf
  - original course/reference material
- docs/อัลกอริทึมการเรียงลำดับข้อมูล_ระดับมหาวิทยาลัยปี1.pdf
  - documentation copy of the course/reference material

## 4. Supporting engineering/knowledge-base documents

- docs/DATA_DICTIONARY.md
- docs/REAL_DATA_TOPIC1_DATA_DICTIONARY.md
- docs/DEPLOYMENT.md
- PROJECT_FRAMEWORK.md
- handover/02_RESEARCH_AND_ARCHITECTURE.md
- handover/03_IMAGE_CROP_LABEL_PIPELINE.md

These explain how the research was translated into schemas, retrieval behavior, visual
extraction, deployment constraints and the next research/evaluation work. All listed files
are included in the portable ZIP.
