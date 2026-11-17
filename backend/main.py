import os
import sqlite3
from contextlib import closing, contextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "todos.db")
Priority = Literal["low", "medium", "high"]

app = FastAPI(title="Todo API")
# CORS only matters when the frontend runs on another origin (e.g. `vite dev` without the proxy).
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def db():
    # shortcut: one connection per request, fine for SQLite at this scale; use a pool/Postgres if it grows.
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        with conn:  # commit on success, rollback on error
            yield conn


@app.on_event("startup")
def init_db():
    with db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: Priority = "medium"
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class TodoPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    completed: Optional[bool] = None
    priority: Optional[Priority] = None
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


def row(r: sqlite3.Row) -> dict:
    return {**dict(r), "completed": bool(r["completed"])}


def get_or_404(conn, todo_id: int) -> sqlite3.Row:
    r = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "Todo not found")
    return r


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/todos")
def list_todos(
    status: Literal["all", "active", "completed"] = "all",
    q: str = Query("", max_length=200),
):
    sql, args = "SELECT * FROM todos WHERE title LIKE ?", [f"%{q}%"]
    if status != "all":
        sql += " AND completed = ?"
        args.append(1 if status == "completed" else 0)
    # open items first, then soonest due date (undated last), newest first
    sql += " ORDER BY completed, due_date IS NULL, due_date, id DESC"
    with db() as conn:
        return [row(r) for r in conn.execute(sql, args)]


@app.post("/api/todos", status_code=201)
def create_todo(todo: TodoIn):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO todos (title, priority, due_date) VALUES (?, ?, ?)",
            (todo.title.strip(), todo.priority, todo.due_date),
        )
        return row(get_or_404(conn, cur.lastrowid))


@app.patch("/api/todos/{todo_id}")
def update_todo(todo_id: int, patch: TodoPatch):
    # exclude_unset lets the client clear due_date by sending null, while omitted fields stay untouched
    changes = patch.model_dump(exclude_unset=True)
    if "title" in changes:
        if changes["title"] is None or not changes["title"].strip():
            raise HTTPException(422, "title cannot be empty")
        changes["title"] = changes["title"].strip()
    if "completed" in changes:
        if changes["completed"] is None:
            raise HTTPException(422, "completed cannot be null")
        changes["completed"] = int(changes["completed"])
    if "priority" in changes and changes["priority"] is None:
        raise HTTPException(422, "priority cannot be null")
    with db() as conn:
        get_or_404(conn, todo_id)
        if changes:
            sets = ", ".join(f"{k} = ?" for k in changes)  # keys come from the model, never from the client
            conn.execute(f"UPDATE todos SET {sets} WHERE id = ?", (*changes.values(), todo_id))
        return row(get_or_404(conn, todo_id))


@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    with db() as conn:
        get_or_404(conn, todo_id)
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))


@app.post("/api/todos/complete-all")
def complete_all():
    with db() as conn:
        n = conn.execute("UPDATE todos SET completed = 1 WHERE completed = 0").rowcount
    return {"updated": n}


@app.delete("/api/todos")
def clear_completed():
    with db() as conn:
        n = conn.execute("DELETE FROM todos WHERE completed = 1").rowcount
    return {"deleted": n}
