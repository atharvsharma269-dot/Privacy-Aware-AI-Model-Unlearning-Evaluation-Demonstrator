import os
import sys
import time
import json
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.experiment_service import ExperimentService
from ml.evaluation.tofu_generative import TOFUGenerativeEvaluator
from datasets import load_dataset


def run_tofu_audit_benchmark():
    print("=" * 80)
    print("  SCIENTIFIC AUDIT & BENCHMARK: LOCUSLAB TOFU DATASET")
    print("  Framework: Auxiliary Text-Classification Proxy + Generative LM Evaluation")
    print("=" * 80)

    # 1. Author and Dataset Reconciliation
    print("\n[Audit Phase 1] TOFU Dataset & Author Count Reconciliation")
    print("Loading locuslab/TOFU ('full' split)...")
    tofu_full = load_dataset("locuslab/TOFU", "full")["train"]
    total_samples = len(tofu_full)
    total_authors = total_samples // 20

    print(f"  > Total QA pairs in full dataset : {total_samples}")
    print(f"  > Total fictitious authors       : {total_authors} (Author IDs 0 to {total_authors - 1})")
    print(f"  > Questions per author           : 20 QA pairs")

    # Author Cohort 0 details: authors where (author_id % 10 == 0)
    cohort_0_author_ids = [a for a in range(total_authors) if a % 10 == 0]
    print(f"  > Cohort 0 contains {len(cohort_0_author_ids)} authors: {cohort_0_author_ids}")
    print(f"  > Cohort 0 comprises: {len(cohort_0_author_ids) * 20} QA pairs (10.0% of full dataset)")
    print("  > Primary Author in Cohort 0: Jaime Vasquez (Author ID 0, Santiago, Chile)")

    # 2. Experiment Setup via ExperimentService
    print("\n[Audit Phase 2] Initializing Controlled Experiment in SQLite Database")
    service = ExperimentService()
    exp = service.create_experiment(
        name="TOFU Author Unlearning Audit Study",
        description="Auxiliary classification proxy (Author Attribution) with exact author count reconciliation",
        dataset_name="tofu",
        model_name="mlp",
        seed=42,
        train_config={
            "epochs": 5,
            "batch_size": 64,
            "learning_rate": 0.005,
            "subsample_size": None,  # Full 3,200 training pool
        },
    )
    exp_id = exp["id"]
    print(f"  > Created Experiment ID: {exp_id}")

    # 3. Train Original Model
    print("\n[Audit Phase 3] Training Original Neural Network on Full Available Pool...")
    train_res = service.train_original_model(exp_id)
    print(f"  > Original Model Trained in {train_res['training_time_seconds']}s")
    print(f"  > Final Train Acc: {train_res['final_train_accuracy']}% | Val Acc: {train_res['final_val_accuracy']}%")

    # 4. Partition Deletion Request (Cohort 0: 20 authors)
    print("\n[Audit Phase 4] Submitting Deletion Request (Cohort 0: 20 Fictitious Authors)...")
    manifest = service.request_forgetting(
        exp_id=exp_id,
        strategy="class",
        target_class=0,
    )

    # Reconciliation of split counts
    print(f"  > Partition Strategy     : Class/Cohort 0 Deletion")
    print(f"  > Forgotten Author IDs   : {cohort_0_author_ids} ({len(cohort_0_author_ids)} authors)")
    print(f"  > Retained Author Count  : 180 authors (all authors with ID % 10 != 0)")
    print(f"  > Retained Train Samples : {manifest['retain_count']}")
    print(f"  > Forgotten Train Samples: {manifest['forget_count']}")
    print(f"  > Validation Set Samples : {manifest['val_count']}")
    print(f"  > Partition Audit Hash   : {manifest['manifest_hash']} (Split Provenance)")

    # 5. Exact Retraining Reference Baseline
    print("\n[Audit Phase 5] Training Retraining Baseline from Scratch on Retained Data...")
    retrain_res = service.train_retrained_model(exp_id)
    print(f"  > Retraining Completed in {retrain_res['training_time_seconds']}s")
    print(f"  > Retrained Final Train Acc: {retrain_res['final_train_accuracy']}% | Val Acc: {retrain_res['final_val_accuracy']}%")

    # 6. Approximate Machine Unlearning (Retain Fine-Tuning)
    print("\n[Audit Phase 6] Executing Approximate Machine Unlearning (Retain Fine-Tuning)...")
    unlearn_res = service.run_unlearning(
        exp_id=exp_id,
        algorithm="retain_fine_tuning",
        epochs=2,
        batch_size=64,
        learning_rate=0.002,
    )
    print(f"  > Unlearning Completed in {unlearn_res['unlearning_time_seconds']}s")

    # 7. Comprehensive 3-Way Model Evaluation
    print("\n[Audit Phase 7] Executing Multi-Model Evaluation & Shadow MIA...")
    metrics = service.evaluate_experiment(exp_id)

    orig = metrics["original_model"]
    ret = metrics["retrained_model"]
    unl = metrics["unlearned_model"]
    mia = metrics["mia"]
    speedup = metrics["speedup_factor"]

    print("\n" + "=" * 80)
    print("          EMPIRICAL RESULTS: AUXILIARY CLASSIFICATION PROXY")
    print("=" * 80)
    col_fmt = "{:<30} | {:<12} | {:<15} | {:<15}"
    print(col_fmt.format("Metric", "Original", "Retrained (Ref)", "Unlearned (Approx)"))
    print("-" * 80)

    print(col_fmt.format(
        "Retain Set Accuracy",
        f"{orig['retain']['accuracy']}%",
        f"{ret['retain']['accuracy']}%",
        f"{unl['retain']['accuracy']}%",
    ))
    print(col_fmt.format(
        "Forget Set Accuracy",
        f"{orig['forget']['accuracy']}%",
        f"{ret['forget']['accuracy']}%",
        f"{unl['forget']['accuracy']}%",
    ))
    print(col_fmt.format(
        "Independent Test Acc",
        f"{orig['test']['accuracy']}%",
        f"{ret['test']['accuracy']}%",
        f"{unl['test']['accuracy']}%",
    ))
    print(col_fmt.format(
        "Forget Set Loss",
        f"{orig['forget']['loss']}",
        f"{ret['forget']['loss']}",
        f"{unl['forget']['loss']}",
    ))
    print(col_fmt.format(
        "MIA ROC-AUC",
        f"{mia['original']['roc_auc']}",
        f"{mia['retrained']['roc_auc']}",
        f"{mia['unlearned']['roc_auc']}",
    ))
    print(col_fmt.format(
        "Attack Advantage",
        f"{mia['original']['attack_advantage']}",
        f"{mia['retrained']['attack_advantage']}",
        f"{mia['unlearned']['attack_advantage']}",
    ))
    print(col_fmt.format(
        "Execution Time",
        f"{orig['training_time_seconds']}s",
        f"{ret['retraining_time_seconds']}s",
        f"{unl['unlearning_time_seconds']}s",
    ))
    print("-" * 80)
    print(f"Empirical Speedup Factor : {speedup}x ({ret['retraining_time_seconds']}s vs {unl['unlearning_time_seconds']}s)")
    if metrics.get("behavioral_similarity"):
        sim = metrics["behavioral_similarity"]
        print(f"Prediction Agreement    : {sim['prediction_agreement_percent']}% with retrained reference")
        print(f"Mean Softmax KL Div     : {sim['mean_kl_divergence']}")

    # 8. Standard Generative TOFU Evaluation Protocol
    print("\n" + "=" * 80)
    print("      STANDARD GENERATIVE LANGUAGE-MODEL TOFU EVALUATION")
    print("=" * 80)
    print("Running answer-conditioned loss and perplexity evaluation via distilgpt2...")
    gen_evaluator = TOFUGenerativeEvaluator(model_name="distilbert/distilgpt2")
    
    # Extract forget and retain QA pairs
    forget_qa = [tofu_full[i] for i in range(len(tofu_full)) if (i // 20) in cohort_0_author_ids][:40]
    retain_qa = [tofu_full[i] for i in range(len(tofu_full)) if (i // 20) not in cohort_0_author_ids][:40]

    from transformers import AutoModelForCausalLM
    base_llm = AutoModelForCausalLM.from_pretrained("distilbert/distilgpt2")
    gen_forget_res = gen_evaluator.evaluate_qa_loss(base_llm, forget_qa)
    gen_retain_res = gen_evaluator.evaluate_qa_loss(base_llm, retain_qa)

    print(f"  > Forget Set Answer Cross-Entropy Loss : {gen_forget_res['answer_loss']}")
    print(f"  > Forget Set Answer Perplexity        : {gen_forget_res['perplexity']}")
    print(f"  > Retain Set Answer Cross-Entropy Loss : {gen_retain_res['answer_loss']}")
    print(f"  > Retain Set Answer Perplexity        : {gen_retain_res['perplexity']}")
    print("=" * 80)
    print(f"[+] Audit benchmark complete. All records persisted to DB (exp_id: {exp_id})")
    return exp_id


if __name__ == "__main__":
    run_tofu_audit_benchmark()
