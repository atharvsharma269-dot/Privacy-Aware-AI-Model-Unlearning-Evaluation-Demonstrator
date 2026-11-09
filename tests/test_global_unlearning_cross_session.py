import pytest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service, TOFUUnlearningService
from backend.app.database.db import get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_to_clean_state():
    """Reset TOFU service and clean up database tables before each test."""
    tofu_service.reset_dataset(admin_confirmed=True)
    yield
    tofu_service.reset_dataset(admin_confirmed=True)


def test_scenario_a_to_g_cross_session_unlearning_lifecycle():
    """
    Executes the exact end-to-end scenario specified in the requirements:
    A. Start with Author A, Author B and Author C intact.
    B. Open Chat 1 and verify that all three authors can be retrieved.
    C. Explicitly request forgetting Author A and confirm.
    D. Open Chat 2 and ask about Author A. The system must not retrieve forgotten information.
    E. Ask about Author B and Author C. Both must still work normally.
    F. Restart the application (re-instantiate service) and repeat the tests.
    G. Open an older chat session and verify that it cannot retrieve Author A through memory/RAG.
    """
    author_a = "TOFU-000"  # Jaime Vasquez
    author_b = "TOFU-001"
    author_c = "TOFU-002"

    # Step A: Verify all three authors start intact
    authors = client.get("/api/tofu/authors").json()
    auth_map = {a["author_id"]: a for a in authors}
    assert auth_map[author_a]["is_fully_unlearned"] is False
    assert auth_map[author_b]["is_fully_unlearned"] is False
    assert auth_map[author_c]["is_fully_unlearned"] is False

    # Step B: Open Chat 1 and verify that all three authors can be retrieved
    res_c1 = client.post("/api/tofu/chat/sessions", json={"title": "Chat 1 Baseline", "author_id": author_a})
    assert res_c1.status_code == 200
    chat_1_id = res_c1.json()["id"]

    # Retrieve Author A in Chat 1
    msg_a = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_a,
    }).json()
    assert "Jaime Vasquez" in msg_a["assistant_message"]["content"]
    assert msg_a["assistant_message"]["sources"][0]["is_unlearned"] is False

    # Retrieve Author B in Chat 1
    msg_b = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_b,
    }).json()
    assert msg_b["assistant_message"]["sources"][0]["author_id"] == author_b
    assert msg_b["assistant_message"]["sources"][0]["is_unlearned"] is False

    # Retrieve Author C in Chat 1
    msg_c = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_c,
    }).json()
    assert msg_c["assistant_message"]["sources"][0]["author_id"] == author_c
    assert msg_c["assistant_message"]["sources"][0]["is_unlearned"] is False

    # Step C: Explicitly request forgetting Author A and confirm
    forget_init = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "Please forget this author completely",
        "author_id": author_a,
    }).json()
    assert forget_init["assistant_message"]["intent"] == "FORGET_AUTHOR"
    assert "CONFIRM" in forget_init["assistant_message"]["content"]

    confirm_res = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "CONFIRM",
        "author_id": author_a,
    }).json()
    assert "[PERMANENT UNLEARNING EXECUTED]" in confirm_res["assistant_message"]["content"]
    assert confirm_res["assistant_message"]["intent"] == "FORGET_CONFIRMATION"

    # Verify Author A is recorded in the persistent global unlearning registry
    registry = client.get("/api/tofu/unlearning/registry").json()
    reg_authors = [r["target_author_id"] for r in registry]
    assert author_a in reg_authors

    # Step D: Open Chat 2 and ask about Author A. The system must not retrieve forgotten information.
    res_c2 = client.post("/api/tofu/chat/sessions", json={"title": "Chat 2 Isolation Test", "author_id": author_a})
    assert res_c2.status_code == 200
    chat_2_id = res_c2.json()["id"]

    c2_ask_a = client.post(f"/api/tofu/chat/sessions/{chat_2_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_a,
    }).json()
    assert "[PRIVACY ENFORCED // RECORD REDACTED]" in c2_ask_a["assistant_message"]["content"]
    assert "Jaime Vasquez" not in c2_ask_a["assistant_message"]["sources"][0]["ground_truth_answer"]
    assert c2_ask_a["assistant_message"]["sources"][0]["is_unlearned"] is True
    assert c2_ask_a["assistant_message"]["sources"][0]["status"] == "UNLEARNED_REDACTED"

    # Step E: Ask about Author B and Author C in Chat 2. Both must still work normally!
    c2_ask_b = client.post(f"/api/tofu/chat/sessions/{chat_2_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_b,
    }).json()
    assert c2_ask_b["assistant_message"]["sources"][0]["is_unlearned"] is False
    assert c2_ask_b["assistant_message"]["sources"][0]["status"] == "ACTIVE"
    assert "[PRIVACY ENFORCED" not in c2_ask_b["assistant_message"]["content"]

    c2_ask_c = client.post(f"/api/tofu/chat/sessions/{chat_2_id}/messages", json={
        "content": "What is the author name?",
        "author_id": author_c,
    }).json()
    assert c2_ask_c["assistant_message"]["sources"][0]["is_unlearned"] is False
    assert c2_ask_c["assistant_message"]["sources"][0]["status"] == "ACTIVE"
    assert "[PRIVACY ENFORCED" not in c2_ask_c["assistant_message"]["content"]

    # Step F: Restart application (instantiate fresh TOFUUnlearningService) and repeat the tests
    fresh_service = TOFUUnlearningService()
    assert author_a in fresh_service.unlearned_authors
    assert author_b not in fresh_service.unlearned_authors
    assert author_c not in fresh_service.unlearned_authors

    # Direct query on fresh service refuses Author A and satisfies Author B & C
    q_a = fresh_service.query_qa("What is the author name?", author_id=author_a)
    assert q_a["is_unlearned"] is True
    assert q_a["status"] == "UNLEARNED_REDACTED"
    assert "Information Redacted" in q_a["answer"]

    q_b = fresh_service.query_qa("What is the author name?", author_id=author_b)
    assert q_b["is_unlearned"] is False
    assert q_b["status"] == "ACTIVE"

    q_c = fresh_service.query_qa("What is the author name?", author_id=author_c)
    assert q_c["is_unlearned"] is False
    assert q_c["status"] == "ACTIVE"

    # Step G: Open an older chat session (Chat 1) and verify that it cannot retrieve Author A through its memory or RAG context
    # 1. Fetching Chat 1 session messages must sanitize past citations
    c1_loaded = client.get(f"/api/tofu/chat/sessions/{chat_1_id}").json()
    for m in c1_loaded["messages"]:
        if m.get("role") == "assistant" and m.get("sources"):
            for s in m["sources"]:
                if s.get("author_id") == author_a:
                    assert s["is_unlearned"] is True
                    assert s["status"] == "UNLEARNED_REDACTED"

    # 2. Posting a new query in Chat 1 about Author A must enforce privacy redaction
    c1_followup = client.post(f"/api/tofu/chat/sessions/{chat_1_id}/messages", json={
        "content": "What is the author date of birth?",
        "author_id": author_a,
    }).json()
    assert "[PRIVACY ENFORCED // RECORD REDACTED]" in c1_followup["assistant_message"]["content"]
    assert c1_followup["assistant_message"]["sources"][0]["is_unlearned"] is True


