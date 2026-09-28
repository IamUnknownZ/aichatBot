# Git History Reference

Portable ZIP เก็บ Git history ครบ 12 commits ตามลำดับเดิม แต่ rewrite object เฉพาะเพื่อ
redact credential ที่เคย hardcode ใน legacy LINE bot และ legacy model-checker โดยเปลี่ยน
เป็น environment variables:

- LINE_CHANNEL_ACCESS_TOKEN
- LINE_CHANNEL_SECRET
- GEMINI_API_KEY_INSURVERSE หรือ GEMINI_API_KEY

การ rewrite ทำให้ SHA-1 ใน portable .git เปลี่ยนตามธรรมชาติของ Git แต่ไม่ได้ตัด
milestone, parent relationship หรือ commit subject อื่นออก รายการต้นฉบับจากเครื่องเดิม:

1. f3216c9871a089cf2f7c1b8cfe380fcb9d70e3e8 — main
2. 7b7e493afaa8b5345c566d74a6785fe63231895c — main
3. c2a702f599bd08dfaa4711095615d9c9899c54f0 — feat: enforce Python code inclusion and PDF page citations
4. fe4561ec833fa33acd1f8006f75abd71f5aa42b9 — feat: upgrade tutor with grounded RAG, profiles, and seamless UI
5. b10b63d1863a6764b978c29d84c59959b4c03f02 — feat: add robust query lexicon and adaptive routing
6. d30099cad4bd80691406a605c9379cb650e98e8f — feat: redesign tutor chat as two-sided messaging UI
7. 015d0a79df39b1a06241b535fbb4ddcddb0194fa — feat: add mixed-initiative clarification and fix chat contrast
8. d1f50b593296a30b390e52826897dc2793afbcf0 — feat: harden closed-source vector RAG for deployment
9. 020ed25fb9a35d80b91ad807901fc36e3eac483f — fix: structure tutor answers and add trace visuals
10. f102c55b6e33479ceb97ebc4dbc86db8cf26338a — fix: stabilize chat reruns and lock six-topic curriculum
11. 3bd2363da6dc4187406f7591cdd85514f0ce4b0f — fix: match curriculum topics to approved source
12. 295df4d871740e76e69ab4803ebe9a0edf81c8a1 — docs: add portable project handover

ตรวจบนเครื่องใหม่:

~~~bash
git rev-list --all --count
git log --oneline --reverse --all
git show <commit>
~~~

คาดว่าจะได้ commit count = 12 และ subjects ตามลำดับข้างต้น โดย hash จะเป็น hash ของ
portable redacted history
