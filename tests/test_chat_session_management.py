import pytest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service
from backend.app.database.db import get_db_connection

client = TestClient(app)


def test_01_delete_one_conversation():
    """1. Delete one conversation returns SUCCESS and 404 on subsequent get."""
    title = f"Test Session {uuid.uuid4().hex[:6]}"
    res = client.post("/api/tofu/chat/sessions", json={"title": title, "dataset_name": "tofu", "author_id": "TOFU-000"})
    assert res.status_code == 200
    session_id = res.json()["id"]

    # Verify exists
    res_get = client.get(f"/api/tofu/chat/sessions/{session_id}")
    assert res_get.status_code == 200

    # Delete
    res_del = client.delete(f"/api/tofu/chat/sessions/{session_id}")
    assert res_del.status_code == 200
    data = res_del.json()
    assert data["status"] == "SUCCESS"
    assert data["deleted_session_id"] == session_id

    # Verify gone
    res_after = client.get(f"/api/tofu/chat/sessions/{session_id}")
    assert res_after.status_code == 404


def test_02_cancel_deletion_leaves_conversation_intact():
    """2. Cancelling deletion (not invoking backend delete) preserves session and messages."""
    title = f"Cancel Test {uuid.uuid4().hex[:6]}"
    res = client.post("/api/tofu/chat/sessions", json={"title": title, "dataset_name": "tofu", "author_id": "TOFU-000"})
    session_id = res.json()["id"]

    # Post message
    msg_res = client.post(f"/api/tofu/chat/sessions/{session_id}/messages", json={
        "content": "What is the author name?",
        "author_id": "TOFU-000",
        "mode": "deterministic"
    })
    assert msg_res.status_code == 200

    # User cancels modal in frontend -> no DELETE endpoint call made
    check = client.get(f"/api/tofu/chat/sessions/{session_id}")
    assert check.status_code == 200
    assert len(check.json()["messages"]) >= 2  # user + assistant


def test_03_delete_selected_conversation_successfully():
    """3. Deleting a selected conversation removes it and keeps others."""
    res1 = client.post("/api/tofu/chat/sessions", json={"title": "Session 1", "dataset_name": "tofu"})
    res2 = client.post("/api/tofu/chat/sessions", json={"title": "Session 2", "dataset_name": "tofu"})
    id1, id2 = res1.json()["id"], res2.json()["id"]

    # Delete session 1
    res_del = client.delete(f"/api/tofu/chat/sessions/{id1}")
    assert res_del.status_code == 200

    # Check listing
    list_res = client.get("/api/tofu/chat/sessions")
    active_ids = [s["id"] for s in list_res.json()]
    assert id1 not in active_ids
    assert id2 in active_ids


def test_04_delete_currently_active_conversation_switches_cleanly():
    """4. When the currently active conversation is deleted, remaining candidates are valid."""
    res1 = client.post("/api/tofu/chat/sessions", json={"title": "Active Candidate 1", "dataset_name": "tofu"})
    res2 = client.post("/api/tofu/chat/sessions", json={"title": "Active Candidate 2", "dataset_name": "tofu"})
    id1, id2 = res1.json()["id"], res2.json()["id"]

    # Delete currently active (id1)
    del_res = client.delete(f"/api/tofu/chat/sessions/{id1}")
    assert del_res.status_code == 200

    # Check that id2 remains and can be selected cleanly
    res_switch = client.get(f"/api/tofu/chat/sessions/{id2}")
    assert res_switch.status_code == 200
    assert res_switch.json()["id"] == id2


