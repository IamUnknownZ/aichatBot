# Research References for AI Sorting Tutor RAG

รายการนี้คัดเพื่อใช้ได้ทั้งตอนพัฒนาระบบและเขียนบทที่ 2-5

## A. Full theses และงานระดับปริญญาที่ใกล้กับโปรเจกต์

1. Muhammad Farhan Fahrezy (2026), IPB University
   Pengembangan Chatbot Berbasis Large Language Model dengan Pendekatan Retrieval-Augmented Generation untuk Layanan Informasi Akademik
   Undergraduate thesis. ใช้ hybrid search, RRF, cross-encoder reranking, section-aware chunking และ RAGAS รายงาน faithfulness 0.992 และ response time ลดจาก 29.08s เป็น 3.90s หลังปรับ retrieval
   https://repository.ipb.ac.id/handle/123456789/178425

2. Faliqul Ishbah (2026), Universitas Muhammadiyah Malang
   Pengembangan Chatbot Berbasis Retrieval-Augmented Generation (RAG) Pada Domain Akademik
   Undergraduate thesis. ใช้ vector database + Gemini และ strict fallback เมื่อข้อมูลไม่อยู่ในฐานความรู้
   https://eprints.umm.ac.id/id/eprint/33379/

3. Jukka Veijanen (2025), Theseus
   Development of a Thesis Guidance Chatbot (PoC)
   Thesis. Python + Streamlit + RAG + ChromaDB จึงใกล้กับ UI stack ของเราโดยตรง
   https://www.theseus.fi/handle/10024/905602

4. Mohammad Labib Husain (2025), Universitas Pendidikan Indonesia
   Pengembangan Chatbot Informasi Administrasi Akademik FPMIPA UPI Berbasis Retrieval Augmented Generation (RAG)
   S1 thesis ใช้ LLM, RAG และ RAGAS evaluation
   https://repository.upi.edu/138355/

5. Muhamad Fadhly Rafiansyah et al. (2026), Universitas Pendidikan Indonesia
   Pengembangan AI Tutor Berbasis LLM dengan Retrieval-Augmented Generation pada Pembelajaran AI
   S1 thesis. เป็น AI tutor ที่ใช้ local curriculum/module เป็น knowledge base ใกล้กับผู้ช่วยสอนเฉพาะวิชาของเรา
   https://repository.upi.edu/151251/

6. Richa Kakati (2025), Asian Institute of Technology, Thailand
   Enhancing reliability and mitigating hallucinations in GPT-based tutors: a comparative study of RAG and document-augmented methods
   Master of Engineering thesis. เปรียบเทียบ baseline tutor, document-augmented tutor และ RAG ใน programming education โดยตรง
   https://mailserv02.ait.ac.th/ait-thesis/detail.php?q=B23628

7. Yana Dayinta Nesthi (2025), Universitas Gadjah Mada
   Integrasi Large Language Models dalam Rancang Bangun Chatbot Berbasis Retrieval Augmented Generation dan Cloud Computing untuk Efisiensi Akses Informasi pada Website Pendukung Akademik
   Final project. ประมวลผล text, image และ PDF เหมาะเป็น reference ด้าน multimodal ingestion และ cloud deployment
   https://etd.repository.ugm.ac.id/penelitian/detail/257206

8. Morin Adepatrick Damanik (2026), Institut Teknologi Sepuluh Nopember
   Development of an LLM- and RAG-Based Chatbot for Academic and Student Affairs Services in the Department of Information Systems at ITS
   Undergraduate thesis. ใช้ domain-specific academic documents กับ web chatbot
   https://repository.its.ac.id/142045/

9. Farel Abid Yasser Prayanto (2025), UPN Veteran Yogyakarta
   Implementasi Chatbot dengan Large Language Model Llama 3.1 dengan Teknologi Retrieval-Augmented Generation (RAG) untuk Layanan Akademik Mahasiswa Informatika
   Skripsi. ใช้ PDF preprocessing, chunking, hybrid BM25 + semantic retrieval, Streamlit UI และวัด context relevance/faithfulness/robustness
   https://eprints.upnyk.ac.id/id/eprint/45305/

10. Institut Teknologi PLN (2026)
    Implementasi Retrieval-Augmented Generation pada Chatbot Berbasis Web untuk Layanan Informasi Akademik di Institut Teknologi PLN
    Thesis. มี controlled prompt และการทดสอบ response restriction เมื่อคำถามไม่ควรตอบ
    https://repository.itpln.ac.id/id/eprint/7549/

11. Ahlis Dinal Bahtiar (2026), Universitas Diponegoro
    Optimasi Hyperparameter Arsitektur Retrieval-Augmented Generation (RAG) pada Chatbot Ekstraksi Informasi Jurnal Ilmiah
    Undergraduate thesis. ทดลอง 72 scenarios และวัด Coverage, ROUGE, BERTScore, response time รวมถึง chunk size, overlap และ top-k
    https://eprints2.undip.ac.id/id/eprint/58712/

12. Sai Prakash Reddy Rao (2025), Kennesaw State University
    OWLBOT: Designing and Developing an AI-Powered Peer Advisor Chatbot for University Websites
    Master’s thesis. RAG chatbot สำหรับเว็บมหาวิทยาลัย เน้น contextual understanding และ retrieval
    https://digitalcommons.kennesaw.edu/masterstheses/87/

