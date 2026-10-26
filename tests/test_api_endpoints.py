import unittest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_health_and_root(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)

        res_h = self.client.get("/api/health")
        self.assertEqual(res_h.status_code, 200)
        self.assertEqual(res_h.json()["status"], "healthy")
        self.assertIn("hardware", res_h.json())

    def test_02_datasets_list(self):
        res = self.client.get("/api/datasets")
        self.assertEqual(res.status_code, 200)
        datasets = res.json()
        ids = [d["id"] for d in datasets]
        self.assertIn("fashion_mnist", ids)

    def test_03_create_and_fetch_experiment(self):
        payload = {
            "name": "Integration Test Experiment",
            "description": "Validating end-to-end API lifecycle",
            "dataset_name": "fashion_mnist",
            "model_name": "mlp",
            "seed": 123,
            "train_config": {
                "epochs": 2,
                "batch_size": 32,
                "learning_rate": 0.001,
                "subsample_size": 500,
            }
        }
        res = self.client.post("/api/experiments", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        exp_id = data["id"]
        self.assertEqual(data["name"], "Integration Test Experiment")

        # Fetch experiment
        res_get = self.client.get(f"/api/experiments/{exp_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], exp_id)

        # Test forgetting request
        forget_payload = {
            "strategy": "random",
            "percentage": 0.10,
        }
        res_forget = self.client.post(f"/api/experiments/{exp_id}/forget", json=forget_payload)
        self.assertEqual(res_forget.status_code, 200)
        manifest = res_forget.json()
        self.assertEqual(manifest["strategy"], "random")
        self.assertGreater(manifest["forget_count"], 0)

        # Test export
        res_export = self.client.get(f"/api/experiments/{exp_id}/export?format=json")
        self.assertEqual(res_export.status_code, 200)


if __name__ == "__main__":
    unittest.main()

