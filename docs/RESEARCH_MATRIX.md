# Research Matrix — AI Sorting Tutor with RAG

อัปเดต: 18 กันยายน 2026

เอกสารนี้แยก 2 กลุ่ม:
1. งานวิจัย/วิทยานิพนธ์ที่ repository แสดงโครงสร้าง Bab/Chapter 1-5 ชัดเจน
2. งานสนับสนุนที่ตรงกับฟีเจอร์เฉพาะ เช่น latency, vector database, multimodal PDF, hallucination

> หมายเหตุเรื่องสิทธิ์: "มี 5 บท" ไม่ได้แปลว่าเปิดดาวน์โหลดทุกบท บาง repository เปิดเฉพาะบท 1/5 หรือ abstract แต่ metadata ยืนยันว่ามีบท 1-5

---

## A. งาน 5 บทที่ใช้เป็นต้นแบบโครงงานได้โดยตรง

| # | งาน | ปี / ระดับ | หลักฐานโครง 5 บท | สิ่งที่เอามาใช้กับโปรเจกต์เรา | บทที่เหมาะอ้าง |
|---|---|---|---|---|---|
| 1 | Mohammad Labib Husain — *Pengembangan Chatbot Informasi Administrasi Akademik FPMIPA UPI Berbasis RAG* | 2025, S1 UPI | Repository แสดง Chapter1-5 แยกไฟล์ | hierarchical segmentation, layered retrieval, conversational memory, out-of-context rejection, RAGAS | 2, 3, 4, 5 |
| 2 | Muhamad Fadhly Rafiansyah et al. — *Pengembangan AI Tutor Berbasis LLM dengan RAG pada Pembelajaran AI* | 2026, S1 UPI | Repository แสดง Chapter1-5 | AI tutor แบบวิชาเฉพาะ, local curriculum/module, strict prompting, usability | 1, 2, 3, 4 |
| 3 | Muhammad Daffa Aulia Jowis & Muhammad Fadli Prathama — *Implementasi RAG pada Chatbot Berbasis Web untuk Layanan Informasi Akademik di ITPLN* | 2026, thesis ITPLN | Repository แสดง BAB 1-5 | controlled knowledge, metadata, relevance scoring, response restriction เมื่อข้อมูลไม่ควรตอบ | 2, 3, 4 |
| 4 | Vidi Septri Argalus — *Rancang Bangun Chatbot Menggunakan LLM sebagai Sarana Informasi Skripsi* | 2025, D4 PNJ | Bab 1/5 + file Bab 2-4 | RAG web architecture, Pinecone, FastAPI/React, Black-box, UAT, SUS/NPS | 3, 4 |
| 5 | Muhamad Atsil Rifqi Riyansyah — *Pengembangan Model Chatbot dengan RAG dan Fine-Tuning Berbasis LLM* | 2025, D4 PNJ | Bab 1/5 + file Bab 2-4 | เปรียบเทียบ RAG กับ fine-tuning, FAISS, BERTScore/UniEval/Human Evaluation | 2, 4, 5 |
| 6 | Ghania Shafiqa Raisa — *Pemanfaatan LLM untuk Chatbot Layanan Akademik: RAG, Fine-Tuning, RAFT* | 2025, D4 PNJ | Bab 1/5 + file Bab 2-4 | เปรียบเทียบ RAG/FT/RAFT, cost/performance trade-off, web deployment | 2, 4, 5 |
| 7 | Andra Rizki Pratama — *Rancang Bangun Web Pembuatan Pasangan Pertanyaan-Jawaban Otomatis dengan RAG* | 2025, D4 PNJ | Bab 1/5 + file Bab 2-4 | PostgreSQL, vector store, retrieval optimization, LLM-as-a-Judge, human evaluation | 3, 4 |
| 8 | Febriansyah & Abdurrasyid — *Otomasi Respons Insiden ... LLM Berbasis RAG* | 2026, thesis ITPLN | Repository แสดง BAB 1-5 | RAGAS, prompt engineering, แยก accuracy ของ task ออกจาก factual correctness | 2, 4, 5 |
| 9 | Muhammad Luthfi Pradana — *Perancangan dan Implementasi Fitur Chatbot ... Berbasis Website* | 2025, D4 PNJ | Bab 1/5 + file Bab 2-4 | SDLC, RAG chatbot, accuracy/precision/recall/F1, SUS/UAT | 3, 4 |
| 10 | Syifa Frizaldy & Agus Mulyanto — *Perancangan Sistem Konseling Mahasiswa Berbasis Chatbot Menggunakan Multi-Agent System* | 2026, thesis ITPLN | Repository แสดง BAB 1-5 | intent routing, multi-agent + RAG, overlap ของ intent, routing evaluation | 3, 4, 5 |
| 11 | Hapid Ramdani — *Perancangan Chatbot Penelitian Dosen Menggunakan Metode RAG* | 2026, Skripsi UIN Suska | มี BAB gabungan และไฟล์ BAB IV-V | custom academic knowledge base, citation/BibTeX, black-box testing | 2, 3, 4 |
| 12 | Lisna Agustin — *Rancang Bangun Chatbot Nutri-Grade dan Nutrisi Berbasis RAG* | 2025, D4 PNJ | repository มีตัวเล่ม/Isi Skripsi | Streamlit + ChromaDB, RAGAS, expert evaluation, SUS/NPS | 3, 4 |

