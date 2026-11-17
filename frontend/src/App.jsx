import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const FILTERS = ["all", "active", "completed"];
const PRIORITIES = ["low", "medium", "high"];
const today = () => new Date().toISOString().slice(0, 10);

function Item({ todo, onChange, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(todo.title);
  const overdue = todo.due_date && !todo.completed && todo.due_date < today();

  const save = () => {
    setEditing(false);
    const t = title.trim();
    if (t && t !== todo.title) onChange(todo.id, { title: t });
    else setTitle(todo.title);
  };

  return (
    <li className={`item ${todo.completed ? "done" : ""}`}>
      <input
        type="checkbox"
        aria-label={`Mark "${todo.title}" as ${todo.completed ? "active" : "done"}`}
        checked={todo.completed}
        onChange={(e) => onChange(todo.id, { completed: e.target.checked })}
      />
      <div className="body">
        {editing ? (
          <input
            className="edit"
            autoFocus
            value={title}
            maxLength={200}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={save}
            onKeyDown={(e) => {
              if (e.key === "Enter") save();
              if (e.key === "Escape") { setTitle(todo.title); setEditing(false); }
            }}
          />
        ) : (
          <span className="title" onDoubleClick={() => setEditing(true)} title="Double-click to edit">
            {todo.title}
          </span>
        )}
        <div className="meta">
          <select
            className={`pill ${todo.priority}`}
            aria-label="Priority"
            value={todo.priority}
            onChange={(e) => onChange(todo.id, { priority: e.target.value })}
          >
            {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
          </select>
          <input
            type="date"
            className={`date ${overdue ? "overdue" : ""}`}
            aria-label="Due date"
            value={todo.due_date || ""}
            onChange={(e) => onChange(todo.id, { due_date: e.target.value || null })}
          />
        </div>
      </div>
      <button className="icon" aria-label={`Edit "${todo.title}"`} onClick={() => setEditing(true)}>✎</button>
      <button className="icon danger" aria-label={`Delete "${todo.title}"`} onClick={() => onDelete(todo.id)}>✕</button>
    </li>
  );
}

export default function App() {
  const [todos, setTodos] = useState([]);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ title: "", priority: "medium", due_date: "" });
  const [error, setError] = useState("");

  const load = useCallback(
    () => api.list(filter, search).then(setTodos).catch((e) => setError(e.message)),
    [filter, search]
  );

  useEffect(() => {
    const t = setTimeout(load, 200); // debounce typing in the search box
    return () => clearTimeout(t);
  }, [load]);

  // Run an API call, then refresh the list; surface any failure in the banner.
  const act = (fn) => async (...args) => {
    setError("");
    try { await fn(...args); await load(); } catch (e) { setError(e.message); }
  };

  const add = act(async (e) => {
    e.preventDefault();
    if (!form.title.trim()) return;
    await api.create({ ...form, due_date: form.due_date || null });
    setForm({ ...form, title: "" });
  });
  const change = act(api.update);
  const remove = act(api.remove);
  const completeAll = act(api.completeAll);
  const clearDone = act(api.clearCompleted);

  const left = todos.filter((t) => !t.completed).length;

  return (
    <main className="app">
      <h1>Todo</h1>

      <form className="add" onSubmit={add}>
        <input
          placeholder="What needs doing?"
          aria-label="New todo"
          maxLength={200}
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
        <select aria-label="Priority" value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
          {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
        </select>
        <input type="date" aria-label="Due date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
        <button className="primary" disabled={!form.title.trim()}>Add</button>
      </form>

      {error && <div className="error" role="alert">{error}</div>}

      <div className="toolbar">
        <div className="tabs" role="tablist">
          {FILTERS.map((f) => (
            <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? "active" : ""} onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
        <input type="search" placeholder="Search…" aria-label="Search todos" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {todos.length === 0 ? (
        <p className="empty">{search || filter !== "all" ? "Nothing matches." : "All clear. Add your first todo."}</p>
      ) : (
        <ul className="list">
          {todos.map((t) => <Item key={t.id} todo={t} onChange={change} onDelete={remove} />)}
        </ul>
      )}

      <footer>
        <span>{left} item{left === 1 ? "" : "s"} left</span>
        <span>
          <button className="link" onClick={completeAll}>Complete all</button>
          <button className="link" onClick={clearDone}>Clear completed</button>
        </span>
      </footer>
    </main>
  );
}
