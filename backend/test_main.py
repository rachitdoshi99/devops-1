import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", str(tmp_path / "test.db"))
    with TestClient(main.app) as c:  # context manager runs startup (creates the table)
        yield c


def test_crud_flow(client):
    t = client.post("/api/todos", json={"title": " Learn Docker ", "priority": "high", "due_date": "2030-01-01"}).json()
    assert t["title"] == "Learn Docker" and t["completed"] is False and t["priority"] == "high"

    done = client.patch(f"/api/todos/{t['id']}", json={"completed": True}).json()
    assert done["completed"] is True and done["title"] == "Learn Docker"

    cleared = client.patch(f"/api/todos/{t['id']}", json={"due_date": None}).json()
    assert cleared["due_date"] is None

    assert client.delete(f"/api/todos/{t['id']}").status_code == 204
    assert client.delete(f"/api/todos/{t['id']}").status_code == 404


def test_filter_search_bulk(client):
    for title in ["alpha", "beta", "gamma"]:
        client.post("/api/todos", json={"title": title})
    beta = client.get("/api/todos", params={"q": "bet"}).json()
    assert [t["title"] for t in beta] == ["beta"]

    client.patch(f"/api/todos/{beta[0]['id']}", json={"completed": True})
    assert len(client.get("/api/todos", params={"status": "active"}).json()) == 2
    assert len(client.get("/api/todos", params={"status": "completed"}).json()) == 1

    assert client.post("/api/todos/complete-all").json() == {"updated": 2}
    assert client.delete("/api/todos").json() == {"deleted": 3}
    assert client.get("/api/todos").json() == []


@pytest.mark.parametrize("body", [{"title": ""}, {"title": "x", "priority": "urgent"}, {"title": "x", "due_date": "tomorrow"}])
def test_validation(client, body):
    assert client.post("/api/todos", json=body).status_code == 422


def test_patch_rejects_blank_title(client):
    t = client.post("/api/todos", json={"title": "x"}).json()
    assert client.patch(f"/api/todos/{t['id']}", json={"title": "   "}).status_code == 422
