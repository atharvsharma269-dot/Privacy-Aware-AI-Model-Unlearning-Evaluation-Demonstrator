import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.app.main import app


class TestExperimentAPICoverage(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_create_get_list_experiment_endpoints(self):
        """Test POST /api/experiments, GET /api/experiments, GET /api/experiments/{id}."""
        # 1. Valid Creation
        payload = {
            "name": "API Exp Valid",
            "description": "Coverage test",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
            "seed": 42,
            "train_config": {
                "epochs": 1,
                "batch_size": 16,
                "learning_rate": 0.001,
                "subsample_size": 30,
            },
        }
        res = self.client.post("/api/experiments", json=payload)
        self.assertEqual(res.status_code, 200)
        exp_data = res.json()
        exp_id = exp_data["id"]

        # 2. Invalid Payload -> 422
        res_invalid = self.client.post("/api/experiments", json={"seed": "not-an-int"})
        self.assertEqual(res_invalid.status_code, 422)

        # 3. Service Error Simulation -> 400
        with patch("backend.app.api.experiments.exp_service.create_experiment", side_effect=ValueError("Database error")):
            res_err = self.client.post("/api/experiments", json=payload)
            self.assertEqual(res_err.status_code, 400)
            self.assertIn("Database error", res_err.json()["detail"])

        # 4. List Experiments
        res_list = self.client.get("/api/experiments")
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(any(e["id"] == exp_id for e in res_list.json()))

        # 5. Get Experiment (Valid and 404)
        res_get = self.client.get(f"/api/experiments/{exp_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], exp_id)

        res_404 = self.client.get("/api/experiments/nonexistent_exp_9999")
        self.assertEqual(res_404.status_code, 404)

    def test_02_train_original_endpoint(self):
        """Test POST /api/experiments/{id}/train including 404 and 409 conflict."""
        # Nonexistent -> 404
        res_404 = self.client.post("/api/experiments/nonexistent_exp_9999/train")
        self.assertEqual(res_404.status_code, 404)

        # Create experiment
        res_create = self.client.post("/api/experiments", json={
            "name": "Train Endpoint Exp",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
            "seed": 42,
        })
        exp_id = res_create.json()["id"]

        # 409 Conflict Simulation (Active job already running)
        with patch("backend.app.api.experiments.job_service.get_active_job_for_experiment", return_value={"id": "job_123", "job_type": "TRAIN", "status": "RUNNING"}):
            res_409 = self.client.post(f"/api/experiments/{exp_id}/train")
            self.assertEqual(res_409.status_code, 409)

        # Successful trigger
        with patch("backend.app.api.experiments.job_service.submit_job") as mock_submit:
            res_train = self.client.post(f"/api/experiments/{exp_id}/train", json={"epochs": 1, "batch_size": 16})
            self.assertEqual(res_train.status_code, 200)
            self.assertIn("job_id", res_train.json())
            self.assertTrue(mock_submit.called)

    def test_03_forget_endpoint(self):
        """Test POST /api/experiments/{id}/forget including 404 and error handling."""
        # Nonexistent -> 404
        res_404 = self.client.post("/api/experiments/nonexistent_exp_9999/forget", json={"strategy": "random", "percentage": 0.1})
        self.assertEqual(res_404.status_code, 404)

        # Create experiment
        res_create = self.client.post("/api/experiments", json={
            "name": "Forget Endpoint Exp",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
            "seed": 42,
        })
        exp_id = res_create.json()["id"]

        # Valid forget request
        res_forget = self.client.post(f"/api/experiments/{exp_id}/forget", json={"strategy": "random", "percentage": 0.2})
        self.assertEqual(res_forget.status_code, 200)
        self.assertEqual(res_forget.json()["strategy"], "random")

        # Service exception -> 400
        with patch("backend.app.api.experiments.exp_service.request_forgetting", side_effect=ValueError("Invalid partition strategy")):
            res_err = self.client.post(f"/api/experiments/{exp_id}/forget", json={"strategy": "random"})
            self.assertEqual(res_err.status_code, 400)

    def test_04_retrain_endpoint(self):
        """Test POST /api/experiments/{id}/retrain including 404, 400 missing partition, and 409."""
        # Nonexistent -> 404
        res_404 = self.client.post("/api/experiments/nonexistent_exp_9999/retrain")
        self.assertEqual(res_404.status_code, 404)

        # Create experiment without partition
        res_create = self.client.post("/api/experiments", json={
            "name": "Retrain Endpoint Exp",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
        })
        exp_id = res_create.json()["id"]

        # Missing partition -> 400
        res_no_part = self.client.post(f"/api/experiments/{exp_id}/retrain")
        self.assertEqual(res_no_part.status_code, 400)

        # Partition it
        self.client.post(f"/api/experiments/{exp_id}/forget", json={"strategy": "random", "percentage": 0.1})

        # Conflict 409
        with patch("backend.app.api.experiments.job_service.get_active_job_for_experiment", return_value={"id": "job_active", "job_type": "RETRAIN", "status": "RUNNING"}):
            res_409 = self.client.post(f"/api/experiments/{exp_id}/retrain")
            self.assertEqual(res_409.status_code, 409)

        # Success
        with patch("backend.app.api.experiments.job_service.submit_job") as mock_submit:
            res_retrain = self.client.post(f"/api/experiments/{exp_id}/retrain")
            self.assertEqual(res_retrain.status_code, 200)
            self.assertIn("job_id", res_retrain.json())
            self.assertTrue(mock_submit.called)

    def test_05_unlearn_endpoint(self):
        """Test POST /api/experiments/{id}/unlearn including 404, 400 missing prerequisites, and 409."""
        # Nonexistent -> 404
        res_404 = self.client.post("/api/experiments/nonexistent_exp_9999/unlearn", json={"algorithm": "retain_fine_tuning"})
        self.assertEqual(res_404.status_code, 404)

        # Create experiment
        res_create = self.client.post("/api/experiments", json={
            "name": "Unlearn Endpoint Exp",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
        })
        exp_id = res_create.json()["id"]

        # Missing checkpoint or partition -> 400
        res_no_prereq = self.client.post(f"/api/experiments/{exp_id}/unlearn", json={"algorithm": "retain_fine_tuning"})
        self.assertEqual(res_no_prereq.status_code, 400)

        # Mock prerequisites met
        mock_exp = {
            "id": exp_id,
            "status": "PARTITIONED",
            "original_checkpoint_path": "fake/original.pt",
            "partition_manifest": {"strategy": "random"},
        }
        with patch("backend.app.api.experiments.exp_service.get_experiment", return_value=mock_exp):
            with patch("os.path.exists", return_value=True):
                # 409 conflict
                with patch("backend.app.api.experiments.job_service.get_active_job_for_experiment", return_value={"id": "job_u", "job_type": "UNLEARN", "status": "RUNNING"}):
                    res_409 = self.client.post(f"/api/experiments/{exp_id}/unlearn", json={"algorithm": "retain_fine_tuning"})
                    self.assertEqual(res_409.status_code, 409)

                # Success
                with patch("backend.app.api.experiments.job_service.get_active_job_for_experiment", return_value=None):
                    with patch("backend.app.api.experiments.job_service.submit_job") as mock_submit:
                        res_unlearn = self.client.post(f"/api/experiments/{exp_id}/unlearn", json={"algorithm": "retain_fine_tuning"})
                        self.assertEqual(res_unlearn.status_code, 200)
                        self.assertIn("job_id", res_unlearn.json())

    def test_06_evaluate_and_cancel_endpoints(self):
        """Test POST /api/experiments/{id}/evaluate and POST /api/experiments/{id}/cancel."""
        # Evaluate 404
        res_404 = self.client.post("/api/experiments/nonexistent_exp_9999/evaluate")
        self.assertEqual(res_404.status_code, 404)

        # Create experiment and trigger evaluation -> 200 with job_id
        res_create = self.client.post("/api/experiments", json={"name": "Eval Exp", "dataset_name": "fashion_mnist", "model_name": "mlp"})
        exp_id = res_create.json()["id"]

        with patch("backend.app.api.experiments.job_service.submit_job") as mock_submit:
            res_eval = self.client.post(f"/api/experiments/{exp_id}/evaluate")
            self.assertEqual(res_eval.status_code, 200)
            self.assertIn("job_id", res_eval.json())
            self.assertEqual(res_eval.json()["status"], "QUEUED")

        # 409 conflict when active job already running
        with patch("backend.app.api.experiments.job_service.get_active_job_for_experiment", return_value={"id": "job_eval", "job_type": "EVALUATE_ALL", "status": "RUNNING"}):
            res_409 = self.client.post(f"/api/experiments/{exp_id}/evaluate")
            self.assertEqual(res_409.status_code, 409)

        # Cancel 404 nonexistent experiment
        res_cancel_404 = self.client.post("/api/experiments/nonexistent_exp_9999/cancel")
        self.assertEqual(res_cancel_404.status_code, 404)

        # Cancel 404 on an experiment with no active job
        res_exp_idle = self.client.post("/api/experiments", json={"name": "Idle Exp", "dataset_name": "fashion_mnist", "model_name": "mlp"})
        idle_exp_id = res_exp_idle.json()["id"]
        res_cancel_no_job = self.client.post(f"/api/experiments/{idle_exp_id}/cancel")
        self.assertEqual(res_cancel_no_job.status_code, 404)

        # Cancel success on the experiment with the active evaluation job
        res_cancel = self.client.post(f"/api/experiments/{exp_id}/cancel")
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.json()["status"], "CANCELLED")

    def test_07_benchmark_arena_and_metadata_endpoints(self):
        """Test GET /api/experiments/benchmark/arena, GET /metrics, and GET /checkpoint."""
        # Arena endpoint
        res_arena = self.client.get("/api/experiments/benchmark/arena")
        self.assertEqual(res_arena.status_code, 200)
        arena_data = res_arena.json()
        self.assertIn("methods", arena_data)
        self.assertIn("seeds", arena_data)

        # Metrics 404
        res_m404 = self.client.get("/api/experiments/nonexistent_9999/metrics")
        self.assertEqual(res_m404.status_code, 404)

        # Metrics valid
        res_create = self.client.post("/api/experiments", json={"name": "Metrics Exp", "dataset_name": "fashion_mnist", "model_name": "mlp"})
        exp_id = res_create.json()["id"]
        res_m = self.client.get(f"/api/experiments/{exp_id}/metrics")
        self.assertEqual(res_m.status_code, 200)
        self.assertEqual(res_m.json()["experiment_id"], exp_id)

        # Checkpoint endpoint: 404 missing, 400 ValueError, 200 verified
        res_ckpt_404 = self.client.get(f"/api/experiments/{exp_id}/checkpoint/original")
        self.assertEqual(res_ckpt_404.status_code, 404)

        with patch("backend.app.api.experiments.exp_service.load_model_checkpoint", side_effect=ValueError("Model type mismatch")):
            res_ckpt_err = self.client.get(f"/api/experiments/{exp_id}/checkpoint/original")
            self.assertEqual(res_ckpt_err.status_code, 400)

        with patch("backend.app.api.experiments.exp_service.load_model_checkpoint", return_value=(MagicMock(), {"model_type": "original", "epochs": 1})):
            res_ckpt_ok = self.client.get(f"/api/experiments/{exp_id}/checkpoint/original")
            self.assertEqual(res_ckpt_ok.status_code, 200)
            self.assertTrue(res_ckpt_ok.json()["verified"])


if __name__ == "__main__":
    unittest.main()
