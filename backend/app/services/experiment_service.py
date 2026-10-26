import datetime
import json
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
import torch
import torch.nn as nn
from ml.datasets.loader import load_raw_dataset
from ml.datasets.partitioner import DatasetPartitioner
from ml.models import get_model
from ml.training.trainer import ModelTrainer
from ml.unlearning.fine_tuning import RetainFineTuningUnlearner
from ml.unlearning.gradient_ascent import RegularizedGradientAscentUnlearner
from ml.evaluation import (
    compute_dataset_metrics,
    compute_utility_degradation,
    MembershipInferenceEvaluator,
    compute_behavioral_similarity,
)
from ml.utils.seed import set_seed
from ml.utils.hardware import get_device, get_hardware_info
from ..database.db import get_db_connection


class ExperimentService:
    def __init__(self, checkpoints_dir: str = "./checkpoints", data_dir: str = "./data"):
        self.checkpoints_dir = checkpoints_dir
        self.data_dir = data_dir
        # In-memory cache of partitioners per experiment
        self._partitioners: Dict[str, DatasetPartitioner] = {}
        self._raw_datasets_cache: Dict[str, Any] = {}

    def _get_datasets(self, dataset_name: str):
        key = dataset_name.lower().strip()
        if key not in self._raw_datasets_cache:
            train_ds, test_ds, classes = load_raw_dataset(key, data_dir=self.data_dir, download=True)
            self._raw_datasets_cache[key] = (train_ds, test_ds, classes)
        return self._raw_datasets_cache[key]

    def create_experiment(
        self,
        name: str,
        description: str,
        dataset_name: str,
        model_name: str,
        seed: int = 42,
        train_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        exp_id = f"exp_{uuid.uuid4().hex[:10]}"
        now = datetime.datetime.utcnow().isoformat()
        default_config = {
            "epochs": 5,
            "batch_size": 64,
            "learning_rate": 0.001,
            "optimizer": "adam",
            "weight_decay": 1e-4,
            "subsample_size": None,
        }
        if train_config:
            default_config.update(train_config)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO experiments (
                id, name, description, dataset_name, model_name, status, seed,
                created_at, updated_at, train_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            exp_id,
            name,
            description,
            dataset_name,
            model_name,
            "CREATED",
            seed,
            now,
            now,
            json.dumps(default_config),
        ))
        conn.commit()
        conn.close()

        # Initialize partitioner
        train_ds, _, _ = self._get_datasets(dataset_name)
        partitioner = DatasetPartitioner(
            train_dataset=train_ds,
            val_ratio=0.1,
            seed=seed,
            subsample_size=default_config.get("subsample_size"),
        )
        self._partitioners[exp_id] = partitioner

        return self.get_experiment(exp_id)

    def get_experiment(self, exp_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None

        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "dataset_name": row["dataset_name"],
            "model_name": row["model_name"],
            "status": row["status"],
            "seed": row["seed"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "train_config": json.loads(row["train_config"]) if row["train_config"] else None,
            "partition_manifest": json.loads(row["partition_manifest"]) if row["partition_manifest"] else None,
            "unlearn_config": json.loads(row["unlearn_config"]) if row["unlearn_config"] else None,
            "original_checkpoint_path": row["original_checkpoint_path"],
            "retrained_checkpoint_path": row["retrained_checkpoint_path"],
            "unlearned_checkpoint_path": row["unlearned_checkpoint_path"],
            "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
            "insights": json.loads(row["insights"]) if row["insights"] else None,
        }

    def list_experiments(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM experiments ORDER BY created_at DESC")
        rows = c.fetchall()
        conn.close()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "dataset_name": row["dataset_name"],
                "model_name": row["model_name"],
                "status": row["status"],
                "seed": row["seed"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "train_config": json.loads(row["train_config"]) if row["train_config"] else None,
                "partition_manifest": json.loads(row["partition_manifest"]) if row["partition_manifest"] else None,
                "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
            })
        return result

    def _get_or_create_partitioner(self, exp_id: str) -> DatasetPartitioner:
        if exp_id in self._partitioners:
            return self._partitioners[exp_id]

        exp = self.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        train_ds, _, _ = self._get_datasets(exp["dataset_name"])
        cfg = exp.get("train_config") or {}
        partitioner = DatasetPartitioner(
            train_dataset=train_ds,
            val_ratio=0.1,
            seed=exp["seed"],
            subsample_size=cfg.get("subsample_size"),
        )
        # If partition manifest was previously stored, re-apply
        manifest = exp.get("partition_manifest")
        if manifest:
            partitioner.create_partition(
                strategy=manifest["strategy"],
                percentage=manifest.get("percentage"),
                target_class=manifest.get("target_class"),
                group_id=manifest.get("group_id"),
            )
        self._partitioners[exp_id] = partitioner
        return partitioner

    # -------------------------------------------------------------
    # STAGE A: Train Original Model
    # -------------------------------------------------------------
    def train_original_model(
        self,
        exp_id: str,
        config_override: Optional[Dict[str, Any]] = None,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        exp = self.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        set_seed(exp["seed"])
        config = exp.get("train_config") or {}
        if config_override:
            config.update(config_override)

        partitioner = self._get_or_create_partitioner(exp_id)
        # Initial training is on the full available train pool (Retain + Forget together)
        train_pool_indices = partitioner.available_train_indices
        train_pool_ds = torch.utils.data.Subset(partitioner.train_dataset, train_pool_indices)
        _, _, val_ds = partitioner.get_subsets()
        _, test_ds, _ = self._get_datasets(exp["dataset_name"])

        model = get_model(exp["model_name"])
        device = get_device()
        trainer = ModelTrainer(
            model=model,
            device=device,
            learning_rate=config.get("learning_rate", 0.001),
            weight_decay=config.get("weight_decay", 1e-4),
            optimizer_name=config.get("optimizer", "adam"),
        )

        epochs = config.get("epochs", 5)
        batch_size = config.get("batch_size", 64)

        def on_epoch(event):
            if step_callback:
                ep = event["epoch"]
                prog = (ep / epochs) * 90.0
                step_callback({
                    "progress": prog,
                    "current_step": f"Training Original Model Epoch {ep}/{epochs}",
                    "log": f"Original Model - Epoch {ep}/{epochs} - Train Loss: {event['data']['train_loss']} - Train Acc: {event['data']['train_accuracy']}%",
                })

        train_result = trainer.train(
            train_dataset=train_pool_ds,
            val_dataset=val_ds,
            epochs=epochs,
            batch_size=batch_size,
            progress_callback=on_epoch,
        )

        # Test evaluation
        if step_callback:
            step_callback({
                "progress": 95.0,
                "current_step": "Evaluating on Test Set",
                "log": "Evaluating original model on independent test set...",
            })
        test_eval = trainer.evaluate(test_ds, batch_size=batch_size)
        train_result["final_test_loss"] = test_eval["loss"]
        train_result["final_test_accuracy"] = test_eval["accuracy"]

        # Save checkpoint
        checkpoint_path = os.path.join(self.checkpoints_dir, exp_id, "original.pt")
        trainer.save_checkpoint(checkpoint_path, metadata=train_result)

        # Update experiment in DB
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE experiments
            SET status = 'ORIGINAL_TRAINED',
                original_checkpoint_path = ?,
                train_config = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            checkpoint_path,
            json.dumps(config),
            datetime.datetime.utcnow().isoformat(),
            exp_id,
        ))
        conn.commit()
        conn.close()

        return train_result

    # -------------------------------------------------------------
    # STAGE B: Forgetting Request & Partitioning
    # -------------------------------------------------------------
    def request_forgetting(
        self,
        exp_id: str,
        strategy: str,
        percentage: Optional[float] = None,
        target_class: Optional[int] = None,
        sample_ids: Optional[List[int]] = None,
        group_id: Optional[int] = None,
        num_groups: int = 10,
    ) -> Dict[str, Any]:
        partitioner = self._get_or_create_partitioner(exp_id)
        manifest = partitioner.create_partition(
            strategy=strategy,
            percentage=percentage,
            target_class=target_class,
            sample_ids=sample_ids,
            group_id=group_id,
            num_groups=num_groups,
        )

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE experiments
            SET partition_manifest = ?,
                status = 'PARTITIONED',
                updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(manifest),
            datetime.datetime.utcnow().isoformat(),
            exp_id,
        ))
        conn.commit()
        conn.close()

        return manifest

    # -------------------------------------------------------------
    # STAGE C: Exact Retraining Baseline (Golden Reference)
    # -------------------------------------------------------------
    def train_retrained_model(
        self,
        exp_id: str,
        config_override: Optional[Dict[str, Any]] = None,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        exp = self.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        manifest = exp.get("partition_manifest")
        if not manifest:
            raise ValueError("No forgetting partition found. Please submit a forgetting request first.")

        set_seed(exp["seed"])
        config = exp.get("train_config") or {}
        if config_override:
            config.update(config_override)

        partitioner = self._get_or_create_partitioner(exp_id)
        retain_ds, _, val_ds = partitioner.get_subsets()
        _, test_ds, _ = self._get_datasets(exp["dataset_name"])

        # Train new model from scratch with SAME architecture
        model = get_model(exp["model_name"])
        device = get_device()
        trainer = ModelTrainer(
            model=model,
            device=device,
            learning_rate=config.get("learning_rate", 0.001),
            weight_decay=config.get("weight_decay", 1e-4),
            optimizer_name=config.get("optimizer", "adam"),
        )

        epochs = config.get("epochs", 5)
        batch_size = config.get("batch_size", 64)

        def on_epoch(event):
            if step_callback:
                ep = event["epoch"]
                prog = (ep / epochs) * 90.0
                step_callback({
                    "progress": prog,
                    "current_step": f"Exact Retraining Epoch {ep}/{epochs}",
                    "log": f"Retrained Reference - Epoch {ep}/{epochs} - Retain Loss: {event['data']['train_loss']} - Retain Acc: {event['data']['train_accuracy']}%",
                })

        train_result = trainer.train(
            train_dataset=retain_ds,
            val_dataset=val_ds,
            epochs=epochs,
            batch_size=batch_size,
            progress_callback=on_epoch,
        )

        if step_callback:
            step_callback({
                "progress": 95.0,
                "current_step": "Evaluating Retrained Model on Test Set",
                "log": "Evaluating exact retrained reference on test set...",
            })
        test_eval = trainer.evaluate(test_ds, batch_size=batch_size)
        train_result["final_test_loss"] = test_eval["loss"]
        train_result["final_test_accuracy"] = test_eval["accuracy"]

        checkpoint_path = os.path.join(self.checkpoints_dir, exp_id, "retrained.pt")
        trainer.save_checkpoint(checkpoint_path, metadata=train_result)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE experiments
            SET retrained_checkpoint_path = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            checkpoint_path,
            datetime.datetime.utcnow().isoformat(),
            exp_id,
        ))
        conn.commit()
        conn.close()

        return train_result

    # -------------------------------------------------------------
    # STAGE D: Machine Unlearning
    # -------------------------------------------------------------
    def run_unlearning(
        self,
        exp_id: str,
        algorithm: str = "retain_fine_tuning",
        epochs: int = 3,
        batch_size: int = 64,
        learning_rate: float = 0.0003,
        alpha_ascent: float = 0.4,
        beta_proximity: float = 0.01,
        max_forget_loss: float = 2.35,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        exp = self.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        orig_ckpt = exp.get("original_checkpoint_path")
        if not orig_ckpt or not os.path.exists(orig_ckpt):
            raise ValueError("Original model checkpoint not found. Please train original model first.")

        partitioner = self._get_or_create_partitioner(exp_id)
        retain_ds, forget_ds, val_ds = partitioner.get_subsets()

        # Load base model from original checkpoint
        device = get_device()
        base_model = get_model(exp["model_name"])
        checkpoint = torch.load(orig_ckpt, map_location=device, weights_only=False)
        base_model.load_state_dict(checkpoint["model_state_dict"])

        unlearn_config = {
            "algorithm": algorithm,
            "epochs": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "alpha_ascent": alpha_ascent,
            "beta_proximity": beta_proximity,
            "max_forget_loss": max_forget_loss,
        }

        def on_epoch(event):
            if step_callback:
                ep = event["epoch"]
                prog = (ep / epochs) * 90.0
                step_callback({
                    "progress": prog,
                    "current_step": f"Unlearning Epoch {ep}/{epochs} ({algorithm})",
                    "log": f"Unlearning - Epoch {ep}/{epochs} - Retain Acc: {event['data']['retain_accuracy']}%",
                })

        if algorithm == "gradient_ascent":
            unlearner = RegularizedGradientAscentUnlearner(
                base_model=base_model,
                learning_rate=learning_rate,
                alpha_ascent=alpha_ascent,
                beta_proximity=beta_proximity,
                max_forget_loss=max_forget_loss,
                device=device,
            )
            unlearn_result = unlearner.unlearn(
                retain_dataset=retain_ds,
                forget_dataset=forget_ds,
                val_dataset=val_ds,
                epochs=epochs,
                batch_size=batch_size,
                progress_callback=on_epoch,
            )
            final_model = unlearner.model
        else:
            # Retain-set fine-tuning
            unlearner = RetainFineTuningUnlearner(
                base_model=base_model,
                learning_rate=learning_rate,
                device=device,
            )
            unlearn_result = unlearner.unlearn(
                retain_dataset=retain_ds,
                val_dataset=val_ds,
                forget_dataset=forget_ds,
                epochs=epochs,
                batch_size=batch_size,
                progress_callback=on_epoch,
            )
            final_model = unlearner.model

        checkpoint_path = os.path.join(self.checkpoints_dir, exp_id, "unlearned.pt")
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        torch.save(
            {
                "model_state_dict": final_model.state_dict(),
                "metadata": unlearn_result,
                "config": unlearn_config,
            },
            checkpoint_path,
        )

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE experiments
            SET unlearned_checkpoint_path = ?,
                unlearn_config = ?,
                status = 'UNLEARNED',
                updated_at = ?
            WHERE id = ?
        """, (
            checkpoint_path,
            json.dumps(unlearn_config),
            datetime.datetime.utcnow().isoformat(),
            exp_id,
        ))
        conn.commit()
        conn.close()

        return unlearn_result

    # -------------------------------------------------------------
    # STAGE E: Full 3-Way Model Evaluation
    # -------------------------------------------------------------
    def evaluate_experiment(
        self,
        exp_id: str,
        step_callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        exp = self.get_experiment(exp_id)
        if not exp:
            raise ValueError(f"Experiment {exp_id} not found")

        orig_ckpt_path = exp.get("original_checkpoint_path")
        retrain_ckpt_path = exp.get("retrained_checkpoint_path")
        unlearn_ckpt_path = exp.get("unlearned_checkpoint_path")

        if not orig_ckpt_path or not os.path.exists(orig_ckpt_path):
            raise ValueError("Original model checkpoint missing")
        if not unlearn_ckpt_path or not os.path.exists(unlearn_ckpt_path):
            raise ValueError("Unlearned model checkpoint missing")

        device = get_device()
        partitioner = self._get_or_create_partitioner(exp_id)
        retain_ds, forget_ds, val_ds = partitioner.get_subsets()
        _, test_ds, classes = self._get_datasets(exp["dataset_name"])

        # Load models
        orig_model = get_model(exp["model_name"]).to(device)
        orig_ckpt = torch.load(orig_ckpt_path, map_location=device, weights_only=False)
        orig_model.load_state_dict(orig_ckpt["model_state_dict"])
        orig_meta = orig_ckpt.get("metadata", {})

        unlearn_model = get_model(exp["model_name"]).to(device)
        unlearn_ckpt = torch.load(unlearn_ckpt_path, map_location=device, weights_only=False)
        unlearn_model.load_state_dict(unlearn_ckpt["model_state_dict"])
        unlearn_meta = unlearn_ckpt.get("metadata", {})

        retrain_model = None
        retrain_meta = {}
        if retrain_ckpt_path and os.path.exists(retrain_ckpt_path):
            retrain_model = get_model(exp["model_name"]).to(device)
            retrain_ckpt = torch.load(retrain_ckpt_path, map_location=device, weights_only=False)
            retrain_model.load_state_dict(retrain_ckpt["model_state_dict"])
            retrain_meta = retrain_ckpt.get("metadata", {})

        # 1. Evaluate Original Model
        if step_callback:
            step_callback({"progress": 15.0, "current_step": "Evaluating Original Model", "log": "Evaluating Original Model across retain, forget, val, test..."})
        orig_eval = {
            "retain": compute_dataset_metrics(orig_model, retain_ds, device=device),
            "forget": compute_dataset_metrics(orig_model, forget_ds, device=device),
            "val": compute_dataset_metrics(orig_model, val_ds, device=device),
            "test": compute_dataset_metrics(orig_model, test_ds, device=device),
            "training_time_seconds": orig_meta.get("training_time_seconds", 0.0),
            "peak_memory_mb": orig_meta.get("peak_memory_mb", 0.0),
        }

        # 2. Evaluate Unlearned Model
        if step_callback:
            step_callback({"progress": 40.0, "current_step": "Evaluating Unlearned Model", "log": "Evaluating Unlearned Model across retain, forget, val, test..."})
        unlearn_eval = {
            "retain": compute_dataset_metrics(unlearn_model, retain_ds, device=device),
            "forget": compute_dataset_metrics(unlearn_model, forget_ds, device=device),
            "val": compute_dataset_metrics(unlearn_model, val_ds, device=device),
            "test": compute_dataset_metrics(unlearn_model, test_ds, device=device),
            "unlearning_time_seconds": unlearn_meta.get("unlearning_time_seconds", 0.0),
            "peak_memory_mb": unlearn_meta.get("peak_memory_mb", 0.0),
            "utility_degradation_pct": compute_utility_degradation(
                orig_eval["test"]["accuracy"],
                compute_dataset_metrics(unlearn_model, test_ds, device=device)["accuracy"],
            ),
        }

        # 3. Evaluate Retrained Reference Model if available
        retrain_eval = None
        speedup = None
        similarity_metrics = None

        if retrain_model is not None:
            if step_callback:
                step_callback({"progress": 65.0, "current_step": "Evaluating Retrained Reference Model", "log": "Evaluating Retrained Model across retain, forget, val, test..."})
            retrain_eval = {
                "retain": compute_dataset_metrics(retrain_model, retain_ds, device=device),
                "forget": compute_dataset_metrics(retrain_model, forget_ds, device=device),
                "val": compute_dataset_metrics(retrain_model, val_ds, device=device),
                "test": compute_dataset_metrics(retrain_model, test_ds, device=device),
                "retraining_time_seconds": retrain_meta.get("training_time_seconds", 0.0),
                "peak_memory_mb": retrain_meta.get("peak_memory_mb", 0.0),
            }

            retrain_time = retrain_meta.get("training_time_seconds", 1.0)
            unlearn_time = max(0.001, unlearn_meta.get("unlearning_time_seconds", 0.001))
            speedup = round(retrain_time / unlearn_time, 2)

            if step_callback:
                step_callback({"progress": 80.0, "current_step": "Computing Behavioral Similarity", "log": "Calculating KL-divergence and prediction agreement..."})
            similarity_metrics = compute_behavioral_similarity(
                unlearned_model=unlearn_model,
                retrained_model=retrain_model,
                eval_dataset=test_ds,
                device=device,
            )

        # 4. Membership Inference Attack (MIA)
        if step_callback:
            step_callback({"progress": 85.0, "current_step": "Executing Membership Inference Attack", "log": "Training shadow MIA attack model on disjoint sets..."})
        mia_evaluator = MembershipInferenceEvaluator(device=device, seed=exp["seed"])
        mia_original = mia_evaluator.evaluate_forget_set_mia(
            orig_model, retain_ds, forget_ds, test_ds
        )
        mia_unlearned = mia_evaluator.evaluate_forget_set_mia(
            unlearn_model, retain_ds, forget_ds, test_ds
        )
        mia_retrained = None
        if retrain_model is not None:
            mia_retrained = mia_evaluator.evaluate_forget_set_mia(
                retrain_model, retain_ds, forget_ds, test_ds
            )

        # Strip large raw arrays from metrics for clean JSON storage
        for m_dict in [orig_eval, unlearn_eval, retrain_eval]:
            if m_dict:
                for k in ["retain", "forget", "val", "test"]:
                    if k in m_dict:
                        m_dict[k].pop("raw_losses", None)
                        m_dict[k].pop("raw_confidences", None)
                        m_dict[k].pop("probabilities", None)
                        m_dict[k].pop("predictions", None)
                        m_dict[k].pop("targets", None)

        # Compute summary comparison structure
        metrics_payload = {
            "original_model": orig_eval,
            "unlearned_model": unlearn_eval,
            "retrained_model": retrain_eval,
            "speedup_factor": speedup,
            "behavioral_similarity": similarity_metrics,
            "mia": {
                "original": mia_original,
                "unlearned": mia_unlearned,
                "retrained": mia_retrained,
            },
            "classes": classes,
        }

        # 5. Generate Evidence-Based Research Insights
        if step_callback:
            step_callback({"progress": 95.0, "current_step": "Synthesizing Evidence-Based Insights", "log": "Generating scientific interpretations..."})
        insights = self._generate_research_insights(metrics_payload, exp)

        # Save to DB
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE experiments
            SET metrics = ?,
                insights = ?,
                status = 'EVALUATED',
                updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(metrics_payload),
            json.dumps(insights),
            datetime.datetime.utcnow().isoformat(),
            exp_id,
        ))
        conn.commit()
        conn.close()

        return metrics_payload

    def _generate_research_insights(self, m: Dict[str, Any], exp: Dict[str, Any]) -> Dict[str, Any]:
        orig = m["original_model"]
        unl = m["unlearned_model"]
        ret = m.get("retrained_model")
        mia = m["mia"]
        sim = m.get("behavioral_similarity")
        speedup = m.get("speedup_factor")

        orig_fg_acc = orig["forget"]["accuracy"]
        unl_fg_acc = unl["forget"]["accuracy"]
        ret_fg_acc = ret["forget"]["accuracy"] if ret else None

        orig_test_acc = orig["test"]["accuracy"]
        unl_test_acc = unl["test"]["accuracy"]
        ret_test_acc = ret["test"]["accuracy"] if ret else None

        mia_orig_auc = mia["original"]["roc_auc"]
        mia_unl_auc = mia["unlearned"]["roc_auc"]
        mia_ret_auc = mia["retrained"]["roc_auc"] if ret else None

        # 1. Forgetting effectiveness interpretation
        forget_delta = orig_fg_acc - unl_fg_acc
        if ret_fg_acc is not None:
            gap_to_retrain = abs(unl_fg_acc - ret_fg_acc)
            if gap_to_retrain <= 5.0:
                forget_text = (
                    f"The unlearned model reduced forget-set accuracy from {orig_fg_acc}% to {unl_fg_acc}%, "
                    f"which is within {round(gap_to_retrain, 1)}% of the retrained baseline reference ({ret_fg_acc}%). "
                    "This demonstrates strong empirical alignment with the golden retraining target."
                )
            else:
                forget_text = (
                    f"Forget-set accuracy dropped from {orig_fg_acc}% to {unl_fg_acc}%, while the exact retrained baseline sits at {ret_fg_acc}%. "
                    f"There remains an accuracy delta of {round(gap_to_retrain, 1)}%, indicating partial or incomplete forgetting under the current hyperparameter configuration."
                )
        else:
            forget_text = (
                f"The unlearned model reduced forget-set accuracy from {orig_fg_acc}% to {unl_fg_acc}%. "
                "However, exact retraining has not yet been executed to serve as the golden reference."
            )

        # 2. Retained utility interpretation
        utility_degradation = unl.get("utility_degradation_pct", 0.0)
        if utility_degradation <= 2.5:
            utility_text = (
                f"Retained test utility remained highly stable with only {utility_degradation}% degradation "
                f"(Original: {orig_test_acc}%, Unlearned: {unl_test_acc}%). The model successfully preserved its generalization capacity."
            )
        else:
            utility_text = (
                f"Test utility suffered a {utility_degradation}% degradation (Original: {orig_test_acc}%, Unlearned: {unl_test_acc}%). "
                "This indicates slight collateral damage to non-forgotten representations."
            )

        # 3. Privacy & Membership Inference Attack (MIA)
        mia_delta = mia_orig_auc - mia_unl_auc
        if mia_unl_auc <= 0.55:
            mia_text = (
                f"Membership Inference ROC-AUC on the forget set was measured at {mia_unl_auc} (Unlearned) vs {mia_orig_auc} (Original). "
                "An AUC near 0.50 signifies that this specific shadow attacker cannot reliably separate forgotten samples from unseen test samples based on confidence/loss features under this empirical setup. It does not constitute certified proof of zero privacy leakage."
            )
        else:
            mia_text = (
                f"Membership Inference ROC-AUC is {mia_unl_auc} for the unlearned model (compared to {mia_orig_auc} original and {mia_ret_auc if mia_ret_auc else 'N/A'} retrained). "
                "While residual membership signal remains detectable by a dedicated attacker, privacy risk is reduced compared to the original model."
            )

        # 4. Computational Efficiency
        if speedup:
            eff_text = (
                f"Machine unlearning achieved a {speedup}x speedup relative to full retraining from scratch "
                f"({unl['unlearning_time_seconds']}s vs {ret['retraining_time_seconds']}s), fulfilling the core promise of computational efficiency."
            )
        else:
            eff_text = f"Unlearning completed in {unl['unlearning_time_seconds']} seconds."

        # 5. Scientific Limitations & Rigorous Caveats
        limitations = [
            "Lower forget-set accuracy alone does not prove certified forgetting; it could reflect intentional misclassification or damaged feature layers.",
            "Approximate unlearning (fine-tuning / regularized gradient ascent) offers empirical heuristic convergence, not the mathematical epsilon-unlearning guarantee of differential privacy.",
            "Behavioral similarity (KL divergence and prediction agreement) reflects output-space proximity, but internal hidden representations may retain subtle latent artifacts.",
            "MIA evaluation reflects the specific loss/entropy attacker deployed; stronger adaptive attacks could reveal additional residual privacy leakage."
        ]

        return {
            "forgetting_effectiveness": forget_text,
            "retained_utility": utility_text,
            "privacy_risk_mia": mia_text,
            "computational_efficiency": eff_text,
            "scientific_limitations": limitations,
            "summary_recommendation": (
                "The approximate unlearning method provides a viable pragmatic trade-off between computational cost and privacy preservation. "
                "For high-compliance regulatory environments requiring certified erasure, exact retraining or differentially private unlearning remains the gold standard."
            ),
        }

