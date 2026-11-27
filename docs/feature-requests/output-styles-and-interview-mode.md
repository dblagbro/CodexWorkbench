# Feature request: optional output-style modes + context-rich interview mode

Backlog request from Devin (relayed by Keel), 2026-11-27. All items are OPTIONAL and DEFAULT OFF;
honor per-user / per-session / per-question settings.

## 1. Output-style presets (per-user / per-project preference)
- **ASD-STE100 (~80%)** — Simplified Technical English: limited vocabulary, short sentences, active
  voice, one instruction per sentence; ~80% adherence = clarity without a robotic tone. Best fit:
  runbooks, handoffs, procedures (STE's native domain).
- **Diagram-first** — when a relationship/flow is clearer as a diagram, emit one (e.g. mermaid)
  instead of prose.
- **HTML output** — interactive HTML (calculators, sliders, visualizations) when it helps.

## 2. Context-rich interview mode (Claude AND Codex)
When one or more questions arise (select option / skip / enter notes / "chat about this"):
- By DEFAULT include the context/background behind the question — never an abbreviated question
  without the "why".
- Render as HTML when possible, with a TERMINAL fallback (slow / text-only connections).
- In HTML, offer **ELI5 / ELI15 / ELI25** depth toggles for the background, unless a default depth
  is set for that user/session/question (e.g. via the ASD-STE100 preference).
- Keep select / skip / notes / chat affordances.

## Later
Research additional prompting/output tips in this family (deferred).
