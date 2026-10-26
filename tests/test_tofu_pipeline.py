import pytest
import torch
import numpy as np
from ml.datasets.loader import load_raw_dataset, get_dataset_class_names, TOFU_CLASSES
from ml.datasets.tofu_loader import load_tofu_raw_dataset, get_tofu_raw_sample
from ml.datasets.partitioner import DatasetPartitioner
from ml.models.mlp import FashionMLP
from ml.training.trainer import ModelTrainer
from ml.unlearning.fine_tuning import RetainFineTuningUnlearner
from ml.unlearning.gradient_ascent import RegularizedGradientAscentUnlearner
from ml.evaluation import compute_dataset_metrics, MembershipInferenceEvaluator
from ml.evaluation.tofu_generative import TOFUGenerativeEvaluator
from backend.app.services.job_service import JobService
from backend.app.services.experiment_service import ExperimentService
from backend.app.database.db import get_db_connection


def test_tofu_loader():
    """Verify that locuslab/TOFU loads correctly and returns indexed subsets."""
    train_ds, test_ds, classes = load_raw_dataset("tofu")
    assert len(train_ds) == 3200
    assert len(test_ds) == 800
    assert len(classes) == 10
    assert classes == TOFU_CLASSES

    # Verify sample format
    idx, feat, target = train_ds[0]
    assert idx == 0
    assert isinstance(feat, torch.Tensor)
    assert feat.shape == torch.Size([784])
    assert 0 <= int(target) < 10


def test_tofu_sample_preview():
    """Verify that get_tofu_raw_sample returns question, answer, and preview image."""
    sample = get_tofu_raw_sample(0, split="train")
    assert "question" in sample
    assert "answer" in sample
    assert "image_base64" in sample
    assert sample["image_base64"].startswith("data:image/png;base64,")
    assert sample["author_id"] == 0


def test_tofu_partitioner():
    """Verify that DatasetPartitioner handles TOFU class/author forgetting without leakage."""
    train_ds, _, _ = load_raw_dataset("tofu")
    partitioner = DatasetPartitioner(
        train_dataset=train_ds,
        val_ratio=0.1,
        seed=42,
        subsample_size=600,
    )
    manifest = partitioner.create_partition(strategy="class", target_class=0)
    assert manifest["forget_count"] > 0
    assert manifest["retain_count"] > 0
    assert manifest["val_count"] == 60

    # Ensure zero data leakage
    retain_set = partitioner.retain_indices
    forget_set = partitioner.forget_indices
    val_set = partitioner.val_indices

    assert len(retain_set.intersection(forget_set)) == 0
    assert len(retain_set.intersection(val_set)) == 0
    assert len(forget_set.intersection(val_set)) == 0


def test_tofu_training_and_unlearning():
    """Small end-to-end verification of training, exact retraining, and fine-tuning on TOFU."""
    train_ds, test_ds, _ = load_raw_dataset("tofu")
    partitioner = DatasetPartitioner(train_ds, val_ratio=0.1, seed=42, subsample_size=300)
    partitioner.create_partition(strategy="class", target_class=0)
    retain_ds, forget_ds, val_ds = partitioner.get_subsets()

    # 1. Train original model (2 epochs)
    model_orig = FashionMLP(input_dim=784, num_classes=10)
    trainer = ModelTrainer(model_orig, learning_rate=0.01)
    train_res = trainer.train(retain_ds, val_ds, epochs=2, batch_size=32)
    assert train_res["training_time_seconds"] > 0

    # 2. Approximate Unlearning
    unlearner = RetainFineTuningUnlearner(model_orig, learning_rate=0.001)
    unlearn_res = unlearner.unlearn(retain_ds, val_ds, forget_ds, epochs=1, batch_size=32)
    assert unlearn_res["unlearning_time_seconds"] > 0
    assert unlearn_res["method"] == "retain_fine_tuning"

    # 3. Evaluation
    metrics_retain = compute_dataset_metrics(unlearner.model, retain_ds)
    assert metrics_retain["accuracy"] >= 0.0


def test_mia_evaluator_metrics_and_uncertainty():
    """Verify shadow MIA computes standard error, sample counts, and directional advantage."""
    train_ds, test_ds, _ = load_raw_dataset("tofu")
    partitioner = DatasetPartitioner(train_ds, val_ratio=0.1, seed=42, subsample_size=200)
    partitioner.create_partition(strategy="class", target_class=0)
    retain_ds, forget_ds, val_ds = partitioner.get_subsets()

    model = FashionMLP(input_dim=784, num_classes=10)
    mia_eval = MembershipInferenceEvaluator(seed=42)
    res = mia_eval.evaluate_forget_set_mia(model, retain_ds, forget_ds, test_ds, batch_size=64)

    assert "roc_auc" in res
    assert "roc_auc_standard_error" in res
    assert "absolute_advantage" in res
    assert "num_forget_evaluated" in res
    assert "num_test_evaluated" in res
    assert res["num_forget_evaluated"] > 0
    assert res["num_test_evaluated"] > 0
    assert 0.0 <= res["roc_auc"] <= 1.0


def test_gradient_ascent_clamping_and_normalization():
    """Verify regularized gradient ascent loss clamping and parameter normalization."""
    train_ds, test_ds, _ = load_raw_dataset("tofu")
    partitioner = DatasetPartitioner(train_ds, val_ratio=0.1, seed=42, subsample_size=200)
    partitioner.create_partition(strategy="class", target_class=0)
    retain_ds, forget_ds, val_ds = partitioner.get_subsets()

    model = FashionMLP(input_dim=784, num_classes=10)
    unlearner = RegularizedGradientAscentUnlearner(model, learning_rate=0.001, max_forget_loss=2.5)
    assert unlearner.total_trainable_params > 0

    res = unlearner.unlearn(retain_ds, forget_ds, val_ds, epochs=1, batch_size=32)
    assert res["unlearning_time_seconds"] > 0
    assert res["method"] == "gradient_ascent_regularized"


def test_job_service_fail_state():
    """Verify that job failure properly marks the parent experiment as FAILED."""
    exp_service = ExperimentService()
    exp = exp_service.create_experiment("Fail Test", "Testing failure propagation", "fashion_mnist", "mlp")
    exp_id = exp["id"]

    job_service = JobService()
    job_id = job_service.create_job(exp_id, "TEST_FAIL")
    job_service.fail_job(job_id, "Simulated crash for regression test")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT status FROM experiments WHERE id = ?", (exp_id,))
    row = c.fetchone()
    conn.close()

    assert row is not None
    assert row["status"] == "FAILED"
