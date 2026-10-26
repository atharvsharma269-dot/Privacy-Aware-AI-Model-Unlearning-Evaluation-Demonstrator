import concurrent.futures
import datetime
import json
import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional, Any
from ..database.db import get_db_connection

logger = logging.getLogger("unlearning.jobs")


class JobService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(JobService, cls).__new__(cls)
                cls._instance._init_service()
            return cls._instance

    def _init_service(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.live_jobs: Dict[str, Dict[str, Any]] = {}

    def create_job(self, experiment_id: str, job_type: str) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()
        job_data = {
            "id": job_id,
            "experiment_id": experiment_id,
            "job_type": job_type,
            "status": "PENDING",
            "progress": 0.0,
            "current_step": "Initialized",
            "logs": [f"[{now}] Job initialized."],
            "error_message": None,
            "result": None,
            "started_at": None,
            "completed_at": None,
        }
        self.live_jobs[job_id] = job_data

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO jobs (id, experiment_id, job_type, status, progress, current_step, logs, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            experiment_id,
            job_type,
            "PENDING",
            0.0,
            "Initialized",
            json.dumps(job_data["logs"]),
            now,
        ))
        conn.commit()
        conn.close()
        return job_id

    def submit_job(self, job_id: str, target_fn: Callable, *args, **kwargs):
        self.executor.submit(self._run_job_wrapper, job_id, target_fn, *args, **kwargs)

    def _run_job_wrapper(self, job_id: str, target_fn: Callable, *args, **kwargs):
        now = datetime.datetime.utcnow().isoformat()
        self.update_job(job_id, status="RUNNING", started_at=now, log_line=f"Starting job execution...")
        try:
            # Provide callback wrapper to update progress
            def step_callback(step_info: Dict[str, Any]):
                prog = step_info.get("progress")
                current_step = step_info.get("current_step") or step_info.get("type", "working")
                log = step_info.get("log")
                self.update_job(job_id, progress=prog, current_step=str(current_step), log_line=log)

            result = target_fn(*args, step_callback=step_callback, **kwargs)
            self.complete_job(job_id, result)
        except Exception as e:
            logger.exception(f"Job {job_id} encountered fatal error")
            self.fail_job(job_id, str(e))

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        log_line: Optional[str] = None,
        started_at: Optional[str] = None,
    ):
        if job_id not in self.live_jobs:
            return

        job = self.live_jobs[job_id]
        if status:
            job["status"] = status
        if progress is not None:
            job["progress"] = min(100.0, max(0.0, float(progress)))
        if current_step:
            job["current_step"] = current_step
        if started_at:
            job["started_at"] = started_at
        if log_line:
            now = datetime.datetime.utcnow().strftime("%H:%M:%S")
            job["logs"].append(f"[{now}] {log_line}")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE jobs
            SET status = ?, progress = ?, current_step = ?, logs = ?
            WHERE id = ?
        """, (
            job["status"],
            job["progress"],
            job["current_step"],
            json.dumps(job["logs"]),
            job_id,
        ))
        conn.commit()
        conn.close()

    def complete_job(self, job_id: str, result: Any):
        if job_id not in self.live_jobs:
            return
        now = datetime.datetime.utcnow().isoformat()
        job = self.live_jobs[job_id]
        job["status"] = "COMPLETED"
        job["progress"] = 100.0
        job["current_step"] = "Completed"
        job["completed_at"] = now
        job["result"] = result
        job["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] Job successfully completed.")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE jobs
            SET status = ?, progress = 100.0, current_step = ?, logs = ?, result = ?, completed_at = ?
            WHERE id = ?
        """, (
            "COMPLETED",
            "Completed",
            json.dumps(job["logs"]),
            json.dumps(result),
            now,
            job_id,
        ))
        conn.commit()
        conn.close()

    def fail_job(self, job_id: str, error_message: str):
        if job_id not in self.live_jobs:
            return
        now = datetime.datetime.utcnow().isoformat()
        job = self.live_jobs[job_id]
        job["status"] = "FAILED"
        job["error_message"] = error_message
        job["completed_at"] = now
        job["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] ERROR: {error_message}")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE jobs
            SET status = ?, logs = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, (
            "FAILED",
            json.dumps(job["logs"]),
            error_message,
            now,
            job_id,
        ))
        # Ensure experiment record is also marked as FAILED so failed jobs never appear successful
        if job.get("experiment_id"):
            c.execute("""
                UPDATE experiments
                SET status = 'FAILED', updated_at = ?
                WHERE id = ?
            """, (now, job["experiment_id"]))
        conn.commit()
        conn.close()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        if job_id in self.live_jobs:
            return self.live_jobs[job_id]

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row["id"],
            "experiment_id": row["experiment_id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "progress": row["progress"],
            "current_step": row["current_step"],
            "logs": json.loads(row["logs"]) if row["logs"] else [],
            "error_message": row["error_message"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }

