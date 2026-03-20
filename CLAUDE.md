# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered Qualtrics survey builder that converts natural language into Qualtrics API payloads. Flask backend + vanilla JS single-page app (no build step, no JS frameworks).

## Running the App

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
# Serves at http://localhost:5000
```

There are no tests, linter, or build commands configured.

## Architecture

**Two-file architecture:**
- `app.py` — Flask backend (all routes, LLM integration, Qualtrics API proxy)
- `templates/index.html` — Complete SPA (HTML + CSS + JS embedded in one file)

**Data flow:**
```
Browser (credentials in localStorage)
  → Flask backend (app.py)
    → Qualtrics API (survey CRUD)
    → LLM API (Anthropic Claude / OpenAI GPT-4o for question generation)
```

### Backend (app.py)

15 Flask routes, all POST, all accept/return JSON:
- **Survey/Block/Flow routes:** `/api/survey`, `/api/blocks`, `/api/blocks/create|delete|update|get`, `/api/flow`, `/api/flow/update`
- **Question routes:** `/api/question/get|update|delete`, `/api/submit`
- **AI routes:** `/api/parse` (text → Qualtrics question JSON via LLM), `/api/generate-js` (generate custom Qualtrics JS), `/api/modify-question` (AI-powered question editing)

Key helpers: `llm_complete()` (unified Anthropic/OpenAI call), `qualtrics_headers()`, `qualtrics_base()`

### Frontend (templates/index.html)

Global state variables: `surveyBlocks[]`, `rawBlocks{}`, `allQuestions{}`, `surveyFlow{}`, `currentDetailQID`, `currentDetailData`, `pendingModifiedData`

Main UI sections:
- **Sidebar** (resizable, 360px default) — block/question tree with drag-and-drop reordering and search
- **Content area** — question creator (textarea → parse → preview JSON → submit to Qualtrics)
- **Detail overlay** (modal) — three tabs: Preview (WYSIWYG + AI modify prompt), JSON editor, JavaScript editor with AI generation

### Qualtrics Question Types Supported

MC (multiple choice), TE (text entry), DB (descriptive/text block), Slider, Matrix, RO (rank order)

## Key Conventions

- All API credentials are client-side only (localStorage), never stored on server
- No session state on backend — every request includes credentials in the JSON body
- `buildUpdatePayload(q)` whitelists safe fields for question PUT requests
- `esc()` function handles HTML escaping to prevent XSS
- After any mutation (create/delete/reorder), the frontend re-fetches the full survey structure
- Drag-and-drop uses native HTML5 drag events with a `dragState` object tracking the operation
- LLM calls use temperature 0 for deterministic output

## Reference Files

- `QUALTRICS_API_REFERENCE.md` — Qualtrics API endpoint documentation
- `FUTURE_WORK.md` — Feature roadmap (Display Logic, Skip Logic, Flow Editor, etc.)