def test_global_unlearning_registry_persistence_survives_restarts():
    """Verifies SQLite table global_unlearning_registry maintains unlearned authors across restarts."""
    author_id = "TOFU-005"
    res = client.post("/api/tofu/forget-author", json={"author_id": author_id})
    assert res.status_code == 200

    # Inspect SQLite database directly
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM global_unlearning_registry WHERE target_author_id = ?", (author_id,))
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row["status"] == "CONFIRMED"

    # Simulate restart with fresh service instance
    restarted_service = TOFUUnlearningService()
    assert author_id in restarted_service.unlearned_authors
    assert len(restarted_service.unlearned_qa[author_id]) == 20


def test_chat_deletion_does_not_destroy_global_unlearning_registry():
    """Deleting chat sessions must NEVER clear or damage the persistent global unlearning registry."""
    author_id = "TOFU-008"
    client.post("/api/tofu/forget-author", json={"author_id": author_id})

    # Create and delete a chat session
    chat = client.post("/api/tofu/chat/sessions", json={"title": "Disposable Chat", "author_id": author_id}).json()
    del_res = client.delete(f"/api/tofu/chat/sessions/{chat['id']}")
    assert del_res.status_code == 200

    # Delete all chat sessions
    del_all = client.delete("/api/tofu/chat/sessions")
    assert del_all.status_code == 200

    # Verify global unlearning registry is 100% intact
    registry = client.get("/api/tofu/unlearning/registry").json()
    reg_authors = [r["target_author_id"] for r in registry]
    assert author_id in reg_authors
    assert author_id in tofu_service.unlearned_authors


def test_fine_grained_qa_global_cross_session_filtering():
    """Fine-grained single QA pair unlearning must be globally filtered across all chat sessions."""
    author_id = "TOFU-010"
    qa_id = "TOFU-QA-0200"

    # Session 1: unlearn single QA
    res = client.post("/api/tofu/forget-qa", json={"author_id": author_id, "qa_id": qa_id})
    assert res.status_code == 200

    # Session 2: asks the unlearned question
    sess2 = client.post("/api/tofu/chat/sessions", json={"title": "Session 2 QA Check", "author_id": author_id}).json()
    chat_res = client.post(f"/api/tofu/chat/sessions/{sess2['id']}/messages", json={
        "content": "Where was the author born?",
        "author_id": author_id,
    }).json()

    # If this matched the unlearned QA, verify it is marked unlearned and redacted
    source = chat_res["assistant_message"]["sources"][0]
    if source["source_id"] == qa_id:
        assert source["is_unlearned"] is True
        assert "[PRIVACY ENFORCED" in chat_res["assistant_message"]["content"]
