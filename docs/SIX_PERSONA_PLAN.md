# Six-persona chat workspace

## Approved contract

Replace the Sorty-facing identity with six AI tutors, ordered Nui, Saimai,
Bam, Bas, Kaka, SabaiTae. Use the Stitch archive as the visual reference:
navy-charcoal surfaces, cyan accents, people sidebar, right-aligned user
bubbles, bottom composer, compact evidence previews. Initial avatars are
letter placeholders, replaceable later without changing persona IDs.

All tutors share the same grounding, curriculum and language rules.
Styles: patient beginner teacher, concise tutor, questioning coach,
code companion, complexity analyst, exam revision coach respectively.
These are AI roles, not real-person impersonations.

Display names must not identify users. Browser identity is a high-entropy
bearer capability: never expose it in URLs or merge by display name.
Anonymous history belongs to this browser; clearing browser storage loses
access. Not cross-device authentication. History segregated by persona.
Do not migrate name-based legacy history automatically or erase it.

## Units and completion gates

1. Persona registry and guarded prompt integration; deterministic/direct
   routes must identify the selected tutor without shared-service mutation.
2. Anonymous browser identity, separate database history schema, explicit
   save outcomes, ordered bounded history loading, ownership-checked delete.
3. Stitch-style Streamlit workspace with six clickable tutors and native
   widgets; avoid dead decorative controls, retain Thai/English and previews.
4. Runtime/AppTest/browser verification: switch tutors, new conversation,
   refresh/reopen, name changes, failed saves, missing DB, desktop/mobile.
   Live DB/model and browser checks must remain NOT_RUN unless executed.

No pushing, destructive schema migration or exposing secrets. Preserve
pre-existing staged changes and ready-to-push snapshot. Additive tables
are acceptable; live schema application must be tracked explicitly.

## Working constraints

Use failing regression tests before implementation. One writer lock:
`/tmp/aichat-six-personas-writer.lock`. Main session owns production files.
Separate fixed-candidate review before declaring complete.
Scheduled automation_update is unavailable; no heartbeat was created.
Current concurrency: at most two Luna workers, per the latest user instruction.
They own browser identity and app/history integration respectively; main owns
the remaining scopes. No further agents may be spawned while both are open.

## Status

currentUnit: 4
nextPass: REVIEW
candidate: six-persona-workspace at 9bfe2eabfa358ca62366c71656be0cb2b41c90b0 (preliminary; newer worktree changes are not included)
verification: full Python suite PASS (110); targeted suite PASS (42); Node identity PASS; Chrome desktop/mobile DOM PASS; PostgreSQL rollback integration/RLS PASS; live Gemini Thai/English PASS
blockers: automation_update unavailable; full browser reopen/history UI lifecycle not yet exercised
nextAction: fixed-candidate review and scoped checkpoint; see SIX_PERSONA_VERIFICATION.md for remaining acceptance checks

Database schema/backend implemented separately by Peirce; SQLite transaction
fixtures passed, live PostgreSQL rollback integration passed without retaining
schema changes. Main session integrated frontend/backend. Chrome later connected
and desktop/mobile DOM checks were executed successfully.
UI preview at port 8502 has API and DB credentials disabled deliberately.
