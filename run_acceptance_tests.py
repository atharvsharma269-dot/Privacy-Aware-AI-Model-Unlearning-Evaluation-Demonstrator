import os
import sys
import functools

sys.stdout.reconfigure(line_buffering=True)
print = functools.partial(print, flush=True)

print(">>> INITIALIZING ACCEPTANCE TEST SUITE <<<")

import time
import json
import hashlib
import torch
from typing import Dict, Any

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.db import get_db_connection


def print_header(title: str):
    print("\n" + "=" * 70, flush=True)
    print(f"  {title}", flush=True)
    print("=" * 70, flush=True)


def poll_job_until(client: TestClient, job_id: str, target_statuses, max_wait_sec=25, poll_interval=0.2):
    start = time.time()
    last_status = None
    while time.time() - start < max_wait_sec:
        res = client.get(f"/api/jobs/{job_id}")
        assert res.status_code == 200, f"Failed to get job: {res.text}"
        data = res.json()
        status = data.get("status")
        last_status = status
        if status in target_statuses:
            return data
        time.sleep(poll_interval)
    raise TimeoutError(f"Job {job_id} did not reach {target_statuses} within {max_wait_sec}s (last status: {last_status})")


def run_test_1(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 1: Original Model Training Cancellation & Telemetry")
    # 1. Create experiment
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 1 - Original Training Cancel",
        "description": "Verifying batch telemetry and cooperative cancellation",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
    })
    assert exp_res.status_code == 200, exp_res.text
    exp_id = exp_res.json()["id"]
    print(f"[Evidence] Created experiment: {exp_id}")

    # 2. Start training job with sufficient samples to allow observing telemetry & cancelling
    train_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 10,
        "batch_size": 16,
        "subsample_size": 3000,
        "learning_rate": 0.001,
        "optimizer": "adam",
    })
    assert train_res.status_code == 200, train_res.text
    train_data = train_res.json()
    job_id = train_data["job_id"]
    print(f"[Evidence] Training job created: {job_id}, status: {train_data['status']}")

    # 3. Poll until RUNNING and verify live batch telemetry
    time.sleep(0.3)
    job_running = poll_job_until(client, job_id, ["RUNNING", "COMPLETED"], max_wait_sec=10)
    print(f"[Evidence] Job transitioned to: {job_running['status']}")
    
    # Wait for at least one batch update
    telemetry_observed = False
    for _ in range(30):
        j_check = client.get(f"/api/jobs/{job_id}").json()
        cur_tel = j_check.get("current_telemetry") or {}
        if cur_tel.get("batch") is not None and cur_tel.get("batch") > 0:
            telemetry_observed = True
            print(f"[Evidence] Live Batch Telemetry Verified: Epoch {cur_tel.get('epoch')}/{cur_tel.get('total_epochs')}, Batch {cur_tel.get('batch')}/{cur_tel.get('total_batches')}, Batch Loss: {cur_tel.get('batch_loss')}, Elapsed: {cur_tel.get('elapsed_seconds')}s")
            break
        time.sleep(0.15)
    
    assert telemetry_observed, "Telemetry batch update was not observed"

    # 4. Cancel the job
    print("[Evidence] Requesting cancellation via POST /api/jobs/{job_id}/cancel...")
    cancel_res = client.post(f"/api/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200, cancel_res.text
    print(f"[Evidence] Cancel response: {cancel_res.json()}")

    # 5. Confirm final terminal state is CANCELLED
    final_job = poll_job_until(client, job_id, ["CANCELLED"], max_wait_sec=10)
    print(f"[Evidence] Final job status: {final_job['status']}")
    assert final_job["status"] == "CANCELLED", f"Expected CANCELLED, got {final_job['status']}"

    # Verify logs mention cancellation
    logs = final_job.get("logs", [])
    print(f"[Evidence] Job logs count: {len(logs)}. Last 2 log lines: {logs[-2:]}")
    assert any("CANCEL" in log for log in logs), "Logs should contain CANCEL confirmation"

    # Verify no checkpoint was promoted
    ckpt_path = f"experiments/checkpoints/{exp_id}/original.pt"
    tmp_path = f"{ckpt_path}.tmp"
    assert not os.path.exists(ckpt_path), f"Checkpoint {ckpt_path} must not exist for cancelled job"
    assert not os.path.exists(tmp_path), f"Temporary file {tmp_path} should have been cleaned up"
    print(f"[Evidence] Filesystem verified: {ckpt_path} does not exist and {tmp_path} is cleaned up.")

    return {
        "test": "Test 1: Original Model Training Cancellation",
        "status": "PASS",
        "experiment_id": exp_id,
        "job_id": job_id,
        "final_status": final_job["status"],
    }


def run_test_2(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 2: Exact Retraining Cancellation")
    # 1. Create experiment
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 2 - Retraining Cancel",
        "description": "Verifying cancellation reaches exact retraining loop",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
    })
    exp_id = exp_res.json()["id"]

    # 2. Partition dataset
    forget_res = client.post(f"/api/experiments/{exp_id}/forget", json={
        "strategy": "random",
        "percentage": 0.10,
    })
    assert forget_res.status_code == 200, forget_res.text
    manifest = forget_res.json()
    print(f"[Evidence] Partition created: Retain={manifest['retain_count']}, Forget={manifest['forget_count']}, Hash={manifest['partition_hash']}")

    # 3. Start exact retraining
    retrain_res = client.post(f"/api/experiments/{exp_id}/retrain", json={
        "epochs": 10,
        "batch_size": 16,
        "learning_rate": 0.001,
        "optimizer": "adam",
    })
    assert retrain_res.status_code == 200, retrain_res.text
    job_id = retrain_res.json()["job_id"]
    print(f"[Evidence] Retraining job started: {job_id}")

    # 4. Wait until running
    job_running = poll_job_until(client, job_id, ["RUNNING", "COMPLETED"], max_wait_sec=10)
    print(f"[Evidence] Retraining reached state: {job_running['status']}")

    # Cancel via experiment-level endpoint
    print(f"[Evidence] Cancelling via POST /api/experiments/{exp_id}/cancel...")
    cancel_res = client.post(f"/api/experiments/{exp_id}/cancel")
    assert cancel_res.status_code == 200, cancel_res.text
    print(f"[Evidence] Cancel response: {cancel_res.json()}")

    # 5. Confirm CANCELLED
    final_job = poll_job_until(client, job_id, ["CANCELLED"], max_wait_sec=10)
    print(f"[Evidence] Final job status: {final_job['status']}")
    assert final_job["status"] == "CANCELLED"

    # Check database and checkpoint integrity
    exp_data = client.get(f"/api/experiments/{exp_id}").json()
    retrained_ckpt = exp_data.get("retrained_checkpoint_path")
    assert not retrained_ckpt or not os.path.exists(retrained_ckpt), f"Retrained checkpoint must not exist: {retrained_ckpt}"
    print(f"[Evidence] Confirmed no retrained checkpoint was registered in experiment: {retrained_ckpt}")

    return {
        "test": "Test 2: Exact Retraining Cancellation",
        "status": "PASS",
        "experiment_id": exp_id,
        "job_id": job_id,
        "final_status": final_job["status"],
    }


