# EventFlow — AI-Powered Hackathon Orchestration Platform

EventFlow is an operating system for running a hackathon. One organizer can run an event for hundreds of participants, because the AI does the heavy lifting — but a **human approves every important decision**.

It automates the parts of running a hackathon that don't scale by hand: ingesting messy registrations, forming skill-balanced teams, matching mentors, collecting judge scores, catching scoring anomalies, ranking teams, and issuing certificates — across four roles (Organizer, Participant, Mentor, Judge).

---

## Why it exists

Most hackathons are run on spreadsheets and group chats. Forming balanced teams by hand is slow and biased, mentor matching is ad-hoc, and scoring has no safeguard against a single rogue or biased judge deciding who wins. EventFlow replaces that manual grind with three real engines and a human-in-the-loop approval layer.

The design thesis: **use AI sparingly.** The AI writes language (rationales, emails, briefs); deterministic algorithms and statistics make the decisions that matter (who's on which team, what a team scores).

---

## Key features

- **AI team formation** — a deterministic, constraint-aware engine that forms skill-balanced teams, enforces institutional diversity as a hard rule, and balances experience levels. Reproducible by design.
- **Statistical anomaly detection** — flags judge scores that deviate too far from the panel and *holds* affected teams off the leaderboard until a human reviews them.
- **Human-in-the-loop approval gates** — every AI-driven action (team formation, mentor intros, anomaly resolution, publishing results) becomes an approval request with a state machine and audit trail. The AI proposes; the organizer disposes.
- **Role-based dashboards** — separate, scoped experiences for organizers, participants, mentors, and judges.
- **AI evaluation briefs** — for each submission, a generated briefing (problem, tech-stack analysis, risks, scalability) that gives judges context fast without scoring for them.
- **Certificates + AI event summary** — one-click certificate generation and an AI-written executive summary of the whole event.

---

## Architecture

```
Frontend — React 19 + Vite + Tailwind + React Router
  Role-based dashboards · JWT auth · single API client
        |  REST / JSON (JWT on every request)
Backend — FastAPI (Python)
  Thin route handlers  ->  Repository layer  ->  SQLAlchemy ORM
  JWT + bcrypt auth · Pydantic validation · CORS
        |
   +----------------+------------------+
   |                |                  |
 team_formation   scoring_engine     ai_engine
 (deterministic   (anomaly detect    (Gemini: language
  greedy+         + consolidation)    tasks only)
  backtrack)
   |                |                  |
   +----------------+------------------+
                    |
        SQLite (WAL mode) via SQLAlchemy
```

The three engines are pure Python with no web or database dependencies, so they can be unit-tested in isolation. Route handlers never touch the ORM directly — they delegate to repository classes (the **repository pattern**), which keeps them thin and testable.

### The three engines

**`team_formation.py` — skill-balanced greedy with backtracking.**
Feasibility check -> score each candidate by skill-gap fill (0.7) and experience balance (0.3) -> place on best-fit team subject to a *hard* one-per-institution constraint -> backtrack-swap to resolve deadlocks -> overflow team for anyone unplaceable (never silently dropped). Deterministic via a fixed seed so results are reproducible and defensible.

**`scoring_engine.py` — anomaly detection + consolidation.**
Adapts to panel size: absolute-gap rule for 2 judges, leave-one-out for 3, z-score for 4+. Flagged scores are excluded and the team is *held* until an organizer reviews. Final score is a weighted average over five rubric dimensions (innovation, technical depth, presentation, feasibility, impact), weights configurable per event.

**`ai_engine.py` — Gemini for language tasks only.**
Skill extraction from messy bios (JSON-mode), team rationale, mentor-intro emails, AI evaluation briefs, and the final event summary. Every prompt is grounded in real database fields; the model never invents facts or numbers.

---

## Tech stack

| Layer     | Tech |
|-----------|------|
| Frontend  | React 19, Vite, Tailwind CSS 4, React Router 7 |
| Backend   | FastAPI, SQLAlchemy 2, Pydantic v2 |
| Auth      | JWT (python-jose) + bcrypt |
| Database  | SQLite (WAL mode) — swappable to Postgres via the ORM |
| AI        | Google Gemini (google-genai SDK, gemini-2.5-flash) |

---

## Getting started

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Google Gemini API key (https://aistudio.google.com/apikey)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt

# configure your API key
cp .env.example .env          # then edit .env and paste your key
# or set it directly:
#   macOS/Linux:  export GEMINI_API_KEY="your_key"
#   Windows PS:   $env:GEMINI_API_KEY="your_key"

python seed.py                # loads demo data
uvicorn main:app --reload     # API at http://localhost:8000  (docs at /docs)
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                   # app at http://localhost:5173
```

---

## Demo accounts

After running `python seed.py`, log in with (password for all: `password123`):

| Role        | Username        |
|-------------|-----------------|
| Organizer   | `admin`         |
| Participant | `aarav`         |
| Mentor      | `mentor_sarah`  |
| Judge       | `judge_michael` |

The seed creates 1 organizer, 20 participants, 5 mentors, and 3 judges.

---

## Project structure

```
backend/
  main.py            FastAPI app + all routes (thin handlers)
  repositories.py    Repository layer (all ORM queries live here)
  models.py          SQLAlchemy models + enums + approval state machine
  schemas.py         Pydantic request/response schemas
  database.py        Engine, session factory, init/seed helpers
  team_formation.py  Deterministic team-formation engine
  scoring_engine.py  Anomaly detection + score consolidation
  ai_engine.py       Gemini language tasks
  seed.py            Demo data loader
frontend/
  src/
    pages/           One dashboard per role (organizer/participant/mentor/judge)
    components/      Shared UI (cards, charts, layout, protected routes)
    context/         Auth context
    api.js           Single API client (attaches JWT, handles 401)
```

---

## Roadmap

- Test suite for the three engines (`pytest`)
- Hardened error handling and retries around LLM calls
- Longitudinal judge-bias detection (across all teams, not just per team)
- Postgres + task queue for large, multi-event deployments
- httpOnly-cookie auth and login rate-limiting

---

*Built for the WISE TI Hackathon.*
