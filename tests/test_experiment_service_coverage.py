import os
import shutil
import tempfile
import unittest
import torch

from backend.app.services.experiment_service import ExperimentService
from ml.utils.exceptions import CancellationError


class TestExperimentServiceCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="test_ckpt_cov_")
        cls.service = ExperimentService(checkpoints_dir=cls.temp_dir, data_dir="./data")

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_01_create_get_list_experiment(self):
        """Test creating, fetching, and listing experiments."""
        train_config = {
            "epochs": 1,
            "batch_size": 16,
            "learning_rate": 0.001,
            "subsample_size": 30,
        }
        exp = self.service.create_experiment(
            name="Coverage Exp 1",
            description="Testing experiment service",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config=train_config,
        )
        self.assertIsNotNone(exp["id"])
        self.assertEqual(exp["status"], "CREATED")
        self.assertEqual(exp["train_config"]["subsample_size"], 30)

        # Get existing
        fetched = self.service.get_experiment(exp["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["id"], exp["id"])

        # Get nonexistent -> None
        self.assertIsNone(self.service.get_experiment("nonexistent_exp_id_999"))

        # List experiments
        all_exps = self.service.list_experiments()
        self.assertGreaterEqual(len(all_exps), 1)
        self.assertIn(exp["id"], [e["id"] for e in all_exps])

    def test_02_request_forgetting_strategies(self):
        """Test partitioning across random, class, and group strategies."""
        exp = self.service.create_experiment(
            name="Partition Test",
            description="Partitioning strategies",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config={"epochs": 1, "batch_size": 16, "subsample_size": 40},
        )
        exp_id = exp["id"]

        # Strategy 1: Random
        m_rand = self.service.request_forgetting(exp_id, strategy="random", percentage=0.25)
        self.assertEqual(m_rand["strategy"], "random")
        self.assertIn("partition_hash", m_rand)
        self.assertGreater(m_rand["forget_count"], 0)

        # Strategy 2: Class
        m_class = self.service.request_forgetting(exp_id, strategy="class", target_class=1)
        self.assertEqual(m_class["strategy"], "class")

        # Strategy 3: Group
        m_group = self.service.request_forgetting(exp_id, strategy="group", group_id=0, num_groups=5)
        self.assertEqual(m_group["strategy"], "group")

    def test_03_train_original_model_and_cancellation(self):
        """Test training original model, callbacks, checkpointing, and cancellation handling."""
        exp = self.service.create_experiment(
            name="Train Original Test",
            description="Testing training pipeline",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config={"epochs": 1, "batch_size": 16, "subsample_size": 30},
        )
        exp_id = exp["id"]

        telemetry_events = []

        def callback(event):
            telemetry_events.append(event)

        # Successful training
        res = self.service.train_original_model(
            exp_id=exp_id,
            step_callback=callback,
        )
        self.assertIn("final_test_loss", res)
        self.assertIn("final_test_accuracy", res)
        self.assertGreater(len(telemetry_events), 0)

        # Check DB status
        updated_exp = self.service.get_experiment(exp_id)
        self.assertEqual(updated_exp["status"], "ORIGINAL_TRAINED")
        self.assertTrue(os.path.exists(updated_exp["original_checkpoint_path"]))

        # Verify load_model_checkpoint works for original
        model, meta = self.service.load_model_checkpoint(exp_id, "original")
        self.assertIsNotNone(model)
        self.assertEqual(meta.get("model_type"), "original")

        # Test cancellation handling
        exp_cancel = self.service.create_experiment(
            name="Train Cancel Test",
            description="Testing train cancellation",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config={"epochs": 1, "batch_size": 16, "subsample_size": 30},
        )
        with self.assertRaises(CancellationError):
            self.service.train_original_model(
                exp_id=exp_cancel["id"],
                cancel_check=lambda: True,
            )

    def test_04_full_lifecycle_retrain_unlearn_evaluate(self):
        """Test complete end-to-end pipeline: partition -> retrain -> unlearn -> evaluate."""
        exp = self.service.create_experiment(
            name="Lifecycle Full Test",
            description="Testing full pipeline",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config={"epochs": 1, "batch_size": 16, "subsample_size": 30},
        )
        exp_id = exp["id"]

        # 1. Train original
        self.service.train_original_model(exp_id)

        # 2. Partition
        self.service.request_forgetting(exp_id, strategy="random", percentage=0.20)

        # 3. Retrain Golden Reference
        retrain_res = self.service.train_retrained_model(exp_id)
        self.assertIn("final_test_accuracy", retrain_res)
        updated_exp = self.service.get_experiment(exp_id)
        self.assertEqual(updated_exp["status"], "RETRAINED")

        # 4. Unlearn (Retain fine-tuning)
        unlearn_res = self.service.run_unlearning(
            exp_id=exp_id,
            algorithm="retain_fine_tuning",
            epochs=1,
            batch_size=16,
        )
        self.assertIsNotNone(unlearn_res)
        updated_exp = self.service.get_experiment(exp_id)
        self.assertEqual(updated_exp["status"], "READY_FOR_EVALUATION")

        # 5. Evaluate all 3 models
        eval_events = []
        eval_res = self.service.evaluate_experiment(
            exp_id=exp_id,
            step_callback=lambda ev: eval_events.append(ev),
        )
        self.assertIn("original_model", eval_res)
        self.assertIn("unlearned_model", eval_res)
        self.assertIn("retrained_model", eval_res)
        self.assertIn("behavioral_similarity", eval_res)
        self.assertIn("mia", eval_res)
        self.assertTrue(eval_res["has_retrained_reference"])
        self.assertGreater(len(eval_events), 0)

        # Verify DB status is EVALUATED and insights exist
        final_exp = self.service.get_experiment(exp_id)
        self.assertEqual(final_exp["status"], "EVALUATED")
        self.assertIsNotNone(final_exp["insights"])
        self.assertIn("forgetting_effectiveness", final_exp["insights"])

        # 6. Unlearn with gradient_ascent
        ga_res = self.service.run_unlearning(
            exp_id=exp_id,
            algorithm="gradient_ascent",
            epochs=1,
            batch_size=16,
        )
        self.assertIsNotNone(ga_res)

    def test_05_checkpoint_validation_and_integrity(self):
        """Test checkpoint integrity validations and error handling."""
        # Non-existent exp ID
        with self.assertRaises(ValueError):
            self.service.load_model_checkpoint("non_existent_exp_xyz", "original")

        # Missing checkpoint
        exp = self.service.create_experiment(
            name="Empty Exp",
            description="No checkpoints yet",
            dataset_name="fashion_mnist",
            model_name="mlp",
        )
        with self.assertRaises(FileNotFoundError):
            self.service.load_model_checkpoint(exp["id"], "original")

        # Missing original checkpoint when unlearning
        with self.assertRaises(ValueError):
            self.service.run_unlearning(exp["id"])

        # Missing partition when retraining
        with self.assertRaises(ValueError):
            self.service.train_retrained_model(exp["id"])

        # Missing checkpoints when evaluating
        with self.assertRaises(ValueError):
            self.service.evaluate_experiment(exp["id"])

    def test_06_cancellation_during_retrain_and_unlearn(self):
        """Test cancellation handling for retraining and unlearning routines."""
        exp = self.service.create_experiment(
            name="Cancel Retrain/Unlearn Test",
            description="Testing cancel checks",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=42,
            train_config={"epochs": 1, "batch_size": 16, "subsample_size": 30},
        )
        exp_id = exp["id"]
        self.service.train_original_model(exp_id)
        self.service.request_forgetting(exp_id, strategy="random", percentage=0.20)

        # Cancel retraining
        with self.assertRaises(CancellationError):
            self.service.train_retrained_model(exp_id, cancel_check=lambda: True)

        # Cancel unlearning
        with self.assertRaises(CancellationError):
            self.service.run_unlearning(exp_id, cancel_check=lambda: True)


if __name__ == "__main__":
    unittest.main()