### Repository URLs

1. https://repository.upi.edu/138355/
2. https://repository.upi.edu/151251/
3. https://repository.itpln.ac.id/id/eprint/7549/
4. https://repository.pnj.ac.id/id/eprint/27279/
5. https://repository.pnj.ac.id/id/eprint/27327/
6. https://repository.pnj.ac.id/id/eprint/28725/
7. https://repository.pnj.ac.id/id/eprint/27025/
8. https://repository.itpln.ac.id/id/eprint/6995/
9. https://repository.pnj.ac.id/id/eprint/30640/
10. https://repository.itpln.ac.id/id/eprint/7828/
11. https://repository.uin-suska.ac.id/92690/
12. https://repository.pnj.ac.id/id/eprint/27874/

---

## B. งานสนับสนุนที่ตรงกับ feature ของเราอย่างมาก

| งาน | ประเด็นสำคัญ | ใช้ตัดสินใจอะไร |
|---|---|---|
| Muhammad Farhan Fahrezy, IPB (2026) | hybrid vector+BM25, RRF, cross-encoder rerank, section-aware chunking, RAGAS; หลัง optimize response time 29.08s → 3.90s | เหตุผลของ hybrid retrieval + performance optimization |
| Faliqul Ishbah, UMM (2026) | Supabase vector DB + Gemini, strict fallback เมื่อข้อมูลไม่มี; 49 scenarios | anti-hallucination / safe fallback |
| Farel Abid Yasser Prayanto, UPN (2025) | PDF preprocessing, RecursiveCharacterTextSplitter, hybrid BM25+semantic, Streamlit, multidimensional evaluation | ใกล้ stack ปัจจุบันที่สุด |
| Ahlis Dinal Bahtiar, UNDIP (2026) | 72 configurations; chunk size/overlap/top-k; similarity vs MMR; response-time evaluation | ทำ experiment tune RAG ในบท 4 |
| Yana Dayinta Nesthi, UGM (2025) | backend ประมวลผล text, image, PDF; vector knowledge base; cloud workflow | multimodal ingestion / image future |
| Morin Adepatrick Damanik, ITS (2026) | 5 core PDFs + JSON structured data; expert-validated QA; RAGAS | multi-source knowledge + evaluation |
| Muhammad Mirza Farisy, ITS (2026) | ศึกษาผลของ vector database ต่อ scalability/response speed | เหตุผลเชิงวิจัยสำหรับ vector DB/performance |
| Richa Kakati, AIT Thailand (2025) | เปรียบเทียบ RAG กับ document-augmented tutor ใน programming education โดยเน้น hallucination | งานด้าน educational tutor ที่ใกล้ domain เรา |
| Jacopo Righetto, University of Padua (2024/25) | technical PDF manuals, semantic chunking, vector retrieval, Gemini, persistent memory, latency | architecture PDF QA แบบ production |
| Sabatino Larosa, University of Genoa (2026) | RAG chatbot สำหรับข้อมูลรายวิชา/มหาวิทยาลัยและลด hallucination | academic chatbot + controlled sources |

Repository URLs:
- https://repository.ipb.ac.id/handle/123456789/178425
- https://eprints.umm.ac.id/id/eprint/33379/
- https://eprints.upnyk.ac.id/45305/
- https://eprints2.undip.ac.id/id/eprint/58712/
- https://etd.repository.ugm.ac.id/penelitian/detail/257206
- https://repository.its.ac.id/142045/
- https://repository.its.ac.id/136327/
- https://mailserv02.ait.ac.th/ait-thesis/detail.php?q=B23628
- https://thesis.unipd.it/handle/20.500.12608/95455
- https://unire.unige.it/handle/123456789/15559

