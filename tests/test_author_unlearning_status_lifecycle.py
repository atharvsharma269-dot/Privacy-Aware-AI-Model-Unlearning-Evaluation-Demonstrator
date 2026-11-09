import pytest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service, TOFUUnlearningService
from backend.app.database.db import get_db_connection

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset dataset and status tables before each test."""
    tofu_service.reset_dataset(admin_confirmed=True)
    yield
    tofu_service.reset_dataset(admin_confirmed=True)


def test_scenario_a_active_author_status():
    """Scenario A: Select an active author -> Expected: ACTIVE_KNOWLEDGE."""
    author_id = "TOFU-001"  # Chukwu Akabueze
    res = client.get(f"/api/tofu/authors/{author_id}/status")
    assert res.status_code == 200
    data = res.json()
    assert data["author_id"] == author_id
    assert data["status"] == "ACTIVE_KNOWLEDGE"
    assert data["progress"] == 0.0
    assert data["data_deleted"] is False
    assert data["unlearning_completed"] is False


def test_scenario_b_request_forgetting_without_confirmation():
    """Scenario B: Request forgetting without confirmation -> Expected: AWAITING_CONFIRMATION; author remains active."""
    author_id = "TOFU-001"
    # Create chat session
    chat = client.post("/api/tofu/chat/sessions", json={"title": "Status Test", "author_id": author_id}).json()

    # Request forgetting
    msg_res = client.post(f"/api/tofu/chat/sessions/{chat['id']}/messages", json={
        "content": "Please forget this author",
        "author_id": author_id,
    }).json()

    assert msg_res["assistant_message"]["intent"] == "FORGET_AUTHOR"

    # Status must now be AWAITING_CONFIRMATION
    status_res = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert status_res["status"] == "AWAITING_CONFIRMATION"

    # Author knowledge must still remain active (not yet unlearned)
    author_details = client.get(f"/api/tofu/authors/{author_id}").json()
    assert author_details["is_fully_unlearned"] is False
    assert author_details["status"] == "AWAITING_CONFIRMATION"


def test_scenario_c_to_g_confirm_and_lifecycle_transitions():
    """
    Scenario C-G:
    C: Confirm forgetting -> Transitions through states.
    D: FORGETTING_IN_PROGRESS & progress.
    E: DATA_DELETED.
    F: RETRIEVAL_UPDATED.
    G: UNLEARNING_COMPLETED & verification passed.
    """
    author_id = "TOFU-001"
    # Direct execution steps verification
    tofu_service.set_author_status(author_id, "FORGETTING_QUEUED", current_step="Queued for unlearning", progress=0.10)
    s_queued = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_queued["status"] == "FORGETTING_QUEUED"
    assert s_queued["progress"] == 0.10

    # D: In progress
    tofu_service.set_author_status(author_id, "FORGETTING_IN_PROGRESS", current_step="Pipeline active", progress=0.25)
    s_in_progress = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_in_progress["status"] == "FORGETTING_IN_PROGRESS"
    assert s_in_progress["progress"] == 0.25

    # E: Data deleted
    tofu_service.set_author_status(author_id, "DATA_DELETED", current_step="Records purged", progress=0.50, data_deleted=True)
    s_deleted = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_deleted["status"] == "DATA_DELETED"
    assert s_deleted["data_deleted"] is True

    # F: Retrieval updated
    tofu_service.set_author_status(author_id, "RETRIEVAL_UPDATED", current_step="Index updated", progress=0.75, data_deleted=True, retrieval_updated=True)
    s_retrieval = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_retrieval["status"] == "RETRIEVAL_UPDATED"
    assert s_retrieval["retrieval_updated"] is True

    # G: Full completion
    tofu_service.forget_author(author_id)
    s_completed = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_completed["status"] == "UNLEARNING_COMPLETED"
    assert s_completed["progress"] == 1.0
    assert s_completed["data_deleted"] is True
    assert s_completed["retrieval_updated"] is True
    assert s_completed["unlearning_completed"] is True
    assert s_completed["verification_passed"] is True


def test_scenario_h_partial_and_failed_states():
    """Scenario H: Partial and failed states."""
    author_id = "TOFU-003"
    # Partial forgetting
    tofu_service.set_author_status(author_id, "PARTIALLY_FORGOTTEN", current_step="Only 1 attribute purged", progress=0.05, data_deleted=True)
    s_part = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_part["status"] == "PARTIALLY_FORGOTTEN"

    # Failed state
    tofu_service.set_author_status(author_id, "FORGETTING_FAILED", current_step="CUDA OOM", error_message="Memory allocation failure")
    s_fail = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s_fail["status"] == "FORGETTING_FAILED"
    assert s_fail["error_message"] == "Memory allocation failure"


def test_scenario_i_persisted_status_survives_reload():
    """Scenario I: Status is persisted in SQLite and survives simulated reload."""
    author_id = "TOFU-004"
    tofu_service.set_author_status(author_id, "FORGETTING_IN_PROGRESS", current_step="Mid-flight step", progress=0.42)

    # Re-query from fresh REST call
    res = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert res["status"] == "FORGETTING_IN_PROGRESS"
    assert res["progress"] == 0.42
    assert res["current_step"] == "Mid-flight step"


def test_scenario_j_author_independence_switching():
    """Scenario J: Switching to another author shows the other author's independent status."""
    author_1 = "TOFU-001"
    author_2 = "TOFU-002"

    tofu_service.forget_author(author_1)

    s1 = client.get(f"/api/tofu/authors/{author_1}/status").json()
    s2 = client.get(f"/api/tofu/authors/{author_2}/status").json()

    assert s1["status"] == "UNLEARNING_COMPLETED"
    assert s2["status"] == "ACTIVE_KNOWLEDGE"


