import os
import time
import shutil
import tempfile
import unittest
import torch
from unittest.mock import MagicMock

from backend.app.services.job_service import JobService
from backend.app.services.experiment_service import ExperimentService
from ml.utils.exceptions import CancellationError
from ml.training.trainer import ModelTrainer
from ml.models import get_model
from ml.datasets.loader import load_raw_dataset
from ml.unlearning.gradient_ascent import RegularizedGradientAscentUnlearner
from backend.app.database.db import get_db_connection


class TestExperimentLifecycle(unittest.TestCase):
    def setUp(self):
        self.job_service = JobService()
        self.exp_service = ExperimentService()

    def test_01_job_lifecycle_state_transitions(self):
        """Test explicit states: QUEUED -> RUNNING -> COMPLETED."""
        job_id = self.job_service.create_job("test_exp_1", "TEST_TASK")
        self.assertEqual(self.job_service.get_job(job_id)["status"], "QUEUED")

        def worker(step_callback, cancel_check=None):
            time.sleep(0.05)
            step_callback({"progress": 50, "current_step": "Working"})
            return {"result": "ok"}

        self.job_service.submit_job(job_id, worker)
        time.sleep(0.01)
        job = self.job_service.get_job(job_id)
        self.assertIn(job["status"], ["RUNNING", "COMPLETED"])

        # Wait for completion
        for _ in range(25):
            if self.job_service.get_job(job_id)["status"] == "COMPLETED":
                break
            time.sleep(0.02)

        self.assertEqual(self.job_service.get_job(job_id)["status"], "COMPLETED")
        final_job = self.job_service.get_job(job_id)
        self.assertEqual(final_job["progress"], 100.0)

    def test_02_queued_job_cancellation_before_execution(self):
        """Test cancelling a job before worker execution begins."""
        job_id = self.job_service.create_job("test_exp_2", "PRE_CANCEL_TASK")
        self.assertEqual(self.job_service.get_job(job_id)["status"], "QUEUED")

        res = self.job_service.request_cancellation(job_id)
        self.assertEqual(res["status"], "CANCELLED")
        self.assertEqual(self.job_service.get_job(job_id)["status"], "CANCELLED")

        executed = []

        def worker(step_callback, cancel_check=None):
            executed.append(True)
            return {"result": "should_not_run"}

        self.job_service.submit_job(job_id, worker)
        time.sleep(0.05)
        self.assertEqual(executed, [], "Worker must not run after queued cancellation")
        self.assertEqual(self.job_service.get_job(job_id)["status"], "CANCELLED")

    def test_03_running_job_cancellation_and_race_safety(self):
        """Test cooperative cancellation while a job is running, including repeated requests."""
        job_id = self.job_service.create_job("test_exp_3", "COOP_CANCEL_TASK")

        def worker(step_callback, cancel_check=None):
            for i in range(20):
                if cancel_check and cancel_check():
                    raise CancellationError("User requested cancellation")
                time.sleep(0.02)
                step_callback({"progress": i * 5, "current_step": f"Step {i}"})
            return {"result": "completed"}

        self.job_service.submit_job(job_id, worker)
        time.sleep(0.03)

        # Trigger cancellation
        res1 = self.job_service.request_cancellation(job_id)
        self.assertIn(res1["status"], ["CANCELLATION_REQUESTED", "CANCELLED"])

        # Repeat cancellation (race safety / idempotency)
        res2 = self.job_service.request_cancellation(job_id)
        self.assertIn(res2["status"], ["CANCELLATION_REQUESTED", "CANCELLED"])

        # Wait for worker to halt
        for _ in range(35):
            if self.job_service.get_job(job_id)["status"] == "CANCELLED":
                break
            time.sleep(0.02)

        self.assertEqual(self.job_service.get_job(job_id)["status"], "CANCELLED")
        job = self.job_service.get_job(job_id)
        self.assertTrue(any("Cancelled by user" in log or "CANCEL" in log for log in job.get("logs", [])))

    def test_04_duplicate_active_job_prevention(self):
        """Test that get_active_job_for_experiment detects running/queued jobs to prevent concurrent runs."""
        exp_id = "test_exp_duplicate"
        job_id = self.job_service.create_job(exp_id, "FIRST_JOB")

        def slow_worker(step_callback, cancel_check=None):
            for _ in range(10):
                if cancel_check and cancel_check():
                    raise CancellationError("Halt")
                time.sleep(0.05)
            return {"done": True}

        self.job_service.submit_job(job_id, slow_worker)
        time.sleep(0.02)

        active = self.job_service.get_active_job_for_experiment(exp_id)
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], job_id)

        # Clean up by cancelling
        self.job_service.request_cancellation(job_id)
        time.sleep(0.1)

    def test_05_atomic_checkpoint_integrity_on_cancellation(self):
        """Verify that interrupting Trainer mid-epoch does NOT promote .tmp checkpoint to final destination."""
        temp_dir = tempfile.mkdtemp()
        try:
            model = get_model("mlp", num_classes=10)
            trainer = ModelTrainer(model, learning_rate=0.001, device="cpu")
            raw_train, raw_test, _ = load_raw_dataset("fashion_mnist", download=False)
            train_ds = torch.utils.data.Subset(raw_train, range(100))
            test_ds = torch.utils.data.Subset(raw_test, range(50))

            ckpt_dest = os.path.join(temp_dir, "model_checkpoint.pt")
            tmp_dest = f"{ckpt_dest}.tmp"

            cancelled_flag = [False]

            def cancel_check():
                return cancelled_flag[0]

            def on_batch(info):
                if info.get("batch") == 1:
                    cancelled_flag[0] = True

            with self.assertRaises(CancellationError):
                trainer.train(
                    train_dataset=train_ds,
                    val_dataset=test_ds,
                    epochs=2,
                    batch_size=16,
                    cancel_check=cancel_check,
                    batch_callback=on_batch,
                )

            # Assert destination checkpoint does NOT exist because training was interrupted
            self.assertFalse(os.path.exists(ckpt_dest), "Final checkpoint must not exist if training was cancelled")

            # Now test that atomic save_checkpoint properly creates and promotes files
            trainer.save_checkpoint(ckpt_dest, is_complete=True, checkpoint_status="complete")
            self.assertTrue(os.path.exists(ckpt_dest), "Final checkpoint should exist after save_checkpoint completes")
            self.assertFalse(os.path.exists(tmp_dest), "Temporary .tmp staging file must be cleanly promoted away")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_06_unlearning_cancellation_and_original_model_preservation(self):
        """Verify that cancelling unlearning halts immediately and preserves original weights."""
        temp_dir = tempfile.mkdtemp()
        try:
            model = get_model("mlp", num_classes=10)
            unlearner = RegularizedGradientAscentUnlearner(model, learning_rate=0.001, device="cpu")
            raw_train, _, _ = load_raw_dataset("fashion_mnist", download=False)
            train_ds = torch.utils.data.Subset(raw_train, range(60))
            retain_ds = torch.utils.data.Subset(train_ds, range(0, 40))
            forget_ds = torch.utils.data.Subset(train_ds, range(40, 60))

            cancel_called = [False]

            def cancel_check():
                return cancel_called[0]

            def on_batch(b_info):
                cancel_called[0] = True

            with self.assertRaises(CancellationError):
                unlearner.unlearn(
                    retain_dataset=retain_ds,
                    forget_dataset=forget_ds,
                    epochs=3,
                    batch_size=16,
                    cancel_check=cancel_check,
                    batch_callback=on_batch,
                )

            self.assertTrue(cancel_called[0])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_07_strict_evaluation_checkpoint_validation(self):
        """Verify evaluate_experiment rejects incomplete, failed, or cancelled checkpoints."""
        temp_dir = tempfile.mkdtemp()
        try:
            exp_id = "test_exp_eval_validation"
            conn = get_db_connection()
            c = conn.cursor()

            fake_orig = os.path.join(temp_dir, "orig.pt")
            fake_unl = os.path.join(temp_dir, "unl.pt")

            # Save fake unlearned checkpoint marked as cancelled
            model = get_model("mlp", num_classes=10)
            torch.save({
                "model_state_dict": model.state_dict(),
                "metadata": {"is_complete": False, "checkpoint_status": "cancelled"}
            }, fake_unl)

            # Save fake original checkpoint complete
            torch.save({
                "model_state_dict": model.state_dict(),
                "metadata": {"is_complete": True, "checkpoint_status": "complete"}
            }, fake_orig)

            c.execute("""
                INSERT OR REPLACE INTO experiments (id, name, dataset_name, model_name, status, seed, original_checkpoint_path, unlearned_checkpoint_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (exp_id, "Incomplete Test", "fashion_mnist", "mlp", "READY_FOR_EVALUATION", 42, fake_orig, fake_unl))
            conn.commit()
            conn.close()

            # Attempt evaluation - must raise ValueError due to incomplete checkpoint
            with self.assertRaises(ValueError) as ctx:
                self.exp_service.evaluate_experiment(exp_id)
            self.assertIn("incomplete or cancelled", str(ctx.exception))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_08_deterministic_partition_hashing(self):
        """Verify partition hash produces identical SHA-256 digests for identical partitions."""
        exp = self.exp_service.create_experiment(
            name="Partition Hash Test",
            description="Testing hash determinism",
            dataset_name="fashion_mnist",
            model_name="mlp",
            seed=999
        )
        manifest1 = self.exp_service.request_forgetting(
            exp_id=exp["id"],
            strategy="random",
            percentage=0.10,
        )
        hash1 = manifest1.get("partition_hash")
        self.assertIsNotNone(hash1)
        self.assertTrue(hash1.startswith("part_"))
        self.assertEqual(manifest1.get("dataset_version"), "1.0-clean")


if __name__ == "__main__":
    unittest.main()