---

## C. งานวิจัยหลัก (paper) ที่ควรอ้างในบท 2

1. Lewis, P., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks.* NeurIPS.
2. Liu, N. F., et al. (2024). *Lost in the Middle: How Language Models Use Long Contexts.* Transactions of the ACL, 12, 157-173.
3. Yan, S.-Q., Gu, J.-C., Zhu, Y., & Ling, Z.-H. (2024). *Corrective Retrieval Augmented Generation.*
4. Es, S., James, J., Espinosa-Anke, L., & Schockaert, S. (2023). *RAGAS: Automated Evaluation of Retrieval Augmented Generation.*
5. Saad-Falcon, J., et al. (2023). *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems.*
6. Niu, C., et al. (2024). *RAGTruth: A Hallucination Corpus for Developing Trustworthy Retrieval-Augmented Language Models.*
7. Ru, D., et al. (2024). *RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation.*
8. Yu, S., et al. (2024). *VisRAG: Vision-based Retrieval-augmented Generation on Multi-modality Documents.*
9. Asai, A., et al. (2023). *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.*
10. Khattab, O., & Zaharia, M. (2020). *ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT.*

---

## D. Feature → งานอ้างอิงที่แนะนำ

| Feature ของเรา | ใช้งานวิจัยไหนเป็นหลัก |
|---|---|
| ไม่ส่ง PDF ทั้งเล่มทุกคำถาม | Lewis; Lost in the Middle |
| Hybrid vector + lexical retrieval | Fahrezy; Prayanto; pgvector literature |
| Relevance threshold + abstain | CRAG; Ishbah; Husain; ITPLN academic chatbot |
| ไม่ hallucinate เมื่อข้อมูลไม่มี | RAGTruth; CRAG; RAGAS; AIT Kakati |
| อธิบายตรงประเด็นและ grounded | Husain; AI Tutor UPI; RAGAS |
| ไม่บังคับโค้ดทุกคำตอบ | เป็น interaction/prompt design ของระบบเรา ต้องทดสอบด้วย no-code test set |
| Page citation | grounded retrieval metadata; Husain/Damanik เป็นงานเทียบเคียง |
| PostgreSQL + vector | Pratama (PostgreSQL system); Farisy (vector DB performance); pgvector docs |
| Streamlit performance | Prayanto; Agustin; Veijanen + Streamlit caching/streaming docs |
| PDF image / multimodal future | Nesthi; VisRAG; Gemini multimodal embeddings |
| Chunk size / overlap / top-k experiment | Bahtiar |
| RAGAS / faithfulness | Husain; Fahrezy; RAGAS paper |
| User evaluation | SUS/UAT จาก PNJ theses; QUEST จาก AI Tutor UPI |
| Latency / TTFT | Fahrezy; Bahtiar; Righetto + logs ของระบบเรา |

---

## E. โครงอ้างในรายงาน 5 บทของโปรเจกต์เรา

### บทที่ 1
- ปัญหา: chatbot แบบ LLM ล้วนมีความเสี่ยง hallucination และ long context ไม่ใช่คำตอบของทุกกรณี
- งานใกล้เคียง: AI Tutor UPI, AIT tutor, academic chatbots

### บทที่ 2
- LLM, embedding, vector database
- RAG / hybrid retrieval
- chunking
- hallucination / abstention
- RAGAS / evaluation
- multimodal document retrieval

### บทที่ 3
- Input PDF → preprocessing → page-aware chunk → embedding → PostgreSQL/pgvector
- hybrid retrieval → relevance gate → prompt grounding → streaming
- data dictionary
- test-set design
- image extraction/multimodal extension

### บทที่ 4
- เทียบ baseline Full-PDF context กับ RAG
- vector-only vs hybrid
- threshold on/off
- chunk/top-k experiments
- Hit@K, faithfulness, answer relevance, citation accuracy
- out-of-scope rejection
- latency P50/P95 และ TTFT
- usability

### บทที่ 5
- สรุปผลและข้อจำกัด
- RAG ลดความเสี่ยง hallucination แต่ไม่ควรอ้างว่าเป็น zero-hallucination
- threshold มี trade-off ระหว่าง false-answer กับ false-rejection
- future work: multimodal PDF, reranker, query decomposition, larger user study
