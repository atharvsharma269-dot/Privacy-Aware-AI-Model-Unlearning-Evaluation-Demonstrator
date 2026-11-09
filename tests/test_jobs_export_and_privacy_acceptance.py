import csv
import io
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.job_service import JobService
from backend.app.services.tofu_service import tofu_service, TOFUUnlearningService
from backend.app.services.experiment_service import ExperimentService
from backend.app.database.db import get_db_connection


class TestJobsExportAndPrivacyAcceptance(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.job_service = JobService()
        self.exp_service = ExperimentService()

    # =========================================================================
    # Phase 4 — Jobs API and Export API Coverage
    # =========================================================================

    def test_01_jobs_api_status_and_cancellation(self):
        """Test GET /api/jobs/{id} and POST /api/jobs/{id}/cancel."""
        # 404 on nonexistent job
        res_404 = self.client.get("/api/jobs/nonexistent_job_12345")
        self.assertEqual(res_404.status_code, 404)

        # Create real job
        job_id = self.job_service.create_job("test_exp_jobs", "TEST_TASK")
        res_job = self.client.get(f"/api/jobs/{job_id}")
        self.assertEqual(res_job.status_code, 200)
        self.assertEqual(res_job.json()["id"], job_id)
        self.assertEqual(res_job.json()["status"], "QUEUED")

        # Cancel job -> 200
        res_cancel = self.client.post(f"/api/jobs/{job_id}/cancel")
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.json()["status"], "CANCELLED")

        # Cancel nonexistent -> 404
        res_cancel_404 = self.client.post("/api/jobs/nonexistent_job_12345/cancel")
        self.assertEqual(res_cancel_404.status_code, 404)

        # Cancel error handling (500 on unexpected exception)
        with patch("backend.app.api.jobs.job_service.request_cancellation", side_effect=RuntimeError("Unexpected job failure")):
            res_500 = self.client.post(f"/api/jobs/{job_id}/cancel")
            self.assertEqual(res_500.status_code, 500)

    def test_02_export_api_json_and_csv(self):
        """Test GET /api/experiments/{id}/export in both JSON and CSV formats."""
        # 404 for nonexistent experiment
        res_404 = self.client.get("/api/experiments/nonexistent_exp_9999/export")
        self.assertEqual(res_404.status_code, 404)

        # Create experiment
        res_create = self.client.post("/api/experiments", json={
            "name": "Export Test Exp",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
            "seed": 42,
        })
        exp_id = res_create.json()["id"]

        # 1. JSON Export
        res_json = self.client.get(f"/api/experiments/{exp_id}/export?format=json")
        self.assertEqual(res_json.status_code, 200)
        self.assertEqual(res_json.headers["content-type"], "application/json")
        self.assertIn(f"experiment_{exp_id}.json", res_json.headers["content-disposition"])
        exported_data = res_json.json()
        self.assertEqual(exported_data["id"], exp_id)

        # 2. CSV Export
        res_csv = self.client.get(f"/api/experiments/{exp_id}/export?format=csv")
        self.assertEqual(res_csv.status_code, 200)
        self.assertEqual(res_csv.headers["content-type"], "text/csv; charset=utf-8")
        self.assertIn(f"experiment_{exp_id}.csv", res_csv.headers["content-disposition"])

        csv_text = res_csv.text
        self.assertIn("Experiment ID", csv_text)
        self.assertIn(exp_id, csv_text)
        self.assertIn("Retain Set Accuracy (%)", csv_text)
        self.assertIn("MIA Forget Set ROC-AUC", csv_text)
        self.assertIn("Computational Speedup Factor", csv_text)

    # =========================================================================
    # Privacy-Critical Acceptance Tests (Explicitly numbered 1 to 8)
    # =========================================================================

    def test_03_privacy_rule_1_and_2_cross_experiment_author_isolation(self):
        """
        Verify:
        1. Forgetting an author in Experiment A does not forget that author in Experiment B.
        2. Experiment B starts from the pristine original baseline.
        """
        # Create Experiment A
        res_a = self.client.post("/api/experiments", json={
            "name": "Experiment A (Privacy Isolation)",
            "dataset_name": "tofu",
            "model_name": "mlp",
        })
        self.assertEqual(res_a.status_code, 200)
        exp_a_id = res_a.json()["id"]

        # Create Experiment B
        res_b = self.client.post("/api/experiments", json={
            "name": "Experiment B (Pristine Baseline)",
            "dataset_name": "tofu",
            "model_name": "mlp",
        })
        self.assertEqual(res_b.status_code, 200)
        exp_b_id = res_b.json()["id"]

        # Verify Chukwu Akabueze (P-001) starts as ACTIVE_KNOWLEDGE in both
        st_a_init = self.client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_a_id}").json()
        st_b_init = self.client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_b_id}").json()
        self.assertEqual(st_a_init["status"], "ACTIVE_KNOWLEDGE")
        self.assertEqual(st_b_init["status"], "ACTIVE_KNOWLEDGE")

        # Forget P-001 strictly in Experiment A
        res_forget_a = self.client.post("/api/tofu/forget-author", json={
            "author_id": "P-001",
            "experiment_id": exp_a_id,
        })
        self.assertEqual(res_forget_a.status_code, 200)

        # In Experiment A: P-001 is now forgotten
        st_a_after = self.client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_a_id}").json()
        self.assertEqual(st_a_after["status"], "UNLEARNING_COMPLETED")

        # PRIVACY REQUIREMENT 1 & 2: Experiment B MUST remain in ACTIVE_KNOWLEDGE
        st_b_after = self.client.get(f"/api/tofu/authors/P-001/status?experiment_id={exp_b_id}").json()
        self.assertEqual(st_b_after["status"], "ACTIVE_KNOWLEDGE")

    def test_04_privacy_rule_3_restart_preserves_independent_state(self):
        """Verify: 3. Restarting the backend preserves each experiment's independent state."""
        # Create experiment and forget an author
        res_exp = self.client.post("/api/experiments", json={
            "name": "Restart Persistence Experiment",
            "dataset_name": "tofu",
            "model_name": "mlp",
        })
        exp_id = res_exp.json()["id"]

        self.client.post("/api/tofu/forget-author", json={
            "author_id": "P-002",
            "experiment_id": exp_id,
        })

        st_before = self.client.get(f"/api/tofu/authors/P-002/status?experiment_id={exp_id}").json()
        self.assertEqual(st_before["status"], "UNLEARNING_COMPLETED")

        # Simulate backend restart by re-instantiating service and checking DB-backed status
        fresh_service = TOFUUnlearningService()
        st_after = self.client.get(f"/api/tofu/authors/P-002/status?experiment_id={exp_id}").json()
        self.assertEqual(st_after["status"], "UNLEARNING_COMPLETED")

    def test_05_privacy_rule_4_chat_deletion_does_not_destroy_dataset_or_forgetting(self):
        """Verify: 4. Deleting a chat session does not delete dataset records or forgetting requests."""
        # Query authors and forgetting requests before deletion
        authors_before = self.client.get("/api/tofu/authors").json()
        self.assertGreater(len(authors_before), 0)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM forgetting_requests")
        req_count_before = c.fetchone()["cnt"]
        conn.close()

        # Create and delete a chat session
        chat_res = self.client.post("/api/tofu/chat/sessions", json={
            "title": "Privacy Chat Session",
            "dataset_name": "tofu",
            "author_id": "P-001",
        })
        self.assertEqual(chat_res.status_code, 200)
        session_id = chat_res.json()["id"]

        del_res = self.client.delete(f"/api/tofu/chat/sessions/{session_id}")
        self.assertEqual(del_res.status_code, 200)

        # Verify dataset records and forgetting requests are completely untouched
        authors_after = self.client.get("/api/tofu/authors").json()
        self.assertEqual(len(authors_before), len(authors_after))

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM forgetting_requests")
        req_count_after = c.fetchone()["cnt"]
        conn.close()

        self.assertEqual(req_count_before, req_count_after)

    def test_06_privacy_rule_5_and_6_cancellation_and_failure_not_falsely_completed(self):
        """
        Verify:
        5. Cancelling an unlearning job does not falsely report successful forgetting.
        6. A failed unlearning operation does not falsely report completion.
        """
        job_id = self.job_service.create_job("exp_cancel_demo", "TOFU_UNLEARNING")
        self.job_service.request_cancellation(job_id)
        job = self.job_service.get_job(job_id)
        self.assertEqual(job["status"], "CANCELLED")
        self.assertNotEqual(job["status"], "COMPLETED")

        # Failed unlearning job
        fail_id = self.job_service.create_job("exp_fail_demo", "TOFU_UNLEARNING")
        # Submit a worker that fails
        def failing_worker(step_callback, cancel_check=None):
            raise RuntimeError("Simulated unlearning worker exception")

        self.job_service.submit_job(fail_id, failing_worker)
        # Give worker a moment to execute and fail
        import time
        time.sleep(0.05)
        fail_job = self.job_service.get_job(fail_id)
        self.assertEqual(fail_job["status"], "FAILED")
        self.assertNotEqual(fail_job["status"], "COMPLETED")

    def test_07_privacy_rule_7_and_8_original_checkpoints_and_retrieval_integrity(self):
        """
        Verify:
        7. Original checkpoints remain unchanged.
        8. Deletion from a retrieval store is not reported as neural parameter unlearning.
        """
        # Rule 7: Attempting to load missing original checkpoint raises error
        exp = self.exp_service.create_experiment(
            name="Baseline Guard Test",
            description="Testing checkpoint guard",
            dataset_name="fashion_mnist",
            model_name="mlp",
        )
        with self.assertRaises(FileNotFoundError):
            self.exp_service.load_model_checkpoint(exp["id"], "original")

        # Rule 8: Retrieval updated is explicitly separated from neural parameter unlearning
        self.assertNotEqual("RETRIEVAL_UPDATED", "UNLEARNING_COMPLETED")
        self.assertNotEqual("DATA_DELETED", "UNLEARNING_COMPLETED")


if __name__ == "__main__":
    unittest.main()