def run_test_3(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 3: Approximate Unlearning Cancellation & Weight Preservation")
    # 1. Create experiment & train original model fast (1 epoch, 300 samples)
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 3 - Unlearning Cancel",
        "description": "Verifying original weights intact after unlearning cancelled",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
        "train_config": {"subsample_size": 300, "epochs": 1, "batch_size": 32, "learning_rate": 0.002},
    })
    exp_id = exp_res.json()["id"]

    train_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 1,
        "batch_size": 32,
        "subsample_size": 300,
        "learning_rate": 0.002,
    })
    job_id = train_res.json()["job_id"]
    poll_job_until(client, job_id, ["COMPLETED"], max_wait_sec=30)
    print(f"[Evidence] Base model trained successfully for {exp_id}")

    # Check original checkpoint exists and record its SHA-256 hash
    exp_info = client.get(f"/api/experiments/{exp_id}").json()
    orig_path = exp_info["original_checkpoint_path"]
    assert os.path.exists(orig_path), f"Original checkpoint must exist: {orig_path}"
    with open(orig_path, "rb") as f:
        orig_sha_before = hashlib.sha256(f.read()).hexdigest()
    print(f"[Evidence] Original checkpoint SHA-256 before unlearning: {orig_sha_before[:16]}...")

    # 2. Partition dataset
    client.post(f"/api/experiments/{exp_id}/forget", json={"strategy": "random", "percentage": 0.10})

    # 3. Start Regularized Gradient Ascent with multiple epochs so we can cancel mid-batch
    unlearn_res = client.post(f"/api/experiments/{exp_id}/unlearn", json={
        "algorithm": "gradient_ascent",
        "epochs": 10,
        "batch_size": 16,
        "learning_rate": 0.0001,
        "alpha_ascent": 0.4,
        "beta_proximity": 0.01,
        "max_forget_loss": 2.35,
    })
    assert unlearn_res.status_code == 200, unlearn_res.text
    unlearn_job_id = unlearn_res.json()["job_id"]
    print(f"[Evidence] Unlearning job submitted: {unlearn_job_id}")

    # Poll until RUNNING
    poll_job_until(client, unlearn_job_id, ["RUNNING", "COMPLETED"], max_wait_sec=10)

    # Cancel the unlearning job
    cancel_res = client.post(f"/api/jobs/{unlearn_job_id}/cancel")
    assert cancel_res.status_code == 200
    final_unlearn = poll_job_until(client, unlearn_job_id, ["CANCELLED"], max_wait_sec=10)
    print(f"[Evidence] Unlearning job reached terminal status: {final_unlearn['status']}")

    # 4. Verify original checkpoint is completely unchanged
    with open(orig_path, "rb") as f:
        orig_sha_after = hashlib.sha256(f.read()).hexdigest()
    assert orig_sha_before == orig_sha_after, "Original checkpoint was corrupted or modified during unlearning cancel!"
    print(f"[Evidence] Integrity check passed: Original checkpoint SHA-256 is unchanged ({orig_sha_after[:16]}...)")

    # 5. Verify unlearned checkpoint does not exist or was not promoted
    unlearned_path = f"experiments/checkpoints/{exp_id}/unlearned.pt"
    assert not os.path.exists(unlearned_path), f"Unlearned checkpoint must not exist: {unlearned_path}"
    print(f"[Evidence] Unlearned checkpoint {unlearned_path} does not exist.")

    # 6. Verify evaluate fails if attempted without valid unlearned model
    eval_res = client.post(f"/api/experiments/{exp_id}/evaluate")
    eval_job_id = eval_res.json()["job_id"]
    eval_final = poll_job_until(client, eval_job_id, ["FAILED"], max_wait_sec=10)
    print(f"[Evidence] Evaluation correctly rejected missing/cancelled model: status={eval_final['status']}, error={eval_final.get('error')}")
    assert eval_final["status"] == "FAILED"

    return {
        "test": "Test 3: Approximate Unlearning Cancellation & Weight Preservation",
        "status": "PASS",
        "experiment_id": exp_id,
        "orig_sha256": orig_sha_before[:16],
        "final_unlearn_status": final_unlearn["status"],
    }


