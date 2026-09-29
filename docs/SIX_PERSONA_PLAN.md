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
nextPass: HANDOFF
candidate: six-persona-workspace at 5a46415 (reviewed); follow-up fixes in worktree pending final checkpoint
verification: final full Python suite PASS (115); targeted UI/history/identity follow-up PASS (22); Node identity/locks PASS; compileall/diff check PASS; Chrome desktop/mobile/scroll-to-bottom PASS; PostgreSQL rollback integration/RLS PASS; live Gemini Thai/English PASS; Chrome refresh/new-tab history PASS
blockers: automation_update unavailable (no scheduled heartbeat required for this handoff)
nextAction: final checkpoint and handoff; do not start Merge Sort extraction until new sources and explicit instruction arrive

Database schema/backend implemented separately by Peirce; SQLite transaction
fixtures passed, live PostgreSQL rollback integration passed without retaining
schema changes. Main session integrated frontend/backend. Chrome later connected
and desktop/mobile DOM checks were executed successfully.
Port 8502 first ran with credentials disabled, then with server-side .env for
live UI/history QA. New tables and an isolated UI QA conversation were created;
legacy history was not deleted or migrated. See verification report.
