import math
import os
import sys
import json
import sqlite3
import time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from ml.models import get_model
from ml.datasets.loader import load_raw_dataset
from ml.datasets.partitioner import DatasetPartitioner
from ml.evaluation import (
    compute_dataset_metrics,
    MembershipInferenceEvaluator,
    compute_behavioral_similarity,
)
from ml.utils.hardware import get_device

METRIC_TOLERANCE = 1e-4

def main():
    print("=" * 70)
    print("  EMPIRICAL VALIDATION OF MACHINE UNLEARNING PIPELINE")
    print("=" * 70)

    # 1. Connect to database and retrieve experiment metadata
    conn = sqlite3.connect("experiments/experiments.db")
    c = conn.cursor()
    exp_id = "exp_0126de8dc3"
    c.execute("SELECT * FROM experiments WHERE id = ?", (exp_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: Experiment {exp_id} not found in database.")
        sys.exit(1)

    col_names = [desc[0] for desc in c.description]
    exp = dict(zip(col_names, row))
    
    # Parse JSON fields
    for k in ["train_config", "partition_manifest", "unlearn_config", "metrics", "insights"]:
        if exp.get(k):
            try:
                exp[k] = json.loads(exp[k])
            except Exception:
                pass

    print(f"\n[Step 1] Target Experiment Selected:")
    print(f"  * ID: {exp['id']}")
    print(f"  * Name: {exp['name']}")
    print(f"  * Dataset: {exp['dataset_name']}")
    print(f"  * Model Architecture: {exp['model_name']}")
    print(f"  * Random Seed: {exp['seed']}")
    print(f"  * Status: {exp['status']}")

    # 2. Verify Checkpoint Existence & Architecture Consistency
    print(f"\n[Step 2] Checkpoint Verification & Loading:")
    orig_path = exp["original_checkpoint_path"]
    ret_path = exp["retrained_checkpoint_path"]
    unl_path = exp["unlearned_checkpoint_path"]

    print(f"  * Original Checkpoint Path : {orig_path} (Exists: {os.path.exists(orig_path)})")
    print(f"  * Retrained Checkpoint Path: {ret_path} (Exists: {os.path.exists(ret_path)})")
    print(f"  * Unlearned Checkpoint Path: {unl_path} (Exists: {os.path.exists(unl_path)})")

    assert os.path.exists(orig_path), "Original checkpoint missing"
    assert os.path.exists(ret_path), "Retrained checkpoint missing"
    assert os.path.exists(unl_path), "Unlearned checkpoint missing"

    device = get_device()
    print(f"  * Evaluation Device: {device}")

    # Load checkpoints
    ckpt_orig = torch.load(orig_path, map_location=device, weights_only=False)
    ckpt_ret = torch.load(ret_path, map_location=device, weights_only=False)
    ckpt_unl = torch.load(unl_path, map_location=device, weights_only=False)

    print(f"  * ckpt_orig keys: {list(ckpt_orig.keys())}")
    print(f"  * ckpt_ret  keys: {list(ckpt_ret.keys())}")
    print(f"  * ckpt_unl  keys: {list(ckpt_unl.keys())}")

    # Verify model class and instantiate models
    model_name = exp["model_name"]
    model_orig = get_model(model_name).to(device)
    model_ret = get_model(model_name).to(device)
    model_unl = get_model(model_name).to(device)

    model_orig.load_state_dict(ckpt_orig["model_state_dict"])
    model_ret.load_state_dict(ckpt_ret["model_state_dict"])
    model_unl.load_state_dict(ckpt_unl["model_state_dict"])
    print(f"  * Successfully loaded state_dicts into 3 independent {model_orig.__class__.__name__} instances.")

    # 3. Reconstruct Exact Partitions and Verify Ingestion Provenance
    print(f"\n[Step 3] Partition Reconstruction & Provenance Verification:")
    raw_train_ds, raw_test_ds, class_names = load_raw_dataset(
        exp["dataset_name"], data_dir="./data", download=True
    )
    train_cfg = exp["train_config"] or {}
    subsample_size = train_cfg.get("subsample_size")

    partitioner = DatasetPartitioner(
        train_dataset=raw_train_ds,
        val_ratio=0.1,
        seed=exp["seed"],
        subsample_size=subsample_size,
    )

    manifest_recorded = exp["partition_manifest"]
    manifest_reconstructed = partitioner.create_partition(
        strategy=manifest_recorded["strategy"],
        percentage=manifest_recorded.get("percentage"),
        target_class=manifest_recorded.get("target_class"),
        sample_ids=manifest_recorded.get("sample_ids"),
        group_id=manifest_recorded.get("group_id"),
    )

    print(f"  * Recorded Partition Hash     : {manifest_recorded['manifest_hash']}")
    print(f"  * Reconstructed Partition Hash: {manifest_reconstructed['manifest_hash']}")
    if manifest_recorded["manifest_hash"] != manifest_reconstructed["manifest_hash"]:
        raise ValueError("Hash mismatch in partition reconstruction!")
    print("  * Hashes MATCH: Partitions are 100% bit-for-bit identical to recorded run.")

    retain_ds, forget_ds, val_ds = partitioner.get_subsets()
    test_ds = raw_test_ds

    n_retain = len(retain_ds)
    n_forget = len(forget_ds)
    n_val = len(val_ds)
    n_test = len(test_ds)

    print(f"  * Sample Counts: Retain={n_retain}, Forget={n_forget}, Val={n_val}, Test={n_test}")

    # Check that forget set is strictly a subset of original training pool
    avail_train_set = set(partitioner.available_train_indices)
    forget_set = set(partitioner.forget_indices)
    retain_set = set(partitioner.retain_indices)
    val_set = set(partitioner.val_indices)

    if not forget_set.issubset(avail_train_set):
        raise ValueError("Forget set was not in available training pool!")
    if forget_set.intersection(retain_set):
        raise ValueError("Forget set overlaps with retain set!")
    if forget_set.intersection(val_set):
        raise ValueError("Forget set overlaps with validation set!")
    forget_set_provenance_verified = True
    print(f"  * Verification passed: Forget set ({n_forget} samples) was part of the original training pool and completely disjoint from retain & val sets.")

    # 4. Fresh Empirical Evaluation Inference Across Partitions
    print(f"\n[Step 4] Running Fresh Model Inference on All Partitions...")
    t0_eval = time.time()

    eval_orig = {
        "retain": compute_dataset_metrics(model_orig, retain_ds, device=device),
        "forget": compute_dataset_metrics(model_orig, forget_ds, device=device),
        "val": compute_dataset_metrics(model_orig, val_ds, device=device),
        "test": compute_dataset_metrics(model_orig, test_ds, device=device),
    }

    eval_ret = {
        "retain": compute_dataset_metrics(model_ret, retain_ds, device=device),
        "forget": compute_dataset_metrics(model_ret, forget_ds, device=device),
        "val": compute_dataset_metrics(model_ret, val_ds, device=device),
        "test": compute_dataset_metrics(model_ret, test_ds, device=device),
    }

    eval_unl = {
        "retain": compute_dataset_metrics(model_unl, retain_ds, device=device),
        "forget": compute_dataset_metrics(model_unl, forget_ds, device=device),
        "val": compute_dataset_metrics(model_unl, val_ds, device=device),
        "test": compute_dataset_metrics(model_unl, test_ds, device=device),
    }
    t_eval_duration = round(time.time() - t0_eval, 3)
    print(f"  * Fresh inference completed in {t_eval_duration}s.")

    # 5. Run Fresh MIA and Behavioral Similarity Evaluations
    print(f"\n[Step 5] Running Fresh Membership Inference Attack & Behavioral Divergence...")
    mia_evaluator = MembershipInferenceEvaluator(device=device, seed=exp["seed"])
    
    t0_mia = time.time()
    mia_orig = mia_evaluator.evaluate_forget_set_mia(model_orig, retain_ds, forget_ds, test_ds)
    mia_ret = mia_evaluator.evaluate_forget_set_mia(model_ret, retain_ds, forget_ds, test_ds)
    mia_unl = mia_evaluator.evaluate_forget_set_mia(model_unl, retain_ds, forget_ds, test_ds)
    t_mia_duration = round(time.time() - t0_mia, 3)
    print(f"  * Fresh MIA evaluation completed in {t_mia_duration}s.")

    t0_sim = time.time()
    sim_metrics = compute_behavioral_similarity(
        unlearned_model=model_unl,
        retrained_model=model_ret,
        eval_dataset=test_ds,
        device=device,
    )
    t_sim_duration = round(time.time() - t0_sim, 3)
    print(f"  * Behavioral similarity evaluation completed in {t_sim_duration}s.")

    # 6. Parameter Tensor Difference Analysis
    print(f"\n[Step 6] Parameter Tensor Norm Differences Analysis:")
    diff_orig_unl = 0.0
    diff_orig_ret = 0.0
    diff_unl_ret = 0.0
    orig_sd = ckpt_orig["model_state_dict"]
    ret_sd = ckpt_ret["model_state_dict"]
    unl_sd = ckpt_unl["model_state_dict"]

    param_elements = 0
    trainable_elements = 0
    for name, p_orig in orig_sd.items():
        param_elements += p_orig.numel()
        diff_orig_unl += torch.norm(p_orig.float().cpu() - unl_sd[name].float().cpu()).item()
        diff_orig_ret += torch.norm(p_orig.float().cpu() - ret_sd[name].float().cpu()).item()
        diff_unl_ret += torch.norm(unl_sd[name].float().cpu() - ret_sd[name].float().cpu()).item()

    print(f"  * Total parameter elements: {param_elements}")
    print(f"  * L2 Distance ||theta_orig - theta_unlearned||: {diff_orig_unl:.4f}")
    print(f"  * L2 Distance ||theta_orig - theta_retrained||: {diff_orig_ret:.4f}")
    print(f"  * L2 Distance ||theta_unlearned - theta_retrained||: {diff_unl_ret:.4f}")

    # 7. Record assumptions about the retrained reference initialization protocol
    print(f"\n[Step 7] Retrained Baseline Initialization (Unverified Assumptions):")
    print(f"  * Unverified assumption: ExperimentService.train_retrained_model() creates a fresh model with get_model(exp['model_name']) instead of loading the original checkpoint.")
    print(f"  * Unverified assumption: The model starts from seed {exp['seed']} and trains exclusively on D_retain ({n_retain} samples).")
    print(f"  * Observed parameter difference: ||theta_orig - theta_retrained|| = {diff_orig_ret:.4f}. This does not verify the initialization protocol.")

    # 8. Compare Fresh vs Historical Recorded Results
    hist_m = exp["metrics"]
    print(f"\n[Step 8] Comparison: Fresh Measured vs Historical Recorded Metrics:")
    print("-" * 75)
    print(f"{'Partition / Metric':<28} | {'Historical':<18} | {'Fresh Measured':<18} | {'Delta':<8} | {'Within Tol.'}")
    print("-" * 75)
    metric_comparisons = []

    def print_row(label, hist_val, fresh_val):
        is_numeric = isinstance(hist_val, (int, float, np.number)) and isinstance(fresh_val, (int, float, np.number))
        delta = float(fresh_val) - float(hist_val) if is_numeric else None
        within_tolerance = delta is not None and math.isfinite(delta) and abs(delta) <= METRIC_TOLERANCE
        reported_delta = delta if delta is not None and math.isfinite(delta) else None
        metric_comparisons.append({
            "metric": label,
            "delta": reported_delta,
            "within_tolerance": within_tolerance,
        })
        d_val = round(reported_delta, 4) if reported_delta is not None else "N/A"
        result = "PASS" if within_tolerance else "FAIL"
        print(f"{label:<28} | {str(hist_val):<18} | {str(fresh_val):<18} | {str(d_val):<8} | {result}")

    print_row("Original Retain Acc (%)", hist_m["original_model"]["retain"]["accuracy"], eval_orig["retain"]["accuracy"])
    print_row("Original Forget Acc (%)", hist_m["original_model"]["forget"]["accuracy"], eval_orig["forget"]["accuracy"])
    print_row("Original Test Acc (%)", hist_m["original_model"]["test"]["accuracy"], eval_orig["test"]["accuracy"])
    print_row("Original Forget Loss", hist_m["original_model"]["forget"]["loss"], eval_orig["forget"]["loss"])
    print("-" * 75)
    print_row("Retrained Retain Acc (%)", hist_m["retrained_model"]["retain"]["accuracy"], eval_ret["retain"]["accuracy"])
    print_row("Retrained Forget Acc (%)", hist_m["retrained_model"]["forget"]["accuracy"], eval_ret["forget"]["accuracy"])
    print_row("Retrained Test Acc (%)", hist_m["retrained_model"]["test"]["accuracy"], eval_ret["test"]["accuracy"])
    print_row("Retrained Forget Loss", hist_m["retrained_model"]["forget"]["loss"], eval_ret["forget"]["loss"])
    print("-" * 75)
    print_row("Unlearned Retain Acc (%)", hist_m["unlearned_model"]["retain"]["accuracy"], eval_unl["retain"]["accuracy"])
    print_row("Unlearned Forget Acc (%)", hist_m["unlearned_model"]["forget"]["accuracy"], eval_unl["forget"]["accuracy"])
    print_row("Unlearned Test Acc (%)", hist_m["unlearned_model"]["test"]["accuracy"], eval_unl["test"]["accuracy"])
    print_row("Unlearned Forget Loss", hist_m["unlearned_model"]["forget"]["loss"], eval_unl["forget"]["loss"])
    print("-" * 75)
    print_row("MIA AUC Original", hist_m["mia"]["original"]["roc_auc"], mia_orig["roc_auc"])
    print_row("MIA AUC Retrained", hist_m["mia"]["retrained"]["roc_auc"], mia_ret["roc_auc"])
    print_row("MIA AUC Unlearned", hist_m["mia"]["unlearned"]["roc_auc"], mia_unl["roc_auc"])
    print("-" * 75)
    print_row("Prediction Agreement (%)", hist_m["behavioral_similarity"]["prediction_agreement_percent"], sim_metrics["prediction_agreement_percent"])
    print_row("Mean KL Divergence", hist_m["behavioral_similarity"]["mean_kl_divergence"], sim_metrics["mean_kl_divergence"])
    print_row("Weight L2 Distance", hist_m["behavioral_similarity"]["weight_l2_distance"], sim_metrics["weight_l2_distance"])
    for model_key, model_label, fresh_metrics in (
        ("original_model", "Original", eval_orig),
        ("retrained_model", "Retrained", eval_ret),
        ("unlearned_model", "Unlearned", eval_unl),
    ):
        historical_model = hist_m.get(model_key, {})
        for partition, partition_label, metric_names in (
            ("retain", "Retain", ("loss",)),
            ("test", "Test", ("loss",)),
            ("val", "Val", None),
        ):
            historical_partition = historical_model.get(partition, {})
            fresh_partition = fresh_metrics.get(partition, {})
            if metric_names is None:
                metric_names = tuple(
                    name for name, value in historical_partition.items()
                    if isinstance(value, (int, float, np.number))
                    and isinstance(fresh_partition.get(name), (int, float, np.number))
                )
            for metric_name in metric_names:
                if metric_name in historical_partition and metric_name in fresh_partition:
                    metric_label = f"{model_label} {partition_label} {metric_name.title()}"
                    if metric_name == "accuracy":
                        metric_label += " (%)"
                    print_row(
                        metric_label,
                        historical_partition[metric_name],
                        fresh_partition[metric_name],
                    )
    print(f"  * Metric comparison tolerance: {METRIC_TOLERANCE}")

    metrics_match_within_tolerance = bool(metric_comparisons) and all(
        comparison["within_tolerance"] for comparison in metric_comparisons
    )
    checkpoints_distinct = diff_orig_unl > 0 and diff_orig_ret > 0

    # Historical timings vs newly measured inference timings
    hist_orig_time = hist_m["original_model"]["training_time_seconds"]
    hist_ret_time = hist_m["retrained_model"]["retraining_time_seconds"]
    hist_unl_time = hist_m["unlearned_model"]["unlearning_time_seconds"]
    speedup = hist_m.get("speedup_factor")

    print("\n[Timing Distinction]")
    print(f"  * Historical Training Time (Original): {hist_orig_time}s")
    print(f"  * Historical Retraining Time (Baseline): {hist_ret_time}s")
    print(f"  * Historical Unlearning Time (Approximate): {hist_unl_time}s")
    print(f"  * Historical Speedup Factor: {speedup}x")
    print(f"  * Newly Measured Total Re-Evaluation Time: {t_eval_duration + t_mia_duration + t_sim_duration:.3f}s")

    # 9. Save verification report to JSON without overwriting existing experiment data
    report_output_path = "experiments/verification_report_exp_0126de8dc3.json"
    validation_report = {
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment_id": exp_id,
        "dataset": exp["dataset_name"],
        "model": exp["model_name"],
        "checkpoints_verified": {
            "original_path": orig_path,
            "retrained_path": ret_path,
            "unlearned_path": unl_path,
        },
        "partitions": {
            "retain_count": n_retain,
            "forget_count": n_forget,
            "val_count": n_val,
            "test_count": n_test,
            "manifest_hash": manifest_reconstructed["manifest_hash"],
        },
        "parameter_differences": {
            "total_parameter_elements": param_elements,
            "l2_distance_orig_unlearned": round(diff_orig_unl, 4),
            "l2_distance_orig_retrained": round(diff_orig_ret, 4),
            "l2_distance_unlearned_retrained": round(diff_unl_ret, 4),
        },
        "historical_timings": {
            "original_training_seconds": hist_orig_time,
            "retraining_seconds": hist_ret_time,
            "unlearning_seconds": hist_unl_time,
            "speedup_factor": speedup,
        },
        "newly_measured_evaluation_timings": {
            "inference_duration_seconds": t_eval_duration,
            "mia_duration_seconds": t_mia_duration,
            "similarity_duration_seconds": t_sim_duration,
            "total_audit_runtime_seconds": round(t_eval_duration + t_mia_duration + t_sim_duration, 3),
        },
        "fresh_measured_metrics": {
            "original": eval_orig,
            "retrained": eval_ret,
            "unlearned": eval_unl,
            "mia": {
                "original": mia_orig,
                "retrained": mia_ret,
                "unlearned": mia_unl,
            },
            "behavioral_similarity": sim_metrics,
        },
        "metric_comparisons": {
            "absolute_tolerance": METRIC_TOLERANCE,
            "results": metric_comparisons,
        },
        "verification_verdict": {
            "reproducibility": metrics_match_within_tolerance,
            "checkpoints_distinct": checkpoints_distinct,
            "forget_set_provenance_verified": forget_set_provenance_verified,
            "metrics_integrity": metrics_match_within_tolerance,
            "metrics_integrity_scope": "Stored scalar validation metrics and retain/test losses compared in Step 8 when present.",
        }
    }

    with open(report_output_path, "w", encoding="utf-8") as f:
        json.dump(validation_report, f, indent=2)

    print(f"\n[Step 9] Full Empirical Validation Report Persisted to: {report_output_path}")
    failed_checks = [
        name for name, passed in validation_report["verification_verdict"].items()
        if isinstance(passed, bool) and not passed
    ]
    if failed_checks:
        print(f"[FAILURE] Verification checks failed: {', '.join(failed_checks)}")
        sys.exit(1)
    print("[SUCCESS] All verification checks passed.")

if __name__ == "__main__":
    main()
