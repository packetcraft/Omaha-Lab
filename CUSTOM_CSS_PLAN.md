# Custom CSS Theming Plan

Chainlit's default UI is being kept (see `DECISIONS.md` for why a full custom
frontend rewrite was ruled out — the sidebar settings widget, chat-profile Lab
Mode picker, pipeline diagram, and header links are all Chainlit-specific
plumbing that a rewrite would have to reproduce from scratch for polish alone).
Instead, polish happens incrementally through `public/theme.css`
(`custom_css` in `.chainlit/config.toml`) plus small `custom_js` snippets
where CSS alone can't reach — bundled together in `public/custom.js` since
Chainlit only loads one `custom_js` file.

Work through the items below one at a time — each is scoped to be a single
sitting. Check off `Status` as they land, and note the commit hash.

**Gotcha to remember:** `custom_css` loads *before* Chainlit's own compiled
stylesheet, so any CSS-variable override needs `html:root` / `html.dark`
(specificity 0,1,1) rather than plain `:root` / `.dark` (0,1,0), or the stock
rule wins the cascade and silently no-ops. Verify any new variable override in
both light and dark mode via a headless-browser screenshot before calling it
done — see the `run` skill's browser-driven pattern.

---

## Done

| # | Item | Where |
|---|---|---|
| 0 | Base cyan/navy palette (light + dark), accented code blocks, colored scrollbar, focus rings, pill-styled header link | `public/theme.css`, commit `4563269` |
| 5 | Persona-coded accent color — `body[data-persona]` tagged by `public/custom.js`, 7 hues in `theme.css` | `public/custom.js`, `public/theme.css` |

---

## Backlog

### 1. Branding — logo & favicon
**Goal:** Replace Chainlit's default logo/favicon with an Omaha Lab mark.
**Approach:** Drop `public/logo_light.png`, `public/logo_dark.png`,
`public/favicon.ico` (or `.svg`) — Chainlit auto-detects these filenames in
`public/`, no config change needed.
**Effort/Risk:** Low. Needs actual artwork (or a simple generated mark) first.
**Status:** Not started.

### 2. Typography accents
**Goal:** Small-caps / letter-spacing on section labels (e.g. "Pipeline
topology", the `Ready — persona: ...` line) for a console/terminal feel.
**Approach:** Generic element/heading selectors in `theme.css`, no JS needed.
**Effort/Risk:** Low.
**Status:** Not started.

### 3. Print stylesheet
**Goal:** Clean, no-chrome transcript output so students can save/print a lab
session for an assignment.
**Approach:** `@media print` block in `theme.css` — hide sidebar/header/
composer, expand message width, force light colors.
**Effort/Risk:** Low.
**Status:** Not started.

### 4. Sidebar toggle contrast pass
**Goal:** Make the Guard/RAG/HITL switches and Active Tools checklist in the
settings sidebar read clearly at a glance (on/off state should be obvious
without reading the label).
**Approach:** Tune switch track/thumb colors in `theme.css`; likely just
needs the existing `--primary`/`--muted` tokens nudged, not new rules.
**Effort/Risk:** Low, mostly eyeballing during a live session.
**Status:** Not started.

### 6. Guard/blocked-message alert styling
**Goal:** Make a LlamaGuard/Presidio block or redaction visually unmistakable
during a live demo (red left border, warning icon) instead of blending in
with normal system messages.
**Approach:** Same `custom_js` pattern as #5 (see Done table) — detect the
blocked-message marker text/author Chainlit renders and tag it with a class,
then style that class in `theme.css`.
**Effort/Risk:** Medium — same content-matching fragility as #5; check
`guardrails/llama_guard.py` and `guardrails/presidio_guard.py` for the exact
message text/author used so the JS match is precise, not a substring that
could false-positive on normal chat.
**Status:** Not started.

### 7. Message/pipeline-diagram motion polish
**Goal:** Subtle fade-in on new messages, maybe a pulse on the pipeline
diagram when the "fired" node changes.
**Approach:** CSS transitions/animations, respecting
`prefers-reduced-motion`.
**Effort/Risk:** Higher — needs internal Tailwind/component class selectors
that aren't guaranteed stable across Chainlit versions (unlike the plain-HTML
selectors used elsewhere in this plan). Treat as lowest priority; re-evaluate
selectors after any Chainlit version bump.
**Status:** Not started.
