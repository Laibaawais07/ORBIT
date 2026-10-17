# ORBIT AI Opportunity & Growth Agent

ORBIT helps students find opportunities (hackathons, internships, research, volunteering), check how well they fit, and turn the gaps into a skill roadmap. An AI model explains the results, and **a human approves every step**. ORBIT never submits an application on anyone's behalf.

> **Status:** hackathon/demo project. Access is protected by a single shared passphrase and the data is single-user. It is not production-ready multi-user software.

## Features

- **Student analysis**   enter your academic year, skills, interest category and weekly hours; ORBIT matches opportunities, lists missing skills and drafts a roadmap.
- **MCP tools**   opportunity search, eligibility check and roadmap generation are exposed as [FastMCP](https://gofastmcp.com) tools that the workflow calls.
- **AI explanations**   Gemini (default) or OpenAI explains each match, with an honest fallback when the AI is unavailable.
- **Human-in-the-loop approvals**   every proposed roadmap becomes a pending request. It can only be used after the student approves it, and each decision is audited.
- **Verified real opportunities**   a curated catalog of official pages (MLH Global Hack Week, Outreachy, Google Summer of Code). Status is deliberately conservative: a reachable page is *not* treated as proof that registration is open.
- **Live freshness checks**   on-demand checks against an allowlist of organizer sites only.
- **Application packets**   prepare and review application material, then hand it off for the student to submit themselves.
- **Access control**   passphrase login, signed session cookies and cross-site request checks.

## Tech stack

Python 3.11+, FastAPI, Uvicorn, FastMCP, Pydantic, httpx, SQLite, plain HTML frontend, Docker.

## Project structure

```
backend/
  main.py                 FastAPI app, analysis and approval endpoints
  mcp_server.py           MCP tools (search, eligibility, roadmap)
  workflow.py             MCP-driven analysis workflow
  ai_workflow.py          Adds AI explanations with fallback
  ai_agent.py             Gemini / OpenAI provider layer
  agent_engine.py         Agent orchestrator (LLM picks MCP tools)
  agent_routes.py         /api/agent endpoints
  approvals.py            Approval records (SQLite)
  application_packets.py  Application preparation and handoff
  real_opportunities.py   Curated catalog of official opportunities
  live_sources.py         Allowlisted freshness checks
  verification_routes.py  Real-opportunity and audit endpoints
  completion_routes.py    Live check, packets, gate check
  security.py             Login, sessions, request checks
  ui.py                   Serves the web UI
frontend/                 index.html, verification.html
tests/                    pytest suite
Dockerfile
requirements.txt
```

## Getting started

### 1. Clone and install

```bash
git clone https://github.com/Laibaawais07/ORBIT.git
cd ORBIT
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root. **Never commit it** (it is already in `.gitignore`).

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.5-flash
ORBIT_ACCESS_TOKEN=a-long-random-string-of-at-least-24-characters
ORBIT_COOKIE_SECURE=false
```

| Variable | Required | Description |
|---|---|---|
| `AI_PROVIDER` | Yes | `gemini` or `openai` |
| `GEMINI_API_KEY` | If provider is `gemini` | Key from [Google AI Studio](https://aistudio.google.com) |
| `GEMINI_MODEL` | Recommended | Gemini model name, e.g. `gemini-2.5-flash` |
| `OPENAI_API_KEY` | If provider is `openai` | Key from [OpenAI](https://platform.openai.com) |
| `OPENAI_MODEL` | No | Defaults to `gpt-4.1-mini` |
| `ORBIT_ACCESS_TOKEN` | Yes | The login passphrase. Must be at least 24 characters. |
| `ORBIT_COOKIE_SECURE` | Yes | `true` when served over HTTPS, `false` for plain `http://localhost` |
| `ORBIT_DB_PATH` | No | SQLite path for approvals (default `data/orbit.sqlite3`) |
| `ORBIT_APPLICATION_DB_PATH` | No | SQLite path for application packets |


### 3. Run

```bash
uvicorn backend.main:app --reload --port 8000
```

Open <http://localhost:8000>, sign in with your `ORBIT_ACCESS_TOKEN`, and use the app at `/app`. Interactive API docs are at `/docs` after you log in.



## Tests

```bash
pip install pytest
pytest tests
```

## Docker

```bash
docker build -t orbit .
docker run -p 8000:8000 --env-file .env orbit
```

The image listens on `$PORT` (default `8000`).

