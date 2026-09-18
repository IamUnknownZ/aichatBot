# UI Redesign Plan — Sorting AI Tutor

Updated: 19 September 2026

## Objective

Redesign the Streamlit tutor into a clean learning workspace rather than a collection of Streamlit cards. The answer should be the visual focus; controls, citations and technical state should be progressive disclosure.

## References

Provided in readthis.md:
- Figma Community — modern chatbot chat window
- Figma Community — ChatGPT redesign
- Figma Community — typing animation in chat
- Figma Community — SleekSphere unified workspace concept
- nxr-dine/AI-Chatbot — responsive chat flow, thinking indicator, auto-growing input and image-upload interaction patterns

The individual Figma Community files are not programmatically inspectable from this environment because Figma blocks direct crawling. The redesign therefore uses their stated interaction themes plus verified modern chat/workspace patterns rather than claiming pixel-level reproduction.

## Design principles

1. Content first
   - Assistant answer uses the largest clean reading area.
   - User messages are visually compact.
   - No technical implementation labels in the learning surface.

2. Workspace, not dashboard
   - Compact course header instead of a large decorative hero.
   - Sidebar is navigation/history, not a second dashboard.
   - The composer feels attached to the conversation.

3. Progressive disclosure
   - Citations collapsed under each grounded answer.
   - Images collapsed unless useful.
   - RAG model/threshold/lexicon data only in Advanced.

4. Visible system state
   - Lightweight "searching / thinking" animation while retrieval/generation is waiting.
   - Remove the indicator at first streamed token.
   - Respect prefers-reduced-motion.

5. Responsive hierarchy
   - Desktop: centered readable column, compact utility rail.
   - Mobile/tablet: no wide hero, reduced padding, full-width composer.
   - Avoid fixed heights and heavy visual effects.

6. Performance
   - CSS-only mascot/micro-animation; no remote assets.
   - No extra API call for UI state.
   - Keep st.cache_resource for RAG resources.
   - Force cache version when service interface changes to avoid stale cached objects.
   - Avoid rendering custom iframe controls for historical messages.

## Planned work

### P0 — Production stability
- Guard service.lexicon_size with a safe fallback.
- Version the cached service factory so old cached service objects cannot crash a new UI.

### P1 — Visual redesign
- Replace large hero card with compact top workspace header.
- Integrate mascot into header instead of a separate decorative box.
- Make assistant answers mostly borderless/open reading blocks.
- Keep user messages as compact accent bubbles.
- Redesign status into one small trust line.
- Refine quick prompts and empty state.
- Restyle source expander as a secondary evidence panel.
- Polish sidebar hierarchy.

### P2 — Interaction polish
- Add CSS thinking dots during retrieval/first-token wait.
- Clear thinking state on first streamed token.
- Improve composer visual treatment.
- Keep citations out of conversational/social replies.

### Reference-repo optimization decisions

Useful patterns adopted from nxr-dine/AI-Chatbot:
- explicit thinking/loading feedback before a response
- responsive conversation layout
- lightweight interaction feedback around the composer

Patterns intentionally not copied:
- sending an ever-growing full chatHistory to the generation API on every turn
- client-side API-key handling
- artificial response delay before calling the model

Our implementation keeps bounded conversation context, server-side secrets, RAG retrieval and immediate streaming.

### P3 — QA
- compileall
- unittest query lexicon
- Streamlit AppTest
- service routing smoke tests
- git diff --check
- secret scan
- review mobile CSS and reduced-motion behavior

## Acceptance criteria

- App no longer crashes if a cached/older RAGService lacks lexicon_size.
- Streamlit AppTest has zero exceptions.
- "ไง", "สวัสดีครับ", "บับเบิลซอร์ท", typo queries and out-of-domain checks still behave correctly.
- Citation UI remains collapsed and readable.
- No new network request or LLM call is added by the UI.
- Query/UI changes do not modify secret files.
