import os
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.app.services.experiment_service import ExperimentService

def run_e2e_demo():
    print("=" * 60)
    print("[*] Launching End-to-End Real Machine Unlearning Benchmark")
    print("=" * 60)

    service = ExperimentService()

    # 1. Create experiment
    print("\n[Step 1] Creating Experiment...")
    exp = service.create_experiment(
        name="Fashion-MNIST Empirical Unlearning Benchmark",
        description="Controlled study of Retain-set fine-tuning vs Exact Retraining reference",
        dataset_name="fashion_mnist",
        model_name="mlp",
        seed=42,
        train_config={
            "epochs": 4,
            "batch_size": 64,
            "learning_rate": 0.001,
            "subsample_size": 4000,  # Fast laptop execution
        }
    )
    exp_id = exp["id"]
    print(f"Created Experiment ID: {exp_id}")

    # 2. Train Original Model
    print("\n[Step 2] Training Original Model (Stage A)...")
    def log_cb(event):
        if "log" in event:
            print(f"  > {event['log']}")
    train_res = service.train_original_model(exp_id, step_callback=log_cb)
    print(f"Original Training Done in {train_res['training_time_seconds']}s | Test Acc: {train_res['final_test_accuracy']}%")

    # 3. Forgetting Request
    print("\n[Step 3] Submitting Forgetting Request (Stage B)...")
    manifest = service.request_forgetting(
        exp_id=exp_id,
        strategy="random",
        percentage=0.10,
    )
    print(f"Partitioned: Retain={manifest['retain_count']}, Forget={manifest['forget_count']}, Val={manifest['val_count']}")
    print(f"Partition Audit Hash: {manifest['manifest_hash']}")

    # 4. Exact Retraining Baseline
    print("\n[Step 4] Executing Exact Retraining from Scratch (Stage C)...")
    retrain_res = service.train_retrained_model(exp_id, step_callback=log_cb)
    print(f"Exact Retraining Done in {retrain_res['training_time_seconds']}s | Test Acc: {retrain_res['final_test_accuracy']}%")

    # 5. Approximate Machine Unlearning
    print("\n[Step 5] Executing Approximate Machine Unlearning (Stage D)...")
    unlearn_res = service.run_unlearning(
        exp_id=exp_id,
        algorithm="retain_fine_tuning",
        epochs=2,
        batch_size=64,
        learning_rate=0.0003,
        step_callback=log_cb,
    )
    print(f"Unlearning Done in {unlearn_res['unlearning_time_seconds']}s")

    # 6. Comprehensive 3-Way Evaluation
    print("\n[Step 6] Running 3-Way Evaluation & MIA Attacks (Stage E)...")
    metrics = service.evaluate_experiment(exp_id, step_callback=log_cb)

    orig = metrics["original_model"]
    ret = metrics["retrained_model"]
    unl = metrics["unlearned_model"]
    mia = metrics["mia"]
    speedup = metrics["speedup_factor"]

    print("\n" + "=" * 60)
    print("[*] EMPIRICAL BENCHMARK RESULTS")
    print("=" * 60)
    print(f"{'Metric':<28} | {'Original':<10} | {'Retrained':<10} | {'Unlearned':<10}")
    print("-" * 66)
    print(f"{'Retain Set Accuracy (%)':<28} | {orig['retain']['accuracy']:<10} | {ret['retain']['accuracy']:<10} | {unl['retain']['accuracy']:<10}")
    print(f"{'Forget Set Accuracy (%)':<28} | {orig['forget']['accuracy']:<10} | {ret['forget']['accuracy']:<10} | {unl['forget']['accuracy']:<10}")
    print(f"{'Test Set Accuracy (%)':<28} | {orig['test']['accuracy']:<10} | {ret['test']['accuracy']:<10} | {unl['test']['accuracy']:<10}")
    print(f"{'Forget Set Loss':<28} | {orig['forget']['loss']:<10} | {ret['forget']['loss']:<10} | {unl['forget']['loss']:<10}")
    print(f"{'MIA Attack ROC-AUC':<28} | {mia['original']['roc_auc']:<10} | {mia['retrained']['roc_auc']:<10} | {mia['unlearned']['roc_auc']:<10}")
    print(f"{'Execution Time (s)':<28} | {orig['training_time_seconds']:<10} | {ret['retraining_time_seconds']:<10} | {unl['unlearning_time_seconds']:<10}")
    print("-" * 66)
    print(f"[Speedup] Computational Speedup Factor: {speedup}x")
    print(f"[Degradation] Test Utility Degradation: {unl['utility_degradation_pct']}%")
    if metrics.get("behavioral_similarity"):
        sim = metrics["behavioral_similarity"]
        print(f"[Agreement] Prediction Agreement: {sim['prediction_agreement_percent']}%")
        print(f"[Divergence] Mean KL Divergence: {sim['mean_kl_divergence']}")

    print("\n" + "=" * 60)
    print("[*] EVIDENCE-BASED RESEARCH INSIGHTS")
    print("=" * 60)
    exp_final = service.get_experiment(exp_id)
    insights = exp_final["insights"]
    print(f"Executive Recommendation: {insights['summary_recommendation']}")
    print(f"Forgetting Analysis: {insights['forgetting_effectiveness']}")
    print(f"Privacy (MIA) Analysis: {insights['privacy_risk_mia']}")
    print(f"Efficiency Analysis: {insights['computational_efficiency']}")
    print("\n[DONE] End-to-End Experiment Successfully Completed and Persisted!")


if __name__ == "__main__":
    run_e2e_demo()