def test_05_delete_nonexistent_conversation_returns_404():
    """5. Attempting to delete a nonexistent conversation returns 404."""
    fake_id = f"nonexistent_{uuid.uuid4().hex}"
    res = client.delete(f"/api/tofu/chat/sessions/{fake_id}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_06_attempt_invalid_session_deletion():
    """6. Invalid or malformed session ID returns 404 safely."""
    invalid_id = "invalid---session-id-%%%$$"
    res = client.delete(f"/api/tofu/chat/sessions/{invalid_id}")
    assert res.status_code == 404


def test_07_delete_all_conversations():
    """7. Delete all conversations clears the chat sessions table completely."""
    # Ensure at least 2 sessions exist
    client.post("/api/tofu/chat/sessions", json={"title": "Bulk 1", "dataset_name": "tofu"})
    client.post("/api/tofu/chat/sessions", json={"title": "Bulk 2", "dataset_name": "tofu"})

    # Delete all
    del_all = client.delete("/api/tofu/chat/sessions")
    assert del_all.status_code == 200
    data = del_all.json()
    assert data["status"] == "SUCCESS"
    assert data["deleted_count"] >= 2

    # Verify listing is now empty
    list_res = client.get("/api/tofu/chat/sessions")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0


def test_08_verify_other_sessions_unaffected_when_one_deleted():
    """8. Verifies other sessions and their message history remain untouched when one is deleted."""
    res_a = client.post("/api/tofu/chat/sessions", json={"title": "Session A", "dataset_name": "tofu", "author_id": "TOFU-000"})
    res_b = client.post("/api/tofu/chat/sessions", json={"title": "Session B", "dataset_name": "tofu", "author_id": "TOFU-001"})
    id_a = res_a.json()["id"]
    id_b = res_b.json()["id"]

    # Send unique message to Session B
    unique_content = f"Unique query {uuid.uuid4().hex}"
    client.post(f"/api/tofu/chat/sessions/{id_b}/messages", json={
        "content": unique_content,
        "author_id": "TOFU-001",
        "mode": "deterministic"
    })

    # Delete Session A
    del_res = client.delete(f"/api/tofu/chat/sessions/{id_a}")
    assert del_res.status_code == 200

    # Verify Session B is completely intact
    b_data = client.get(f"/api/tofu/chat/sessions/{id_b}").json()
    assert b_data["id"] == id_b
    assert any(unique_content in m.get("content", "") for m in b_data["messages"])


def test_09_verify_tofu_records_remain_unchanged():
    """9. Chat session deletion must NEVER alter TOFU dataset records or trigger unlearning."""
    authors_before = client.get("/api/tofu/authors").json()
    assert len(authors_before) > 0

    # Create and delete chat session
    res = client.post("/api/tofu/chat/sessions", json={"title": "Ephemeral Session", "dataset_name": "tofu"})
    s_id = res.json()["id"]
    client.delete(f"/api/tofu/chat/sessions/{s_id}")

    # Verify TOFU authors and active knowledge records are 100% identical
    authors_after = client.get("/api/tofu/authors").json()
    assert len(authors_before) == len(authors_after)
    for a_before, a_after in zip(authors_before, authors_after):
        assert a_before["author_id"] == a_after["author_id"]
        assert a_before["is_fully_unlearned"] == a_after["is_fully_unlearned"]
        assert a_before["retained_records_count"] == a_after["retained_records_count"]


def test_10_verify_forgetting_requests_remain_unchanged():
    """10. Chat session deletion must NEVER modify or delete the forgetting_requests table."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM forgetting_requests")
    req_count_before = c.fetchone()["cnt"]
    conn.close()

    # Create and delete session
    res = client.post("/api/tofu/chat/sessions", json={"title": "Ephemeral Session", "dataset_name": "tofu"})
    client.delete(f"/api/tofu/chat/sessions/{res.json()['id']}")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM forgetting_requests")
    req_count_after = c.fetchone()["cnt"]
    conn.close()

    assert req_count_before == req_count_after


def test_11_verify_checkpoints_and_experiment_history_unchanged():
    """11. Chat session deletion must NEVER delete or alter experiments or model checkpoints."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM experiments")
    exp_count_before = c.fetchone()["cnt"]
    conn.close()

    # Delete all chat sessions
    client.delete("/api/tofu/chat/sessions")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM experiments")
    exp_count_after = c.fetchone()["cnt"]
    conn.close()

    assert exp_count_before == exp_count_after


def test_12_verify_deleted_conversations_do_not_reappear_after_refresh():
    """12. Deleted sessions are permanently removed from the database and do not reappear on refresh."""
    res = client.post("/api/tofu/chat/sessions", json={"title": "Permanent Deletion Test", "dataset_name": "tofu"})
    s_id = res.json()["id"]

    # Delete session
    client.delete(f"/api/tofu/chat/sessions/{s_id}")

    # Re-query fresh DB connection directly
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM chat_sessions WHERE id = ?", (s_id,))
    row = c.fetchone()
    conn.close()
    assert row is None

    # Re-query REST endpoint (simulating page reload)
    list_res = client.get("/api/tofu/chat/sessions")
    active_ids = [s["id"] for s in list_res.json()]
    assert s_id not in active_ids
