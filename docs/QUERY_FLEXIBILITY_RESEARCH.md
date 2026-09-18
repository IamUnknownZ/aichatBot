# Query Flexibility & Conversational Retrieval Research

Updated: 19 September 2026

## Problem observed in the tutor

Real students do not always type full, clean questions. Examples include:
- short social turns: "ไง", "สวัสดีครับ"
- topic-only queries: "บับเบิลซอร์ท"
- transliterations: "ควิกซอร์ท"
- misspellings: "บับเบิ้ลซอท"
- context-dependent follow-ups: "แล้วตัวนี้ล่ะ", "ต่างกันยังไง"

A RAG system that sends these raw strings directly to retrieval can reject valid intent even when the source document contains the answer.

## Research basis

### 1. Conversational Query Rewriting

Wu et al. (2022), CONQRR, frames conversational retrieval as a problem in which the current question must be interpreted using dialogue context and rewritten into a standalone query suitable for an existing retriever.

Qian & Dou (2022), Explicit Query Rewriting for Conversational Dense Retrieval, similarly reports that context-dependent queries can contain omitted or referring expressions and shows gains from query rewriting/context modelling.

Ma et al. (2023), Query Rewriting in Retrieval-Augmented Large Language Models, proposes Rewrite-Retrieve-Read rather than retrieving directly from raw user input.

Design consequence for this project:
- never assume the student's raw message is already an optimal retrieval query
- expand topic-only utterances into standalone retrieval queries
- add previous-turn context only when the message behaves like a genuine follow-up
- preserve the original user message for the final answer

### 2. Query Expansion

Wang et al. (2023), Query2doc, shows that query expansion can improve sparse and dense retrieval. The paper reports improvements on ad-hoc IR benchmarks by enriching the original query with information that guides retrieval.

Design consequence:
- known course terms can be expanded cheaply without another model request
- example: "บับเบิลซอร์ท" -> "Bubble Sort ... คืออะไร หลักการทำงาน ขั้นตอน ตัวอย่าง"
- this is deliberately deterministic for common curriculum vocabulary to keep latency low

### 3. Robustness to misspellings

Tasawong et al. (2023), Typo-Robust Representation Learning for Dense Retrieval, and Sidiropoulos & Kanoulas (2022/2024) show that retrieval quality can degrade substantially with misspelled/noisy queries.

Design consequence:
- normalize Unicode and punctuation before matching
- maintain Thai/English aliases and transliteration variants for curriculum terms
- use lightweight fuzzy matching for short course terms
- evaluate with noisy test queries, not only clean textbook questions

### 4. Clarification for genuinely ambiguous requests

Cao et al. (2025), ICR: Iterative Clarification and Rewriting for Conversational Search, alternates clarification questions with rewritten queries and reports continuing retrieval gains through the clarification-rewriting process.

Mass et al. (2022), Conversational Search with Mixed-Initiative, explicitly studies under-specified or ambiguous user queries where the system asks a clarification question before continuing retrieval.

Qian & Dou (2022) report that making only necessary query modifications can improve both query-rewriting quality and efficiency. This supports resolving common ambiguity deterministically before considering a more expensive model rewrite.

Design consequence:
- deterministic aliases resolve obvious course terms first
- genuinely under-specified whole utterances trigger a clarification question
- context-resolvable intents such as "code", "trace", "example", or "complexity" reuse the previous explicit algorithm topic instead of asking again
- intents requiring missing information, such as "compare", still ask for the missing target(s)
- clarification routing does not call Gemini and does not perform document retrieval
- after clarification, normal query expansion/retrieval handles the user's more specific reply

### 5. Educational-chatbot interaction design

Kuhail et al. (2023) reviewed 36 educational-chatbot studies and found multiple interaction styles including intent-based and user-driven approaches, while also identifying usability and insufficient datasets as recurring challenges.

Debets et al. (2025) reviewed 71 educational-chatbot papers and highlights that educational chatbot design/evaluation often lacks a sufficiently justified pedagogical basis.

Design consequence:
- accept natural student language instead of forcing menu-only interaction
- give students control of the conversation
- keep the interface content-first
- measure usability and successful intent recognition rather than claiming the interface is effective because it looks polished

## Implemented architecture

Current query lexicon: **644 unique normalized aliases** across four groups:
- topics: algorithm names, Thai transliterations, common misspellings and descriptive names
- concepts: Big-O, memory/space, stability, in-place, comparison sorting, divide-and-conquer, recursion and tracing
- actions: explain, compare, example, trace, code, summarize and why/reason
- social: greetings, thanks, farewell, help and tutor identity

