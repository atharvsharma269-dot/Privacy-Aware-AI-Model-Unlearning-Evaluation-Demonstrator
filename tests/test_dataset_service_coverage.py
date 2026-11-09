import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.dataset_service import DatasetService


class TestDatasetServiceCoverage(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.service = DatasetService(data_dir="./data")

    def test_01_dataset_service_get_raw_datasets(self):
        """Test loading raw datasets and cache population."""
        train_ds, test_ds, classes = self.service.get_raw_datasets("fashion_mnist")
        self.assertIsNotNone(train_ds)
        self.assertIsNotNone(test_ds)
        self.assertEqual(len(classes), 10)
        self.assertIn("fashion_mnist", self.service._cache)

        # Cache hit
        train_ds_2, test_ds_2, classes_2 = self.service.get_raw_datasets("fashion_mnist")
        self.assertIs(train_ds, train_ds_2)
        self.assertIs(test_ds, test_ds_2)

    def test_02_dataset_service_summary(self):
        """Test get_summary for image dataset."""
        summary = self.service.get_summary("fashion_mnist")
        self.assertEqual(summary["name"], "fashion_mnist")
        self.assertGreater(summary["total_train"], 0)
        self.assertGreater(summary["total_test"], 0)
        self.assertEqual(summary["num_classes"], 10)
        self.assertEqual(len(summary["classes"]), 10)
        self.assertIn("class_distribution_train", summary)
        self.assertEqual(len(summary["class_distribution_train"]), 10)

    def test_03_dataset_service_get_samples_fashion_mnist(self):
        """Test image dataset samples retrieval with various parameters."""
        # Train split, offset 0, limit 4
        samples_train = self.service.get_samples(
            dataset_name="fashion_mnist",
            split="train",
            offset=0,
            limit=4,
        )
        self.assertEqual(len(samples_train), 4)
        for s in samples_train:
            self.assertIn("index", s)
            self.assertIn("label", s)
            self.assertIn("class_name", s)
            self.assertTrue(s["image_base64"].startswith("data:image/png;base64,"))

        # Test split, offset 10, limit 3
        samples_test = self.service.get_samples(
            dataset_name="fashion_mnist",
            split="test",
            offset=10,
            limit=3,
        )
        self.assertEqual(len(samples_test), 3)

        # Filter by class
        target_class = 2
        filtered_samples = self.service.get_samples(
            dataset_name="fashion_mnist",
            split="train",
            offset=0,
            limit=5,
            class_filter=target_class,
        )
        self.assertLessEqual(len(filtered_samples), 5)
        for s in filtered_samples:
            self.assertEqual(s["label"], target_class)

    def test_04_dataset_service_get_samples_tofu(self):
        """Test TOFU dataset samples retrieval including class filter."""
        samples_tofu = self.service.get_samples(
            dataset_name="tofu",
            split="train",
            offset=0,
            limit=5,
        )
        self.assertEqual(len(samples_tofu), 5)
        for s in samples_tofu:
            self.assertIn("index", s)
            self.assertIn("label", s)
            self.assertIn("class_name", s)
            self.assertIn("question", s)
            self.assertIn("answer", s)
            self.assertIn("author_id", s)
            self.assertTrue(s["image_base64"].startswith("data:image/png;base64,"))

        # TOFU test split
        samples_tofu_test = self.service.get_samples(
            dataset_name="tofu",
            split="test",
            offset=0,
            limit=3,
        )
        self.assertEqual(len(samples_tofu_test), 3)

        # TOFU with class_filter
        filtered_tofu = self.service.get_samples(
            dataset_name="tofu",
            split="train",
            offset=0,
            limit=3,
            class_filter=0,
        )
        for s in filtered_tofu:
            self.assertEqual(s["label"], 0)

        # TOFU with non-matching first element to trigger filter continue
        filtered_tofu_skip = self.service.get_samples(
            dataset_name="tofu",
            split="train",
            offset=0,
            limit=2,
            class_filter=9,
        )
        for s in filtered_tofu_skip:
            self.assertEqual(s["label"], 9)

    def test_05_dataset_service_error_handling(self):
        """Test error handling when underlying dataset loading fails or is corrupt."""
        with patch("backend.app.services.dataset_service.load_raw_dataset", side_effect=FileNotFoundError("Corrupted dataset archive")):
            svc = DatasetService(data_dir="./nonexistent_data")
            with self.assertRaises(FileNotFoundError):
                svc.get_raw_datasets("corrupted_dataset")

            with self.assertRaises(FileNotFoundError):
                svc.get_summary("corrupted_dataset")

            with self.assertRaises(FileNotFoundError):
                svc.get_samples("corrupted_dataset")

    def test_06_dataset_api_endpoints(self):
        """Test API endpoints in backend/app/api/datasets.py."""
        # List datasets
        res_list = self.client.get("/api/datasets")
        self.assertEqual(res_list.status_code, 200)
        data = res_list.json()
        self.assertGreaterEqual(len(data), 2)
        dataset_ids = [d["id"] for d in data]
        self.assertIn("fashion_mnist", dataset_ids)
        self.assertIn("tofu", dataset_ids)

        # Summary valid
        res_summary = self.client.get("/api/datasets/fashion_mnist/summary")
        self.assertEqual(res_summary.status_code, 200)
        summary = res_summary.json()
        self.assertEqual(summary["name"], "fashion_mnist")

        # Summary error handling -> 400
        with patch("backend.app.api.datasets.dataset_service.get_summary", side_effect=ValueError("Dataset loading error")):
            res_summary_err = self.client.get("/api/datasets/fashion_mnist/summary")
            self.assertEqual(res_summary_err.status_code, 400)
            self.assertIn("Dataset loading error", res_summary_err.json()["detail"])

        # Samples valid fashion_mnist
        res_samples = self.client.get("/api/datasets/fashion_mnist/samples?split=train&offset=0&limit=4")
        self.assertEqual(res_samples.status_code, 200)
        samples_data = res_samples.json()
        self.assertEqual(samples_data["dataset_id"], "fashion_mnist")
        self.assertEqual(len(samples_data["samples"]), 4)

        # Samples valid tofu
        res_tofu_samples = self.client.get("/api/datasets/tofu/samples?split=train&offset=0&limit=3")
        self.assertEqual(res_tofu_samples.status_code, 200)
        tofu_data = res_tofu_samples.json()
        self.assertEqual(tofu_data["dataset_id"], "tofu")
        self.assertEqual(len(tofu_data["samples"]), 3)

        # Samples error handling -> 400
        with patch("backend.app.api.datasets.dataset_service.get_samples", side_effect=RuntimeError("Data corrupted")):
            res_samples_err = self.client.get("/api/datasets/fashion_mnist/samples")
            self.assertEqual(res_samples_err.status_code, 400)
            self.assertIn("Data corrupted", res_samples_err.json()["detail"])

        # Samples validation error (limit > 100) -> 422
        res_val_err = self.client.get("/api/datasets/fashion_mnist/samples?limit=500")
        self.assertEqual(res_val_err.status_code, 422)


if __name__ == "__main__":
    unittest.main()
