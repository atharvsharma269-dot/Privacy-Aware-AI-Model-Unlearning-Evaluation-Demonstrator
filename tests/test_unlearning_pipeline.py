import os
import shutil
import unittest
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from ml.datasets.loader import IndexedDataset
from ml.datasets.partitioner import DatasetPartitioner
from ml.models.mlp import FashionMLP
from ml.models.cnn import FashionCNN
from ml.training.trainer import ModelTrainer
from ml.unlearning.fine_tuning import RetainFineTuningUnlearner
from ml.unlearning.gradient_ascent import RegularizedGradientAscentUnlearner
from ml.evaluation.metrics import compute_dataset_metrics, compute_utility_degradation
from ml.evaluation.mia import MembershipInferenceEvaluator
from ml.evaluation.similarity import compute_behavioral_similarity
from ml.utils.seed import set_seed


class TestUnlearningPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        set_seed(42)
        # Create a synthetic dataset of 200 samples, 28x28 images, 10 classes for fast deterministic testing
        x = torch.randn(200, 1, 28, 28)
        y = torch.randint(0, 10, (200,))
        base_ds = TensorDataset(x, y)
        cls.indexed_ds = IndexedDataset(base_ds)

    def test_01_partitioner_strict_disjoint(self):
        """Verify Retain, Forget, and Val sets have zero overlap and sum to total pool."""
        partitioner = DatasetPartitioner(self.indexed_ds, val_ratio=0.1, seed=42)
        manifest = partitioner.create_partition(strategy="random", percentage=0.20)

        retain_ds, forget_ds, val_ds = partitioner.get_subsets()
        indices = partitioner.get_indices_dict()

        retain_set = set(indices["retain_indices"])
        forget_set = set(indices["forget_indices"])
        val_set = set(indices["val_indices"])

        # Check zero overlaps
        self.assertEqual(len(retain_set.intersection(forget_set)), 0, "Retain and Forget overlap!")
        self.assertEqual(len(retain_set.intersection(val_set)), 0, "Retain and Val overlap!")
        self.assertEqual(len(forget_set.intersection(val_set)), 0, "Forget and Val overlap!")

        # Check completeness
        self.assertEqual(len(retain_set) + len(forget_set) + len(val_set), 200)
        self.assertAlmostEqual(manifest["forget_ratio"], 0.20, delta=0.05)

    def test_02_class_specific_partitioning(self):
        """Verify class-specific deletion selects only the targeted class."""
        partitioner = DatasetPartitioner(self.indexed_ds, val_ratio=0.1, seed=42)
        target_class = 3
        manifest = partitioner.create_partition(strategy="class", target_class=target_class)

        for idx in partitioner.forget_indices:
            _, _, label = self.indexed_ds[idx]
            self.assertEqual(int(label), target_class)

    def test_03_group_based_partitioning(self):
        """Verify group-based deletion allocates samples consistently by group ID."""
        partitioner = DatasetPartitioner(self.indexed_ds, val_ratio=0.1, seed=42)
        group_id = 2
        num_groups = 5
        manifest = partitioner.create_partition(strategy="group", group_id=group_id, num_groups=num_groups)

        for idx in partitioner.forget_indices:
            self.assertEqual(idx % num_groups, group_id % num_groups)

    def test_04_model_forward_and_checkpoint(self):
        """Verify model forward pass and checkpoint saving/loading."""
        model = FashionMLP(num_classes=10)
        x = torch.randn(4, 1, 28, 28)
        out = model(x)
        self.assertEqual(out.shape, (4, 10))

        trainer = ModelTrainer(model)
        ckpt_path = "./checkpoints/test_model.pt"
        trainer.save_checkpoint(ckpt_path, metadata={"test_metric": 42.0})

        new_model = FashionMLP(num_classes=10)
        new_trainer = ModelTrainer(new_model)
        meta = new_trainer.load_checkpoint(ckpt_path)
        self.assertEqual(meta["test_metric"], 42.0)

        if os.path.exists(ckpt_path):
            os.remove(ckpt_path)

    def test_05_unlearning_execution(self):
        """Verify both unlearning methods execute without error and produce valid weights."""
        model = FashionMLP(num_classes=10)
        partitioner = DatasetPartitioner(self.indexed_ds, val_ratio=0.1, seed=42)
        partitioner.create_partition(strategy="random", percentage=0.10)
        retain_ds, forget_ds, val_ds = partitioner.get_subsets()

        # Retain Fine-Tuning
        ft_unlearner = RetainFineTuningUnlearner(model, learning_rate=0.001)
        ft_res = ft_unlearner.unlearn(retain_ds, epochs=1, batch_size=32)
        self.assertEqual(ft_res["method"], "retain_fine_tuning")
        self.assertIn("unlearning_time_seconds", ft_res)

        # Regularized Gradient Ascent
        ga_unlearner = RegularizedGradientAscentUnlearner(model, learning_rate=0.0005)
        ga_res = ga_unlearner.unlearn(retain_ds, forget_ds, epochs=1, batch_size=32)
        self.assertEqual(ga_res["method"], "gradient_ascent_regularized")
        self.assertIn("unlearning_time_seconds", ga_res)

    def test_06_metrics_and_similarity(self):
        """Verify metrics computation, behavioral similarity, and MIA evaluation."""
        model_a = FashionMLP(num_classes=10)
        model_b = FashionMLP(num_classes=10)

        metrics_a = compute_dataset_metrics(model_a, self.indexed_ds, batch_size=32)
        self.assertIn("accuracy", metrics_a)
        self.assertIn("loss", metrics_a)
        self.assertIn("class_metrics", metrics_a)

        sim = compute_behavioral_similarity(model_a, model_b, self.indexed_ds, batch_size=32)
        self.assertIn("prediction_agreement_percent", sim)
        self.assertIn("mean_kl_divergence", sim)
        self.assertIn("weight_l2_distance", sim)

        # Test MIA
        partitioner = DatasetPartitioner(self.indexed_ds, val_ratio=0.2, seed=42)
        partitioner.create_partition(strategy="random", percentage=0.20)
        retain_ds, forget_ds, test_ds = partitioner.get_subsets()

        mia = MembershipInferenceEvaluator(seed=42)
        mia_result = mia.evaluate_forget_set_mia(model_a, retain_ds, forget_ds, test_ds, batch_size=32)
        self.assertIn("roc_auc", mia_result)
        self.assertIn("attack_advantage", mia_result)
        self.assertIn("roc_curve", mia_result)


if __name__ == "__main__":
    unittest.main()

