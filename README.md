# devops-1: Todo app to learn Docker

React (Vite) frontend + FastAPI backend + SQLite, wired together with Docker Compose.

```
Browser ──> nginx :3000 (serves React build)
                 │  /api/*
                 ▼
            FastAPI :8000 ──> SQLite file on the `todo-data` volume
```

## Features

Add, edit (double-click or ✎), complete, delete · priority (low/medium/high) · due date with overdue highlight · filter all/active/completed · search · complete all · clear completed · dark mode follows your OS.

## Run it

```bash
docker compose up --build
```

Open http://localhost:3000. API docs: not exposed in this mode (see dev mode below).

Hot-reload dev mode (frontend http://localhost:5173, API + Swagger http://localhost:8000/docs):

```bash
docker compose -f docker-compose.dev.yml up --build
```

Run backend tests in a throwaway container:

```bash
docker run --rm -v "${PWD}/backend:/app" -w /app python:3.12-slim sh -c "pip install -q -r requirements-dev.txt && pytest -q"
```

## Docker concepts to look at, and where

| Concept | Where |
|---|---|
| Layer caching (deps copied before code) | `backend/Dockerfile`, `frontend/Dockerfile` |
| Multi-stage build (Node builds, nginx serves) | `frontend/Dockerfile` |
| Non-root user | `backend/Dockerfile` |
| `.dockerignore` | `backend/.dockerignore`, `frontend/.dockerignore` |
| Healthcheck + `depends_on: service_healthy` | `docker-compose.yml` |
| Named volume (data survives rebuilds) | `todo-data` in `docker-compose.yml` |
| Service-name networking (`http://backend:8000`) | `frontend/nginx.conf` |
| Bind mounts for hot reload | `docker-compose.dev.yml` |

## Useful commands

```bash
docker compose ps                    # running services + health
docker compose logs -f backend       # follow backend logs
docker compose exec backend sh       # shell inside the container
docker compose exec backend python -c "import sqlite3; print(sqlite3.connect('/data/todos.db').execute('select * from todos').fetchall())"
docker compose down                  # stop, keep data
docker compose down -v               # stop AND delete the todo-data volume
docker image ls                      # compare frontend (~50MB) vs backend image sizes
```

Try this: add a todo, run `docker compose down`, then `docker compose up`. The todo is still there. Now run `docker compose down -v` and it is gone.

## Without Docker

```bash
cd backend && pip install -r requirements-dev.txt && uvicorn main:app --reload   # :8000
cd frontend && npm install && npm run dev                                         # :5173 (Node 18+)
```

## API

| Method | Path | Notes |
|---|---|---|
| GET | `/api/todos?status=all\|active\|completed&q=text` | open items first, then by due date |
| POST | `/api/todos` | `{title, priority?, due_date?}` |
| PATCH | `/api/todos/{id}` | any of `title, completed, priority, due_date` (`null` clears the date) |
| DELETE | `/api/todos/{id}` | |
| POST | `/api/todos/complete-all` | |
| DELETE | `/api/todos` | clears completed |
| GET | `/api/health` | used by the healthcheck |