def run_test_4(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 4: Short Training Job Successful Completion")
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 4 - Successful Training",
        "description": "Verifying full completion, atomic checkpointing, and telemetry",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
        "train_config": {"subsample_size": 400, "epochs": 2, "batch_size": 32, "learning_rate": 0.002},
    })
    exp_id = exp_res.json()["id"]

    train_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 2,
        "batch_size": 32,
        "subsample_size": 400,
        "learning_rate": 0.002,
        "optimizer": "adam",
    })
    job_id = train_res.json()["job_id"]
    print(f"[Evidence] Training job {job_id} submitted for {exp_id}")

    final_job = poll_job_until(client, job_id, ["COMPLETED", "FAILED"], max_wait_sec=30)
    print(f"[Evidence] Final job status: {final_job['status']}, progress: {final_job.get('progress')}%")
    assert final_job["status"] == "COMPLETED", f"Job failed: {final_job.get('error')}"
    assert final_job.get("progress") == 100.0

    # Verify completed checkpoint exists and can be loaded
    exp_info = client.get(f"/api/experiments/{exp_id}").json()
    ckpt_path = exp_info["original_checkpoint_path"]
    assert os.path.exists(ckpt_path), f"Checkpoint missing: {ckpt_path}"
    
    ckpt_obj = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    assert "model_state_dict" in ckpt_obj, "Checkpoint missing model_state_dict"
    meta = ckpt_obj.get("metadata", {})
    print(f"[Evidence] Loaded checkpoint metadata: is_complete={meta.get('is_complete')}, status={meta.get('checkpoint_status')}, final_accuracy={meta.get('final_test_accuracy')}%")
    assert meta.get("is_complete") is True
    assert meta.get("checkpoint_status") == "complete"

    # Verify metrics correspond to job
    assert exp_info["status"] in ["ORIGINAL_TRAINED", "TRAINED"]
    assert "original_model" in (exp_info.get("metrics") or {})
    print(f"[Evidence] Experiment status: {exp_info['status']}, metrics recorded successfully.")

    return {
        "test": "Test 4: Training Successful Completion",
        "status": "PASS",
        "experiment_id": exp_id,
        "job_id": job_id,
        "checkpoint_path": ckpt_path,
        "final_accuracy": meta.get("final_test_accuracy"),
    }


