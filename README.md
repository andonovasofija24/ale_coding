# ALE — Adaptive Learning Environment

An AI-guided coding practice platform for undergraduate programming courses (C++).

## Services

| Service | Port | Description |
|---|---|---|
| Frontend | 3000 | React student + admin UI |
| Backend | 8000 | FastAPI REST API |
| Code Runner | 8001 (internal) | C++ sandbox execution |
| PostgreSQL | 5432 | Database |

## Quick Start

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY in .env

docker compose up --build
```

Then open http://localhost:3000

Default admin: `admin@example.com` / `adminpassword` (set via env vars).

## Architecture

```
frontend (React + Monaco)
    ↕ REST
backend (FastAPI)
    ├── /auth         — JWT auth (register/login)
    ├── /tasks        — task listing (student)
    ├── /sessions     — learning sessions + AI agent
    └── /admin        — task & test case management
         ↕ HTTP (internal)
code-runner (g++ sandbox)
         ↕ PostgreSQL
```

## AI Agent (Amazon Strands SDK)

The agent uses **GPT-4o** via OpenAI and has three capabilities:

1. **Plan generation** — on session start, analyzes task requirements + model solution → produces ordered steps (correctness-first, optimization-last)
2. **Step evaluation** — on "Check Step", evaluates student code against current step criteria → pass/fail + feedback
3. **Hints** — targeted guidance without revealing the answer

## Student Flow

1. Register / Login
2. Pick a task from the list
3. Click **Start Session** → AI generates a step-by-step plan
4. Write code in Monaco editor
5. **Check Step** → AI evaluates, gives feedback
6. **Hint** → AI gives a nudge without the answer
7. **Run All Tests** → runs all (including hidden) test cases
8. Progress through all steps to complete the task

## Admin Flow

1. Login with admin account
2. Go to **Admin** → **Manage Tasks**
3. Create task: title, description (Markdown), starter code, model solution, test cases
4. Test cases can be `code_sample` (snippet inserted into main) or `stdin_stdout`
5. Mark test cases as hidden to use them for grading but not show to students
