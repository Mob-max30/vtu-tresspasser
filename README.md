# VTU Result Intelligence Agent

An AI browser agent that uses Webcmd to learn the VTU results workflow
once, reuse that learned workflow, validate extracted academic data,
and turn it into performance intelligence — built across **two data
tracks** so the ~360-student analytics story and the live Webcmd demo
each rest on a legitimate footing.

## Why two tracks

`results.vtu.ac.in` disallows automated access in its `robots.txt` and
gates every lookup behind a captcha. That's fine for a student checking
their *own* result with a human solving the captcha — it is not fine
for programmatically pulling hundreds of other students' academic
records. So:

- **Track A (bulk, ~360 students)** — `backend/ingestion/exam_cell_import.py`
  reads an **already-authorized** exam-cell/ERP CSV export. Colleges
  already receive this data officially; this is the legitimate door to
  full-scale analytics, not the public single-lookup portal.
- **Track B (live Webcmd demo)** — `backend/agent/webcmd_adapter.py`
  drives a real browser against VTU's site for a **small, explicitly
  consenting** batch (e.g. teammates checking their own results,
  solving their own captchas). This is what actually demonstrates
  Webcmd's explore→learn→reuse loop live.
  **`MAX_DEMO_BATCH_SIZE = 10`** and per-USN `consent=True` are enforced
  in code (`DemoBatch`), not just policy — see that file before
  changing either.

Both tracks converge on the same `StudentResult` schema
(`backend/database/models.py`) and the same validate → save → analytics
pipeline, so the dashboard doesn't care which track a result came from.

## Architecture

```
                    ┌─────────────────────┐
                    │   React Frontend      │
                    │  Setup / Agent /       │
                    │  Results / Analytics   │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼─────────────┐
                    │   FastAPI Backend       │
                    └───┬──────────┬─────┬────┘
                        │          │     │
           ┌────────────▼──┐  ┌────▼───┐ │
           │ USN CLASSIFIER │  │ AGENT  │ │
           │ (deterministic)│  │ ORCH.  │ │
           └────────┬───────┘  └───┬────┘ │
                     │      ┌───────┴──────┐│
                     │      │              ││
              ┌──────▼──┐ ┌─▼───────────┐  ││
              │ TRACK A │ │  TRACK B    │  ││
              │ CSV     │ │  WEBCMD     │  ││
              │ import  │ │  (capped,   │  ││
              │ (~360)  │ │  consented) │  ││
              └────┬────┘ └──────┬──────┘  ││
                   │             │         ││
                   └──────┬──────┘         ││
                          │                ││
                 ┌────────▼────────┐       ││
                 │ VALIDATION       │       ││
                 └────────┬─────────┘       │▼
                          │           ┌─────▼──────┐
                 ┌────────▼────────┐  │ ANALYTICS   │
                 │ SQLite DATABASE │◄─┤ ENGINE      │
                 └─────────────────┘  └─────────────┘
```

## Running it

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python -m pytest          # 19 tests, all deterministic logic
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev                # http://localhost:5173
```

**Track A smoke test (no server needed):**
```bash
cd backend
python3 -c "
from agent.orchestrator import process_bulk_import
from pathlib import Path
from database.database import init_db
import json

init_db()
curriculum = json.load(open('curriculum/config.json'))
report = process_bulk_import(Path('../data/exam_cell_results_sample.csv'), curriculum)
print(report)
"
```

## What's implemented vs. stubbed

| Component | Status |
|---|---|
| USN classifier + tests | ✅ Implemented, tested |
| Validator + tests | ✅ Implemented, tested |
| Analytics engine + tests | ✅ Implemented, tested (SGPA/CGPA math verified against known values) |
| SQLite models/persistence | ✅ Implemented |
| Track A CSV import | ✅ Implemented, end-to-end tested |
| Track B webcmd adapter | ✅ Structure + guardrails implemented and tested; `execute_workflow`'s actual `webcmd vtu results` call depends on the adapter file at `~/.webcmd/clis/vtu/results.js` being authored against the real page (Phase 2 — needs a live browser session, can't be done in a sandboxed container) |
| Orchestrator | ✅ Implemented, wires both tracks into validate/save |
| Recovery (retry/re-discover) | ✅ Implemented |
| FastAPI routes | ✅ Implemented |
| React frontend | ✅ Skeleton with working API calls for Setup (Track A), Agent status, Results, Analytics; Track B's consent-list form is a documented stub |
| CAPTCHA human-in-the-loop | ✅ Wired via `CaptchaPending` exception → orchestrator → route → (frontend stub) |

## Curriculum config

Fill in real subject codes/credits in `backend/curriculum/config.json`
before running against real data — the placeholders will fail
validation against real VTU subject codes on purpose (fail loud, not
silent, per the project's non-negotiable principles).

## Remaining before a live demo

1. On a machine with a real display (not this sandbox — headless
   containers can't show a captcha to a human), run
   `webcmd browser init vtu/results`, explore the live VTU page with
   `webcmd browser run`, author the adapter's selectors, and
   `webcmd browser verify vtu/results` until it passes.
2. Fill in real curriculum subjects/credits.
3. Get the exam-cell CSV export for Track A's full dataset.
4. Build Track B's consent-list UI in `SetupPage.jsx` (form → POST
   `/api/agent/run-live-demo`) and the captcha-prompt UI in
   `AgentRunningPage.jsx` (render `captcha_pending` entries from the
   response with a "solve it, then Continue" button).