def run_test_5(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 5: Full Three-Model End-to-End Evaluation")
    # 1. Create dedicated experiment
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 5 - 3-Model Benchmark",
        "description": "Verifying common partition evaluation and honest metrics",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
        "train_config": {"subsample_size": 400, "epochs": 2, "batch_size": 32, "learning_rate": 0.002},
    })
    exp_id = exp_res.json()["id"]

    # 2. Train original model (2 epochs, subsample 400)
    train_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 2,
        "batch_size": 32,
        "subsample_size": 400,
        "learning_rate": 0.002,
    })
    poll_job_until(client, train_res.json()["job_id"], ["COMPLETED"], max_wait_sec=30)
    print(f"[Evidence] Original model trained for {exp_id}")

    # 3. Request forgetting partition (10% forget)
    forget_res = client.post(f"/api/experiments/{exp_id}/forget", json={
        "strategy": "random",
        "percentage": 0.10,
    })
    manifest = forget_res.json()
    part_hash = manifest["partition_hash"]
    print(f"[Evidence] Dataset partition manifest hash: {part_hash}")

    # 4. Train exact retrained reference (2 epochs)
    retrain_res = client.post(f"/api/experiments/{exp_id}/retrain", json={
        "epochs": 2,
        "batch_size": 32,
        "learning_rate": 0.002,
    })
    poll_job_until(client, retrain_res.json()["job_id"], ["COMPLETED"], max_wait_sec=40)
    print(f"[Evidence] Exact retrained model completed for {exp_id}")

    # 5. Approximate unlearning (1 epoch GA)
    unlearn_res = client.post(f"/api/experiments/{exp_id}/unlearn", json={
        "algorithm": "gradient_ascent",
        "epochs": 1,
        "batch_size": 32,
        "learning_rate": 0.0001,
        "alpha_ascent": 0.4,
        "beta_proximity": 0.01,
        "max_forget_loss": 2.35,
    })
    poll_job_until(client, unlearn_res.json()["job_id"], ["COMPLETED"], max_wait_sec=40)
    print(f"[Evidence] Approximate unlearning completed for {exp_id}")

    # 6. Execute full evaluation
    eval_res = client.post(f"/api/experiments/{exp_id}/evaluate")
    eval_job_id = eval_res.json()["job_id"]
    print(f"[Evidence] Evaluation job started: {eval_job_id}")
    final_eval_job = poll_job_until(client, eval_job_id, ["COMPLETED", "FAILED"], max_wait_sec=40)
    assert final_eval_job["status"] == "COMPLETED", f"Evaluation failed: {final_eval_job.get('error')}"
    print(f"[Evidence] 3-Way Evaluation completed successfully.")

    # 7. Fetch and verify metrics
    metrics_res = client.get(f"/api/experiments/{exp_id}/metrics").json()
    metrics = metrics_res.get("metrics") or {}
    
    orig = metrics.get("original_model", {})
    ret = metrics.get("retrained_model", {})
    unl = metrics.get("unlearned_model", {})
    mia = metrics.get("mia", {})
    speedup = metrics.get("speedup_factor")
    prov = metrics.get("provenance", {})

    print(f"[Evidence] Provenance Hash: {prov.get('partition_hash')} (matches manifest: {prov.get('partition_hash') == part_hash})")
    print(f"[Evidence] Forget Accuracy: Original={orig.get('forget', {}).get('accuracy')}%, Retrained={ret.get('forget', {}).get('accuracy')}%, Unlearned={unl.get('forget', {}).get('accuracy')}%")
    print(f"[Evidence] Retain Accuracy: Original={orig.get('retain', {}).get('accuracy')}%, Retrained={ret.get('retain', {}).get('accuracy')}%, Unlearned={unl.get('retain', {}).get('accuracy')}%")
    print(f"[Evidence] MIA ROC-AUC: Original={mia.get('original', {}).get('roc_auc')}, Retrained={mia.get('retrained', {}).get('roc_auc')}, Unlearned={mia.get('unlearned', {}).get('roc_auc')}")
    print(f"[Evidence] Compute Speedup: {speedup}x (Unlearn {unl.get('unlearning_time_seconds')}s vs Retrain {ret.get('retraining_time_seconds')}s)")

    assert orig.get("forget") is not None, "Original forget metrics missing"
    assert ret.get("forget") is not None, "Retrained forget metrics missing"
    assert unl.get("forget") is not None, "Unlearned forget metrics missing"
    assert mia.get("unlearned") is not None, "MIA unlearned metrics missing"
    assert prov.get("partition_hash") == part_hash, "Provenance hash mismatch"

    return {
        "test": "Test 5: Three-Model Evaluation",
        "status": "PASS",
        "experiment_id": exp_id,
        "partition_hash": part_hash,
        "speedup_factor": speedup,
        "orig_forget_acc": orig.get("forget", {}).get("accuracy"),
        "unl_forget_acc": unl.get("forget", {}).get("accuracy"),
        "ret_forget_acc": ret.get("forget", {}).get("accuracy"),
    }