Current clarification dictionary: **534 ambiguity aliases** across situations such as generic sort/algorithm requests, compare, code, trace, complexity, stability, memory, examples, summaries, visualization, steps, pros/cons, use cases, ordering direction, pivot, recursion, data input, swap and partition.

User message
→ Unicode/punctuation normalization
→ exact per-kind hash lookup
→ social/conversation router
→ course alias + transliteration + typo handling
→ deterministic query expansion
→ contextual rewrite only for genuine follow-up
→ hybrid retrieval (local fallback or PostgreSQL + pgvector)
→ relevance gate
→ grounded answer

This means PostgreSQL is not responsible for handling "ไง" or recognizing "บับเบิลซอร์ท". PostgreSQL/pgvector improves semantic retrieval, persistence and scale after the query-understanding layer has prepared the query.

### Streamlit performance optimization

The lexicon is designed so adding hundreds of variants does not create another network request.

Implementation details:
- all aliases are normalized once at Python-module import
- exact normalized/compact aliases use dictionary/hash lookup
- indexes are separated by kind (topics, concepts, actions, social)
- substring search only scans the requested kind
- fuzzy matching is used only after exact/substring matching fails
- fuzzy candidates are bucketed by string length instead of scanning the whole lexicon
- normalized queries and match results use bounded LRU caches
- no additional Gemini request is used for normal alias correction/query expansion
- social messages bypass document retrieval entirely
- ambiguous whole-message clarification uses a separate exact/compact hash index
- clarification fuzzy matching is length-bucketed and cached
- clarification responses bypass both retrieval and Gemini generation
- contextual clarification can reuse a previous explicit algorithm topic without another clarification turn

Development benchmark on the current machine (19 Sep 2026):
- 644 unique normalized aliases
- validation of all configured aliases: 0 canonical mismatches
- representative first-seen exact/fuzzy query routing sample: about 0.395 ms/query average
- clarification dictionary: 534 ambiguity aliases
- representative first-seen clarification sample: about 0.46 ms/query average
- an earlier broader noisy/fuzzy sample before per-kind indexing averaged about 1.8 ms/query

These timings are engineering measurements, not research outcomes. Chapter 4 should measure the deployed Streamlit environment separately (P50/P95) before reporting final performance claims.

## Evaluation set additions

The Chapter 4 test set should include at least:
- 20 topic-only queries
- 20 Thai transliteration variants
- 20 misspelled/noisy queries
- 15 conversational follow-ups
- 10 social turns/greetings
- 20 out-of-domain short/noisy queries

Report:
- intent acceptance rate
- retrieval Hit@K after normalization
- false rejection rate
- out-of-domain rejection rate
- clarification trigger precision
- unnecessary-clarification rate
- clarification resolution rate
- average clarification turns before retrieval
- clarification-router P50/P95 latency
- latency added by query understanding
- comparison: raw query vs normalized/expanded query

## References

- Wu, Z. et al. (2022). CONQRR: Conversational Query Rewriting for Retrieval with Reinforcement Learning. EMNLP 2022. https://aclanthology.org/2022.emnlp-main.679/
- Qian, H., & Dou, Z. (2022). Explicit Query Rewriting for Conversational Dense Retrieval. EMNLP 2022. https://aclanthology.org/2022.emnlp-main.311/
- Ma, X. et al. (2023). Query Rewriting in Retrieval-Augmented Large Language Models. EMNLP 2023.
- Wang, L., Yang, N., & Wei, F. (2023). Query2doc: Query Expansion with Large Language Models. EMNLP 2023. https://aclanthology.org/2023.emnlp-main.585/
- Tasawong, P. et al. (2023). Typo-Robust Representation Learning for Dense Retrieval. ACL 2023. https://aclanthology.org/2023.acl-short.95/
- Sidiropoulos, G., & Kanoulas, E. (2022). Analysing the Robustness of Dual Encoders for Dense Retrieval Against Misspellings.
- Cao, Z., Li, P., & Zhu, Q. (2025). ICR: Iterative Clarification and Rewriting for Conversational Search. EMNLP 2025. https://aclanthology.org/2025.emnlp-main.496/
- Mass, Y., Cohen, D., Yehudai, A., & Konopnicki, D. (2022). Conversational Search with Mixed-Initiative - Asking Good Clarification Questions backed-up by Passage Retrieval. DialDoc 2022. https://aclanthology.org/2022.dialdoc-1.7/
- Kuhail, M. A. et al. (2023). Interacting with educational chatbots: A systematic review. Education and Information Technologies, 28, 973–1018.
- Debets, T. et al. (2025). Chatbots in education: A systematic review of objectives, underlying technology and theory, evaluation criteria, and impacts. Computers & Education, 234, 105323.