13. University of Padua thesis
    Engineering a RAG Chatbot for Technical Manual Navigation through Vector Search and Cloud LLM Integration
    ใช้ PDF manuals, semantic chunking, vector search, Gemini API, FastAPI และ persistent memory
    https://thesis.unipd.it/handle/20.500.12608/95455

14. Hapid Ramdani (2026), UIN Sultan Syarif Kasim Riau
    Perancangan Chatbot Penelitian Dosen Menggunakan Metode Retrieval Augmented Generation
    Skripsi. ใช้เอกสารวิชาการเป็น custom knowledge base พร้อม citation
    https://repository.uin-suska.ac.id/92690/

15. Sabatino Larosa (2026), University of Genoa
    Un chatbot rivolto agli studenti per l’esplorazione dei corsi universitari basato su Retrieval-Augmented Generation
    Thesis. RAG chatbot สำหรับข้อมูลรายวิชาและมหาวิทยาลัย โดยออกแบบเพื่อลด hallucination
    https://unire.unige.it/handle/123456789/15559

## B. Core research papers สำหรับทฤษฎีและ architecture

1. Lewis et al. (2020), Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
   งานต้นทาง RAG: ผสาน parametric LM กับ external non-parametric memory
   https://arxiv.org/abs/2005.11401

2. Gao et al. (2023), Retrieval-Augmented Generation for Large Language Models: A Survey
   ใช้เป็นกรอบ Naive, Advanced และ Modular RAG
   https://arxiv.org/abs/2312.10997

3. Liu et al. (2023), Lost in the Middle: How Language Models Use Long Contexts
   รองรับเหตุผลที่ไม่ควรยัด PDF ทั้งเล่มเข้า long context ทุกคำถาม
   https://arxiv.org/abs/2307.03172

4. Asai et al. (2023), Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection
   ชี้ว่าควรประเมิน relevance ของ retrieval ไม่ใช่ retrieve แบบตายตัวทุกครั้ง
   https://arxiv.org/abs/2310.11511

5. Yan et al. (2024), Corrective Retrieval Augmented Generation
   แนวคิด retrieval evaluator และ confidence gate นำมาใช้กับ relevance threshold และ abstention
   https://arxiv.org/abs/2401.15884

6. Chen et al. (2023), Benchmarking Large Language Models in Retrieval-Augmented Generation
   กรอบทดสอบ noise robustness, negative rejection, information integration และ counterfactual robustness
   https://arxiv.org/abs/2309.01431

7. Es et al. (2023), RAGAS: Automated Evaluation of Retrieval Augmented Generation
   ใช้ประเมิน context relevance, faithfulness และ answer quality
   https://arxiv.org/abs/2309.15217

8. Saad-Falcon et al. (2023), ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems
   วัด context relevance, answer faithfulness และ answer relevance
   https://arxiv.org/abs/2311.09476

9. Niu et al. (2024), RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models
   ยืนยันว่า RAG ยัง hallucinate ได้ จึงต้องวัด faithfulness และ unsupported claims
   https://arxiv.org/abs/2401.00396

10. Ru et al. (2024), RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation
    แยกวิเคราะห์ error ของ retriever และ generator
    https://arxiv.org/abs/2408.08067

11. Khattab and Zaharia (2020), ColBERT
    reference ด้าน retrieval efficiency และ pre-computed document representations
    https://arxiv.org/abs/2004.12832

12. Gao et al. (2022), Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE)
    ใช้ต่อยอด query expansion เมื่อคำถามสั้นหรือกำกวม
    https://arxiv.org/abs/2212.10496

13. Yu et al. (2024), VisRAG
    reference สำหรับ phase ภาพประกอบและ multimodal PDF
    https://arxiv.org/abs/2410.10594

14. Jin et al. (2024), FlashRAG
    reference ด้าน modular RAG และ reproducible evaluation
    https://arxiv.org/abs/2405.13576

15. Ni et al. (2025), Towards Trustworthy Retrieval Augmented Generation for Large Language Models: A Survey
    ใช้กรอบ reliability, privacy, safety, explainability และ accountability ในข้อจำกัด/future work
    https://arxiv.org/abs/2502.06872

## C. Mapping งานวิจัยไปยัง feature ของระบบ

| Feature | Research basis |
|---|---|
| ไม่ส่ง PDF ทั้ง 101 หน้า | Lost in the Middle; Lewis RAG |
| Vector retrieval | Lewis; ColBERT |
| Hybrid semantic + lexical | IPB thesis; UPN thesis |
| Relevance threshold และไม่ตอบเมื่อหลักฐานไม่พอ | CRAG; RGB; UMM thesis; ITPLN thesis |
| Grounded prompt | RAGTruth; Self-RAG |
| Page-level citation | RAG/RAGAS และ thesis systems |
| Chunk/page metadata | IPB thesis; UPN thesis |
| PostgreSQL + pgvector | engineering design สำหรับ relational metadata + vector search |
| Streaming UI | วัด TTFT แยกจาก total latency |
| PDF image extraction | UGM thesis; VisRAG |
| Multimodal embedding ready | VisRAG |
| Faithfulness/relevance evaluation | RAGAS; ARES; RAGChecker |
| Out-of-scope test set | RGB negative rejection; RAGTruth |
| Chunk/top-k tuning | UNDIP thesis |