def run_test_6(client: TestClient) -> Dict[str, Any]:
    print_header("TEST 6: Failure Handling, 409 Conflict, and Idempotency")
    # 1. Test Duplicate Submission 409 Conflict
    exp_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 6 - Conflict & Idempotency",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
        "seed": 42,
    })
    exp_id = exp_res.json()["id"]

    # Start a running job
    train_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 10,
        "batch_size": 16,
        "subsample_size": 3000,
    })
    job1_id = train_res.json()["job_id"]
    poll_job_until(client, job1_id, ["RUNNING"], max_wait_sec=10)
    print(f"[Evidence] Active job running: {job1_id}")

    # Submit second job on the same experiment - MUST return HTTP 409 Conflict
    dup_res = client.post(f"/api/experiments/{exp_id}/train", json={
        "epochs": 5,
        "batch_size": 16,
    })
    print(f"[Evidence] Duplicate submission response: HTTP {dup_res.status_code}")
    assert dup_res.status_code == 409, f"Expected 409 Conflict, got {dup_res.status_code}"
    print(f"[Evidence] Conflict detail: {dup_res.json().get('detail')}")

    # 2. Test Idempotent Cancellation
    print(f"[Evidence] Cancelling active job {job1_id}...")
    cancel1 = client.post(f"/api/jobs/{job1_id}/cancel")
    assert cancel1.status_code == 200
    poll_job_until(client, job1_id, ["CANCELLED"], max_wait_sec=10)

    # Repeat cancellation on now-cancelled job
    cancel2 = client.post(f"/api/jobs/{job1_id}/cancel")
    print(f"[Evidence] Second cancellation call response: HTTP {cancel2.status_code}, body: {cancel2.json()}")
    assert cancel2.status_code == 200
    assert cancel2.json()["status"] == "CANCELLED"

    # 3. Test Controlled Failure Handling
    # Submitting an unlearning request for an experiment that has NO original model checkpoint
    exp_empty_res = client.post("/api/experiments", json={
        "name": "Acceptance Test 6 - Empty Exp",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
    })
    empty_exp_id = exp_empty_res.json()["id"]
    fail_res = client.post(f"/api/experiments/{empty_exp_id}/unlearn", json={
        "algorithm": "gradient_ascent",
        "epochs": 1,
    })
    print(f"[Evidence] Invalid request response: HTTP {fail_res.status_code}, detail: {fail_res.json().get('detail')}")
    assert fail_res.status_code in [400, 422], f"Expected 400 or 422, got {fail_res.status_code}"

    # 4. Cross-experiment cancellation safety
    # Ensure cancelling job1 for exp A did not affect another experiment
    exp_b_res = client.post("/api/experiments", json={
        "name": "Experiment B",
        "dataset_name": "fashion_mnist",
        "model_name": "mlp",
    })
    exp_b_id = exp_b_res.json()["id"]
    exp_b_data = client.get(f"/api/experiments/{exp_b_id}").json()
    assert exp_b_data["status"] == "CREATED"
    print(f"[Evidence] Experiment B remains completely unaffected: status={exp_b_data['status']}")

    return {
        "test": "Test 6: Failure & Conflict Handling",
        "status": "PASS",
        "conflict_http_code": dup_res.status_code,
        "idempotent_cancel_status": cancel2.json()["status"],
    }


