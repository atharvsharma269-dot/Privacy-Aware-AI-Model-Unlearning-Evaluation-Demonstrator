import pytest
import os
import sys
import json
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import tofu_service, TOFUUnlearningService
from backend.app.services.experiment_service import ExperimentService
from ml.models import get_model

client = TestClient(app)
exp_service = ExperimentService()


def test_experiment_state_isolation_scenarios_a_to_h(tmp_path):
    """
    Executes the exact 8 test scenarios (A through H) required by the specification:
      TEST A: Create Experiment A. Forget author P-001 and confirm. Expected: P-001 unavailable in Exp A.
      TEST B: Create Experiment B from baseline. Expected: P-001 is available in Exp B.
      TEST C: Return to Experiment A. Expected: P-001 remains forgotten there.
      TEST D: Restart backend (re-instantiate services). Expected: Both states persist correctly.
      TEST E: Start a new conversation within Experiment B. Expected: P-001 remains available.
      TEST F: Load Experiment A's unlearned model. Expected: Correct experiment-specific checkpoint is loaded.
      TEST G: Load Experiment B's original model. Expected: Correct original baseline is loaded.
      TEST H: Switch between experiments repeatedly. Expected: No cross-experiment state contamination.
    """
    # 0. Clean repair before running
    print("\n[TEST] 0. Executing stale state repair...", flush=True)
    repair_res = client.post("/api/tofu/admin/repair-stale-state/execute", json={"confirmed": True}).json()
    assert repair_res["status"] == "REPAIR_COMPLETED"
    print("  -> Stale state repair completed.", flush=True)

    # --- TEST A: Create Experiment A. Forget author P-001 ---
    print("[TEST] A. Creating Experiment A and forgetting author P-001...", flush=True)
    res_exp_a = client.post("/api/experiments", json={
        "name": "Experiment A (Privacy Unlearning Study)",
        "dataset_name": "tofu",
        "model_name": "mlp",
        "knowledge_store_version": "v1.0-clean",
        "model_baseline": "original",
    })
    assert res_exp_a.status_code == 200
    exp_a_id = res_exp_a.json()["id"]

    # Before unlearning in Exp A, P-001 (Chukwu Akabueze) is available
    status_a_before = client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_a_id}").json()
    assert status_a_before["status"] == "ACTIVE_KNOWLEDGE"
    assert status_a_before["data_deleted"] is False

    # Execute forgetting of P-001 in Exp A
    forget_a_res = client.post("/api/tofu/forget-author", json={
        "author_id": "P-001",
        "experiment_id": exp_a_id,
    })
    assert forget_a_res.status_code == 200
    assert forget_a_res.json()["action"] == "AUTHOR_UNLEARNED"

    # Verify P-001 is now unavailable / redacted in Experiment A
    status_a_after = client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_a_id}").json()
    assert status_a_after["status"] == "UNLEARNING_COMPLETED"
    assert status_a_after["data_deleted"] is True

    qa_a = client.post("/api/tofu/ask", json={
        "question": "What is Chukwu Akabueze's date of birth?",
        "author_id": "P-001",
        "experiment_id": exp_a_id,
    }).json()
    assert qa_a["is_unlearned"] is True
    assert qa_a["status"] == "UNLEARNED_REDACTED"
    assert "Information Redacted" in qa_a["answer"]
    print("  -> TEST A PASSED: P-001 forgotten and redacted in Exp A.", flush=True)

    # --- TEST B: Create Experiment B from original baseline. Expected: P-001 available in Exp B ---
    print("[TEST] B. Creating Experiment B from baseline. Checking P-001 availability...", flush=True)
    res_exp_b = client.post("/api/experiments", json={
        "name": "Experiment B (Fresh Retention Study)",
        "dataset_name": "tofu",
        "model_name": "mlp",
        "knowledge_store_version": "v1.0-clean",
        "model_baseline": "original",
    })
    assert res_exp_b.status_code == 200
    exp_b_id = res_exp_b.json()["id"]

    # Verify P-001 is ACTIVE and AVAILABLE in Experiment B
    status_b = client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_b_id}").json()
    assert status_b["status"] == "ACTIVE_KNOWLEDGE"
    assert status_b["data_deleted"] is False

    qa_b = client.post("/api/tofu/ask", json={
        "question": "What is Chukwu Akabueze's date of birth?",
        "author_id": "P-001",
        "experiment_id": exp_b_id,
    }).json()
    assert qa_b["is_unlearned"] is False
    assert qa_b["status"] == "ACTIVE"
    assert "September 26, 1965" in qa_b["answer"]
    print("  -> TEST B PASSED: P-001 is intact and active in Exp B.", flush=True)

    # --- TEST C: Return to Experiment A. Expected: P-001 remains forgotten there ---
    print("[TEST] C. Returning to Experiment A. Checking P-001 remains forgotten...", flush=True)
    status_a_return = client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_a_id}").json()
    assert status_a_return["status"] == "UNLEARNING_COMPLETED"
    qa_a_return = client.post("/api/tofu/ask", json={
        "question": "What is Chukwu Akabueze's date of birth?",
        "author_id": "P-001",
        "experiment_id": exp_a_id,
    }).json()
    assert qa_a_return["is_unlearned"] is True
    assert "Information Redacted" in qa_a_return["answer"]
    print("  -> TEST C PASSED: P-001 remains forgotten in Exp A.", flush=True)

    # --- TEST D: Restart backend. Expected: Both experiment states persist correctly ---
    print("[TEST] D. Simulating backend restart. Verifying state persistence...", flush=True)
    restarted_tofu_service = TOFUUnlearningService()
    unlearned_in_a = restarted_tofu_service.get_unlearned_authors(exp_a_id)
    unlearned_in_b = restarted_tofu_service.get_unlearned_authors(exp_b_id)
    assert "TOFU-001" in unlearned_in_a
    assert "TOFU-001" not in unlearned_in_b
    assert len(unlearned_in_b) == 0
    print("  -> TEST D PASSED: Persistent registry correctly segregates both experiments across restarts.", flush=True)

    # --- TEST E: Start a new conversation within Experiment B. Expected: P-001 remains available ---
    print("[TEST] E. Starting new chat conversation in Experiment B...", flush=True)
    chat_res = client.post("/api/tofu/chat/sessions", json={
        "title": "Conversation in Exp B",
        "author_id": "P-001",
        "experiment_id": exp_b_id,
    })
    assert chat_res.status_code == 200
    session_b_id = chat_res.json()["id"]

    msg_res = client.post(f"/api/tofu/chat/sessions/{session_b_id}/messages", json={
        "content": "What is Chukwu Akabueze's date of birth?",
        "author_id": "P-001",
        "experiment_id": exp_b_id,
    })
    assert msg_res.status_code == 200
    msg_data = msg_res.json()
    assert "September 26, 1965" in msg_data["assistant_message"]["content"]
    assert msg_data["assistant_message"]["sources"][0]["is_unlearned"] is False
    print("  -> TEST E PASSED: New chat in Exp B retrieves factual answer.", flush=True)

    # --- TEST F & G: Model Checkpoint Verification ---
    print("[TEST] F & G. Verifying model checkpoint isolation and baseline integrity guards...", flush=True)
    # Setup test checkpoint files for Experiment A and Experiment B
    ckpt_dir_a = os.path.join(exp_service.checkpoints_dir, exp_a_id)
    ckpt_dir_b = os.path.join(exp_service.checkpoints_dir, exp_b_id)
    os.makedirs(ckpt_dir_a, exist_ok=True)
    os.makedirs(ckpt_dir_b, exist_ok=True)

    dummy_model = get_model("mlp")

    # Experiment A has unlearned checkpoint
    unlearned_ckpt_path_a = os.path.join(ckpt_dir_a, "unlearned.pt")
    torch.save({
        "model_state_dict": dummy_model.state_dict(),
        "metadata": {
            "model_type": "unlearned",
            "experiment_id": exp_a_id,
            "is_complete": True,
            "algorithm": "gradient_ascent",
        }
    }, unlearned_ckpt_path_a)

    # Experiment B has original baseline checkpoint
    orig_ckpt_path_b = os.path.join(ckpt_dir_b, "original.pt")
    torch.save({
        "model_state_dict": dummy_model.state_dict(),
        "metadata": {
            "model_type": "original",
            "experiment_id": exp_b_id,
            "is_complete": True,
            "dataset_name": "tofu",
        }
    }, orig_ckpt_path_b)

    # Update database checkpoint paths
    from backend.app.database.db import get_db_connection
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE experiments SET unlearned_checkpoint_path = ? WHERE id = ?", (unlearned_ckpt_path_a, exp_a_id))
    c.execute("UPDATE experiments SET original_checkpoint_path = ? WHERE id = ?", (orig_ckpt_path_b, exp_b_id))
    conn.commit()
    conn.close()

    # TEST F: Load Experiment A's unlearned model
    model_a, meta_a = exp_service.load_model_checkpoint(exp_a_id, "unlearned")
    assert meta_a["model_type"] == "unlearned"
    assert meta_a["experiment_id"] == exp_a_id

    # TEST G: Load Experiment B's original model
    model_b, meta_b = exp_service.load_model_checkpoint(exp_b_id, "original")
    assert meta_b["model_type"] == "original"
    assert meta_b["experiment_id"] == exp_b_id

    # Verify integrity guard: attempting to load an unlearned checkpoint as original baseline fails
    with pytest.raises(ValueError, match="is an unlearned checkpoint, cannot be loaded as original model baseline"):
        # Temporarily point Exp A original path to unlearned checkpoint
        conn = get_db_connection()
        conn.execute("UPDATE experiments SET original_checkpoint_path = ? WHERE id = ?", (unlearned_ckpt_path_a, exp_a_id))
        conn.commit()
        conn.close()
        exp_service.load_model_checkpoint(exp_a_id, "original")

    # --- TEST H: Switch between experiments repeatedly. Expected: No contamination ---
    print("[TEST] H. Alternating queries across experiments repeatedly...", flush=True)
    for _ in range(5):
        # Query A -> must be unlearned
        q_a = client.post("/api/tofu/ask", json={
            "question": "What is Chukwu Akabueze's date of birth?",
            "author_id": "P-001",
            "experiment_id": exp_a_id,
        }).json()
        assert q_a["is_unlearned"] is True

        # Query B -> must be active and factual
        q_b = client.post("/api/tofu/ask", json={
            "question": "What is Chukwu Akabueze's date of birth?",
            "author_id": "P-001",
            "experiment_id": exp_b_id,
        }).json()
        assert q_b["is_unlearned"] is False
        assert "September 26, 1965" in q_b["answer"]
    print("ALL SCENARIOS A THROUGH H PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_experiment_state_isolation_scenarios_a_to_h(None)
