// Relative URLs: Vite's dev proxy and nginx both forward /api to the backend.
async function req(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body && JSON.stringify(options.body),
  });
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({}))).detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  list: (status, q) => req(`/todos?status=${status}&q=${encodeURIComponent(q)}`),
  create: (todo) => req("/todos", { method: "POST", body: todo }),
  update: (id, changes) => req(`/todos/${id}`, { method: "PATCH", body: changes }),
  remove: (id) => req(`/todos/${id}`, { method: "DELETE" }),
  completeAll: () => req("/todos/complete-all", { method: "POST" }),
  clearCompleted: () => req("/todos", { method: "DELETE" }),
};