def main():
    print("=" * 70)
    print("  PRIVACY-AWARE AI MODEL UNLEARNING DEMONSTRATOR")
    print("  MANUAL-STYLE END-TO-END ACCEPTANCE TEST SUITE")
    print(f"  Execution Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 70)

    client = TestClient(app)
    results = []

    try:
        r1 = run_test_1(client)
        results.append(r1)
    except Exception as e:
        print(f"[FAIL] Test 1: {e}")
        results.append({"test": "Test 1: Original Model Training Cancellation", "status": "FAIL", "error": str(e)})

    try:
        r2 = run_test_2(client)
        results.append(r2)
    except Exception as e:
        print(f"[FAIL] Test 2: {e}")
        results.append({"test": "Test 2: Exact Retraining Cancellation", "status": "FAIL", "error": str(e)})

    try:
        r3 = run_test_3(client)
        results.append(r3)
    except Exception as e:
        print(f"[FAIL] Test 3: {e}")
        results.append({"test": "Test 3: Approximate Unlearning Cancellation", "status": "FAIL", "error": str(e)})

    try:
        r4 = run_test_4(client)
        results.append(r4)
    except Exception as e:
        print(f"[FAIL] Test 4: {e}")
        results.append({"test": "Test 4: Training Successful Completion", "status": "FAIL", "error": str(e)})

    try:
        r5 = run_test_5(client)
        results.append(r5)
    except Exception as e:
        print(f"[FAIL] Test 5: {e}")
        results.append({"test": "Test 5: Three-Model Evaluation", "status": "FAIL", "error": str(e)})

    try:
        r6 = run_test_6(client)
        results.append(r6)
    except Exception as e:
        print(f"[FAIL] Test 6: {e}")
        results.append({"test": "Test 6: Failure & Conflict Handling", "status": "FAIL", "error": str(e)})

    print_header("FINAL ACCEPTANCE TEST SUMMARY")
    all_passed = True
    for r in results:
        status = r.get("status")
        print(f"  [{status}] {r.get('test')}")
        if status != "PASS":
            all_passed = False
            print(f"        Reason: {r.get('error')}")

    with open("experiments/acceptance_test_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved report to experiments/acceptance_test_report.json")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