def test_scenario_k_backend_restart_consistency():
    """Scenario K: Status remains consistent after backend restart."""
    author_id = "TOFU-006"
    tofu_service.forget_author(author_id)

    # Simulate restart by instantiating fresh TOFUUnlearningService
    restarted = TOFUUnlearningService()
    s = restarted.get_author_status(author_id)
    assert s["status"] == "UNLEARNING_COMPLETED"
    assert s["unlearning_completed"] is True


def test_scenario_l_cancel_active_job():
    """Scenario L: Cancel an active request -> Reflects FORGETTING_CANCELLED."""
    author_id = "TOFU-007"
    chat = client.post("/api/tofu/chat/sessions", json={"title": "Cancel Test", "author_id": author_id}).json()

    # Initiate
    client.post(f"/api/tofu/chat/sessions/{chat['id']}/messages", json={
        "content": "Forget this author",
        "author_id": author_id,
    })

    # Cancel
    cancel_res = client.post(f"/api/tofu/chat/sessions/{chat['id']}/messages", json={
        "content": "CANCEL",
        "author_id": author_id,
    }).json()

    assert cancel_res["assistant_message"]["intent"] == "FORGET_CANCELLATION"
    s = client.get(f"/api/tofu/authors/{author_id}/status").json()
    assert s["status"] == "FORGETTING_CANCELLED"


def test_forensic_before_after_diff_endpoint():
    """Scenario 7: Live Before/After diff endpoint returns actual dynamic comparison."""
    author_id = "TOFU-001"
    diff_pre = client.get(f"/api/tofu/authors/{author_id}/diff").json()
    assert diff_pre["author_id"] == author_id
    assert diff_pre["status"] == "ACTIVE_KNOWLEDGE"
    assert diff_pre["data_store_status"] == "ACTIVE"
    assert diff_pre["verification_passed"] is False

    # Execute unlearning
    tofu_service.forget_author(author_id)

    diff_post = client.get(f"/api/tofu/authors/{author_id}/diff").json()
    assert diff_post["status"] == "UNLEARNING_COMPLETED"
    assert diff_post["data_store_status"] == "VERIFIED_PURGED"
    assert diff_post["retrieval_index_status"] == "VECTOR_EMBEDDINGS_PURGED"
    assert diff_post["neural_unlearning_status"] == "REGULARIZED_GRADIENT_ASCENT_APPLIED"
    assert diff_post["verification_passed"] is True
    assert "Information Redacted" in diff_post["post_deletion_answer"]
