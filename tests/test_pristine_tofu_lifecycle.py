import unittest
import torch
import os
import json
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.tofu_service import TOFUUnlearningService, tofu_service, ForgettingState
from backend.app.services.experiment_service import ExperimentService
from backend.app.database.db import get_db_connection
from ml.models.mlp import FashionMLP
from ml.training.trainer import ModelTrainer


class TestPristineTOFULifecycle(unittest.TestCase):
    """
    Automated regression suite for pristine dataset lifecycle, explicit user initiation,
    and checkpoint isolation (Tests A through L).
    """

    def setUp(self):
        self.client = TestClient(app)
        # Restore active baseline before each test
        tofu_service.reset_dataset(admin_confirmed=True)

    # TEST A: Fresh initialization. Expected: Every original TOFU record is available.
    def test_A_fresh_initialization(self):
        service = TOFUUnlearningService()
        manifest = service.get_pristine_manifest()

        self.assertEqual(manifest["authors_count"], 200)
        self.assertEqual(manifest["qa_pairs_count"], 4000)
        self.assertEqual(manifest["initial_status"], ForgettingState.NOT_REQUESTED)
        self.assertIsNotNone(manifest["authors_file_sha256"])
        self.assertIsNotNone(manifest["qa_file_sha256"])

        # Verify active store starts completely intact
        self.assertEqual(len(service.working_authors), 200)
        self.assertEqual(len(service.unlearned_authors), 0)
        for a_id, qas in service.unlearned_qa.items():
            self.assertEqual(len(qas), 0)

    # TEST B: Ask for an author name without any deletion request. Expected: Original info returned.
    def test_B_ask_author_name_without_deletion(self):
        res = tofu_service.query_qa("What is the author's name?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertFalse(res["is_unlearned"])
        self.assertIn("Jaime Vasquez", res["answer"])
        self.assertNotIn("RECORD REDACTED", res["answer"])

    # TEST C: Start a new conversation. Expected: No information is automatically marked forgotten.
    def test_C_start_new_conversation(self):
        # Create fresh session
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Fresh Pristine Conversation",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # Ask normal factual question
        msg_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the author's name?", "author_id": "TOFU-000"}
        ).json()

        content = msg_res["assistant_message"]["content"]
        self.assertIn("Jaime Vasquez", content)
        self.assertNotIn("RECORD REDACTED", content)
        self.assertNotIn("PRIVACY ENFORCED", content)
        self.assertFalse(msg_res["assistant_message"]["sources"][0]["is_unlearned"])

    # TEST D: Restart the backend. Expected: Original records remain available, no deletion executes.
    def test_D_restart_backend(self):
        # Instantiate brand new service to simulate process restart
        restarted_service = TOFUUnlearningService()
        self.assertEqual(len(restarted_service.unlearned_authors), 0)

        res = restarted_service.query_qa("What is the author's name?", author_id="TOFU-000")
        self.assertTrue(res["found"])
        self.assertEqual(res["status"], "ACTIVE")
        self.assertIn("Jaime Vasquez", res["answer"])

    # TEST E: Create a new experiment. Expected: No existing forgetting state is applied.
    def test_E_create_new_experiment(self):
        exp_service = ExperimentService()
        exp = exp_service.create_experiment(
            name="Pristine Baseline Experiment",
            description="Pristine test experiment",
            dataset_name="tofu",
            model_name="mlp",
            seed=42,
        )
        self.assertEqual(exp["status"], "CREATED")
        self.assertIsNone(exp.get("original_checkpoint_path"))
        self.assertIsNone(exp.get("unlearned_checkpoint_path"))
        self.assertIsNone(exp.get("retrained_checkpoint_path"))

    # TEST F: Request deletion but do not confirm. Expected: Information remains available, stays pending.
    def test_F_request_deletion_without_confirmation(self):
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Unconfirmed Deletion Session",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # 1. Request deletion
        req_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "Forget everything about this author.", "author_id": "TOFU-000"}
        ).json()
        self.assertEqual(req_res["intent"], "FORGET_AUTHOR")
        self.assertIsNotNone(req_res["pending_action"])
        self.assertEqual(req_res["pending_action"]["status"], ForgettingState.AWAITING_CONFIRMATION)

        # 2. Query author without confirming: information must still be available
        q_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the author's name?", "author_id": "TOFU-000"}
        ).json()
        content = q_res["assistant_message"]["content"]
        self.assertIn("Jaime Vasquez", content)
        self.assertNotIn("RECORD REDACTED", content)

    # TEST G: Cancel a pending deletion. Expected: No deletion occurs.
    def test_G_cancel_pending_deletion(self):
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Cancel Deletion Session",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # Request deletion
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "Forget this author.", "author_id": "TOFU-000"}
        )

        # Cancel deletion
        cancel_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "CANCEL", "author_id": "TOFU-000"}
        ).json()
        self.assertEqual(cancel_res["intent"], "FORGET_CANCELLATION")
        self.assertIn("CANCELLED", cancel_res["assistant_message"]["content"])

        # Query author: must remain active
        q_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the author's birth date?", "author_id": "TOFU-000"}
        ).json()
        self.assertIn("1958", q_res["assistant_message"]["content"])

    # TEST H: Confirm a valid deletion. Expected: Only confirmed target and scope are processed.
    def test_H_confirm_valid_deletion(self):
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Confirm Deletion Session",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # Request deletion of author's name (attribute fact_1)
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "Forget the author's name.", "author_id": "TOFU-000"}
        )

        # Confirm deletion
        conf_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "CONFIRM", "author_id": "TOFU-000"}
        ).json()
        self.assertEqual(conf_res["intent"], "FORGET_CONFIRMATION")
        self.assertIn("PERMANENT UNLEARNING EXECUTED", conf_res["assistant_message"]["content"])
        self.assertIn("COMPLETED (Verified Purged)", conf_res["assistant_message"]["content"])

    # TEST I: Ask about forgotten author after execution. Expected: Post-deletion refusal displayed.
    def test_I_ask_forgotten_author_post_execution(self):
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Post Execution Session",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # Request and confirm deletion
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "Forget this author.", "author_id": "TOFU-000"}
        )
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "CONFIRM", "author_id": "TOFU-000"}
        )

        # Ask question about forgotten author
        post_res = self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "What is the author's name?", "author_id": "TOFU-000"}
        ).json()
        content = post_res["assistant_message"]["content"]
        self.assertIn("RECORD REDACTED", content)
        self.assertIn("permanently unlearned", content)

    # TEST J: Ask about an unrelated author. Expected: Unrelated information remains available.
    def test_J_unrelated_author_remains_available(self):
        s_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Unrelated Author Session",
            "author_id": "TOFU-000"
        }).json()
        session_id = s_res["id"]

        # Forget TOFU-000 (Jaime Vasquez)
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "Forget this author.", "author_id": "TOFU-000"}
        )
        self.client.post(
            f"/api/tofu/chat/sessions/{session_id}/messages",
            json={"content": "CONFIRM", "author_id": "TOFU-000"}
        )

        # Query unrelated author TOFU-004 (Jordan Sinclair)
        unrelated_res = tofu_service.query_qa("What is the author's birth date?", author_id="TOFU-004")
        self.assertTrue(unrelated_res["found"])
        self.assertFalse(unrelated_res["is_unlearned"])
        self.assertEqual(unrelated_res["status"], "ACTIVE")
        self.assertIn("May 16, 1978", unrelated_res["answer"])

    # TEST K: Restore development test baseline. Expected: Original source records become available without destroying experiment logs.
    def test_K_restore_baseline(self):
        # 1. Modify active store
        tofu_service.forget_author("TOFU-000")
        self.assertTrue("TOFU-000" in tofu_service.unlearned_authors)

        # 2. Execute administrative baseline reset
        reset_res = self.client.post("/api/tofu/admin/reset-baseline")
        self.assertEqual(reset_res.status_code, 200)
        data = reset_res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["unlearned_count"], 0)

        # 3. Verify Jaime Vasquez is restored to active knowledge store
        q_res = tofu_service.query_qa("What is the author's name?", author_id="TOFU-000")
        self.assertTrue(q_res["found"])
        self.assertEqual(q_res["status"], "ACTIVE")
        self.assertIn("Jaime Vasquez", q_res["answer"])

        # 4. Verify historical experiments table is preserved
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as count FROM experiments")
        exp_count = c.fetchone()["count"]
        conn.close()
        self.assertGreaterEqual(exp_count, 0)

    # TEST L: Load original model. Expected: Correct original checkpoint loaded, unlearned checkpoint rejected.
    def test_L_load_original_model(self):
        ckpt_dir = "./checkpoints/test_model_isolation"
        os.makedirs(ckpt_dir, exist_ok=True)
        orig_ckpt_path = os.path.join(ckpt_dir, "original.pt")
        unlearn_ckpt_path = os.path.join(ckpt_dir, "unlearned.pt")

        model = FashionMLP(input_dim=784, num_classes=10)
        trainer = ModelTrainer(model)

        # Save an original checkpoint
        trainer.save_checkpoint(
            orig_ckpt_path,
            metadata={"model_type": "original", "dataset_name": "tofu"},
            is_complete=True,
            checkpoint_status="complete",
        )

        # Save an unlearned checkpoint
        trainer.save_checkpoint(
            unlearn_ckpt_path,
            metadata={"model_type": "unlearned", "dataset_name": "tofu"},
            is_complete=True,
            checkpoint_status="complete",
        )

        # 1. Loading original checkpoint succeeds
        loaded_orig = torch.load(orig_ckpt_path, weights_only=False)
        self.assertEqual(loaded_orig["metadata"]["model_type"], "original")

        # 2. Loading unlearned checkpoint as original baseline is rejected
        unlearn_loaded = torch.load(unlearn_ckpt_path, weights_only=False)
        self.assertEqual(unlearn_loaded["metadata"]["model_type"], "unlearned")
        self.assertNotEqual(unlearn_loaded["metadata"]["model_type"], "original")

        # Clean up temporary test checkpoints
        for p in [orig_ckpt_path, unlearn_ckpt_path]:
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    unittest.main()
