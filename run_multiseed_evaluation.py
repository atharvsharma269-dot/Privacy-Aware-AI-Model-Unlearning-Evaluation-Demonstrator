import os
import sys
import copy
import time
import json
import numpy as np
import torch
import torch.nn as nn
from ml.models import get_model
from ml.datasets.loader import load_raw_dataset
from ml.datasets.partitioner import DatasetPartitioner
from ml.training.trainer import ModelTrainer
from ml.unlearning.fine_tuning import RetainFineTuningUnlearner
from ml.unlearning.gradient_ascent import RegularizedGradientAscentUnlearner
from ml.evaluation import (
    compute_dataset_metrics,
    MembershipInferenceEvaluator,
    compute_behavioral_similarity,
)
from ml.utils.seed import set_seed

def run_multiseed_study(seeds=[42, 43, 44]):
    device = torch.device("cpu")
    print(f"Executing Multi-Seed Unlearning Study across seeds: {seeds}...")
    
    results = {
        "seeds": seeds,
        "retrained": [],
        "finetune": [],
        "reg_ga": [],
    }

    raw_train_ds, raw_test_ds, _ = load_raw_dataset("fashion_mnist", data_dir="./data", download=True)

    for seed in seeds:
        print(f"\n==========================================")
        print(f"  RUNNING PIPELINE FOR SEED {seed}")
        print(f"==========================================")
        set_seed(seed)

        # 1. Partition
        partitioner = DatasetPartitioner(
            train_dataset=raw_train_ds,
            val_ratio=0.1,
            seed=seed,
            subsample_size=4000,
        )
        partitioner.create_partition(strategy="random", percentage=0.10)
        retain_ds, forget_ds, val_ds = partitioner.get_subsets()
        test_ds = raw_test_ds
        
        # 2. Train Original Model
        print(f"[Seed {seed}] Training Original Model...")
        orig_model = get_model("mlp").to(device)
        trainer_orig = ModelTrainer(orig_model, device=device, learning_rate=0.001)
        # Train on available training pool (retain + forget)
        train_pool = torch.utils.data.Subset(partitioner.train_dataset, partitioner.available_train_indices)
        trainer_orig.train(train_pool, val_dataset=val_ds, epochs=4, batch_size=64)
        
        # 3. Train Retrained Reference Model (from scratch on retain_ds only)
        print(f"[Seed {seed}] Training Retrained Baseline (Scratch)...")
        set_seed(seed)
        ret_model = get_model("mlp").to(device)
        trainer_ret = ModelTrainer(ret_model, device=device, learning_rate=0.001)
        t0 = time.time()
        trainer_ret.train(retain_ds, val_dataset=val_ds, epochs=4, batch_size=64)
        t_ret = time.time() - t0
        
        m_ret = {
            "retain": compute_dataset_metrics(ret_model, retain_ds, device=device),
            "forget": compute_dataset_metrics(ret_model, forget_ds, device=device),
            "val": compute_dataset_metrics(ret_model, val_ds, device=device),
            "test": compute_dataset_metrics(ret_model, test_ds, device=device),
            "time": round(t_ret, 3),
        }
        
        mia_eval = MembershipInferenceEvaluator(device=device, seed=seed)
        mia_ret = mia_eval.evaluate_forget_set_mia(ret_model, retain_ds, forget_ds, test_ds)
        m_ret["mia_auc"] = mia_ret["roc_auc"]
        m_ret["mia_adv"] = mia_ret["attack_advantage"]
        results["retrained"].append(m_ret)
        
        # 4. Method A: Retain Fine-Tuning
        print(f"[Seed {seed}] Evaluating Method A (Retain Fine-Tuning)...")
        ft_model = copy.deepcopy(orig_model)
        ft_unlearner = RetainFineTuningUnlearner(ft_model, learning_rate=0.0003, device=device)
        t0 = time.time()
        ft_unlearner.unlearn(retain_ds, val_dataset=val_ds, epochs=2, batch_size=64)
        t_ft = time.time() - t0
        
        m_ft = {
            "retain": compute_dataset_metrics(ft_unlearner.model, retain_ds, device=device),
            "forget": compute_dataset_metrics(ft_unlearner.model, forget_ds, device=device),
            "val": compute_dataset_metrics(ft_unlearner.model, val_ds, device=device),
            "test": compute_dataset_metrics(ft_unlearner.model, test_ds, device=device),
            "time": round(t_ft, 3),
        }
        mia_ft = mia_eval.evaluate_forget_set_mia(ft_unlearner.model, retain_ds, forget_ds, test_ds)
        sim_ft = compute_behavioral_similarity(ft_unlearner.model, ret_model, test_ds, device=device)
        m_ft["mia_auc"] = mia_ft["roc_auc"]
        m_ft["mia_adv"] = mia_ft["attack_advantage"]
        m_ft["pred_agree"] = sim_ft["prediction_agreement_percent"]
        m_ft["kl_div"] = sim_ft["mean_kl_divergence"]
        results["finetune"].append(m_ft)
        
        # 5. Method B: Regularized Gradient Ascent (alpha=0.40, lr=1e-4)
        print(f"[Seed {seed}] Evaluating Method B (Regularized Gradient Ascent)...")
        ga_model = copy.deepcopy(orig_model)
        ga_unlearner = RegularizedGradientAscentUnlearner(
            base_model=ga_model,
            learning_rate=0.0001,
            alpha_ascent=0.40,
            beta_proximity=0.01,
            max_forget_loss=2.35,
            device=device,
        )
        t0 = time.time()
        ga_unlearner.unlearn(retain_ds, forget_ds, val_ds, epochs=3, batch_size=64)
        t_ga = time.time() - t0
        
        m_ga = {
            "retain": compute_dataset_metrics(ga_unlearner.model, retain_ds, device=device),
            "forget": compute_dataset_metrics(ga_unlearner.model, forget_ds, device=device),
            "val": compute_dataset_metrics(ga_unlearner.model, val_ds, device=device),
            "test": compute_dataset_metrics(ga_unlearner.model, test_ds, device=device),
            "time": round(t_ga, 3),
        }
        mia_ga = mia_eval.evaluate_forget_set_mia(ga_unlearner.model, retain_ds, forget_ds, test_ds)
        sim_ga = compute_behavioral_similarity(ga_unlearner.model, ret_model, test_ds, device=device)
        m_ga["mia_auc"] = mia_ga["roc_auc"]
        m_ga["mia_adv"] = mia_ga["attack_advantage"]
        m_ga["pred_agree"] = sim_ga["prediction_agreement_percent"]
        m_ga["kl_div"] = sim_ga["mean_kl_divergence"]
        results["reg_ga"].append(m_ga)

    # Statistical Aggregation
    print("\n" + "=" * 90)
    print("  MULTI-SEED AGGREGATE RESULTS (MEAN +/- STD OVER 3 INDEPENDENT SEEDS)")
    print("=" * 90)
    
    def get_stats(method_key, metric_path):
        vals = []
        for run in results[method_key]:
            cur = run
            for p in metric_path.split("."):
                cur = cur[p]
            vals.append(cur)
        return float(np.mean(vals)), float(np.std(vals))

    metrics_to_report = [
        ("Retain Accuracy (%)", "retain.accuracy"),
        ("Forget Accuracy (%)", "forget.accuracy"),
        ("Forget Loss", "forget.loss"),
        ("Test Accuracy (%)", "test.accuracy"),
        ("MIA ROC-AUC", "mia_auc"),
        ("MIA Attack Advantage", "mia_adv"),
        ("Pred Agreement (%)", "pred_agree"),
        ("Mean KL Divergence", "kl_div"),
        ("Execution Time (s)", "time"),
    ]

    print(f"{'Metric':<26} | {'Retrained Reference':<20} | {'Method A (FineTune)':<20} | {'Method B (Reg GA)'}")
    print("-" * 90)

    stats_summary = {}

    for label, path in metrics_to_report:
        if path in ["pred_agree", "kl_div"]:
            m_r, s_r = (100.0, 0.0) if path == "pred_agree" else (0.0, 0.0)
            r_str = "100.0 (Self)" if path == "pred_agree" else "0.0000 (Self)"
        else:
            m_r, s_r = get_stats("retrained", path)
            r_str = f"{m_r:.2f} +/- {s_r:.2f}"
            
        m_a, s_a = get_stats("finetune", path)
        m_b, s_b = get_stats("reg_ga", path)
        
        a_str = f"{m_a:.2f} +/- {s_a:.2f}"
        b_str = f"{m_b:.2f} +/- {s_b:.2f}"
        
        print(f"{label:<26} | {r_str:<20} | {a_str:<20} | {b_str}")
        stats_summary[label] = {
            "retrained": {"mean": m_r, "std": s_r},
            "finetune": {"mean": m_a, "std": s_a},
            "reg_ga": {"mean": m_b, "std": s_b},
        }

    # Save summary report
    out_file = "experiments/multiseed_unlearning_study.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "study_name": "Multi-Seed Unlearning Benchmark Study (Seeds 42, 43, 44)",
            "seeds": seeds,
            "aggregate_stats": stats_summary,
            "raw_runs": results,
        }, f, indent=2)
    print(f"\n[DONE] Saved Multi-Seed Report to {out_file}")

if __name__ == "__main__":
    run_multiseed_study()
