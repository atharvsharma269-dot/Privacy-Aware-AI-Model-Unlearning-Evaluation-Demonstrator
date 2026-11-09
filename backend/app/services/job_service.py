import concurrent.futures
import datetime
import json
import logging
import threading
import uuid
from typing import Callable, Dict, List, Optional, Any
from ..database.db import get_db_connection
from ml.utils.exceptions import CancellationError

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
        self._cancel_events: Dict[str, threading.Event] = {}
        self._futures: Dict[str, concurrent.futures.Future] = {}
        self._recover_interrupted_jobs_on_startup()

    def _recover_interrupted_jobs_on_startup(self):
        """
        Phase 11 resilience: Scans database on startup for uncompleted jobs interrupted
        by a server restart or crash. Safely marks them INTERRUPTED without corrupting checkpoints.
        """
        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                SELECT id, experiment_id, status, logs FROM jobs
                WHERE status IN ('QUEUED', 'PENDING', 'RUNNING', 'CANCELLATION_REQUESTED')
            """)
            interrupted = c.fetchall()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for row in interrupted:
                job_id = row["id"]
                exp_id = row["experiment_id"]
                try:
                    logs = json.loads(row["logs"]) if row["logs"] else []
                except Exception:
                    logs = []
                logs.append(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S')}] Server restarted. Job safely marked INTERRUPTED.")

                c.execute("""
                    UPDATE jobs
                    SET status = 'INTERRUPTED', current_step = 'Interrupted by server restart',
                        logs = ?, completed_at = ?, error_message = 'Backend process restarted during execution'
                    WHERE id = ?
                """, (json.dumps(logs), now, job_id))

                # Update experiment status if it was active
                c.execute("""
                    UPDATE experiments
                    SET status = 'INTERRUPTED', updated_at = ?
                    WHERE id = ? AND status IN ('TRAINING', 'UNLEARNING', 'EVALUATING')
                """, (now, exp_id))
                logger.warning(f"Recovered interrupted job {job_id} on startup.")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error during job recovery on startup: {e}")

    def get_active_job_for_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns active job for this experiment if one is currently QUEUED, PENDING, RUNNING, or CANCELLATION_REQUESTED.
        Prevents duplicate concurrent job submissions on the same experiment.
        """
        for job in self.live_jobs.values():
            if job.get("experiment_id") == experiment_id and job.get("status") in [
                "QUEUED", "PENDING", "RUNNING", "CANCELLATION_REQUESTED"
            ]:
                return job

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM jobs
            WHERE experiment_id = ? AND status IN ('QUEUED', 'PENDING', 'RUNNING', 'CANCELLATION_REQUESTED')
            ORDER BY started_at DESC LIMIT 1
        """, (experiment_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return self.get_job(row["id"])
        return None

    def create_job(self, experiment_id: str, job_type: str) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.datetime.utcnow().isoformat()
        job_data = {
            "id": job_id,
            "experiment_id": experiment_id,
            "job_type": job_type,
            "status": "QUEUED",
            "progress": 0.0,
            "current_step": "Queued in runner queue",
            "logs": [f"[{now}] Job {job_id} queued for execution."],
            "telemetry": [],
            "current_telemetry": None,
            "error_message": None,
            "result": None,
            "started_at": None,
            "completed_at": None,
        }
        self.live_jobs[job_id] = job_data
        self._cancel_events[job_id] = threading.Event()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO jobs (id, experiment_id, job_type, status, progress, current_step, logs, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            experiment_id,
            job_type,
            "QUEUED",
            0.0,
            "Queued",
            json.dumps(job_data["logs"]),
            now,
        ))
        conn.commit()
        conn.close()
        return job_id

    def submit_job(self, job_id: str, target_fn: Callable, *args, **kwargs):
        future = self.executor.submit(self._run_job_wrapper, job_id, target_fn, *args, **kwargs)
        self._futures[job_id] = future

    def is_cancellation_requested(self, job_id: str) -> bool:
        if job_id in self._cancel_events and self._cancel_events[job_id].is_set():
            return True
        if job_id in self.live_jobs:
            return self.live_jobs[job_id].get("status") in ["CANCELLATION_REQUESTED", "CANCELLED"]
        return False

    def request_cancellation(self, job_id: str) -> Dict[str, Any]:
        """
        Initiates cancellation request.
        If queued: transitions immediately to CANCELLED.
        If running: transitions to CANCELLATION_REQUESTED and signals cooperative PyTorch loop.
        """
        job = self.live_jobs.get(job_id)
        if not job:
            job = self.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

        current_status = job.get("status")

        if current_status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return {
                "job_id": job_id,
                "status": current_status,
                "message": f"Job {job_id} is already terminal ({current_status}).",
            }

        if current_status in ["QUEUED", "PENDING"]:
            # Cancel before worker starts
            future = self._futures.get(job_id)
            if future:
                future.cancel()
            now = datetime.datetime.utcnow().isoformat()
            self._cancel_events[job_id].set()
            job["status"] = "CANCELLED"
            job["completed_at"] = now
            job["current_step"] = "Cancelled before start"
            job["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] Job cancelled while queued.")

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE jobs
                SET status = 'CANCELLED', current_step = 'Cancelled before start', logs = ?, completed_at = ?
                WHERE id = ?
            """, (json.dumps(job["logs"]), now, job_id))
            conn.commit()
            conn.close()
            logger.info(f"Job {job_id} cancelled while queued.")
            return {
                "job_id": job_id,
                "status": "CANCELLED",
                "message": "Job cancelled before execution started.",
            }

        # Status is RUNNING: signal cancellation
        self._cancel_events[job_id].set()
        now_str = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.update_job(
            job_id,
            status="CANCELLATION_REQUESTED",
            current_step="Cancellation requested - halting at next batch boundary",
            log_line=f"CANCELLATION_REQUESTED: User requested abort. Awaiting safe batch boundary stop...",
        )
        logger.info(f"Cancellation requested for running job {job_id}.")
        return {
            "job_id": job_id,
            "status": "CANCELLATION_REQUESTED",
            "message": "Cancellation signal sent. Computation will stop safely at the next batch boundary.",
        }

    def cancel_job_confirmed(self, job_id: str, reason: str = "Execution cancelled by user"):
        """
        Called when the computation has safely stopped and confirmed cancellation.
        """
        if job_id not in self.live_jobs:
            return
        now = datetime.datetime.utcnow().isoformat()
        job = self.live_jobs[job_id]
        job["status"] = "CANCELLED"
        job["current_step"] = "Cancelled"
        job["completed_at"] = now
        job["error_message"] = reason
        job["logs"].append(f"[{datetime.datetime.utcnow().strftime('%H:%M:%S')}] CANCELLED: {reason}. Resources released.")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE jobs
            SET status = 'CANCELLED', current_step = 'Cancelled', logs = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, (
            json.dumps(job["logs"]),
            reason,
            now,
            job_id,
        ))
        conn.commit()
        conn.close()
        logger.info(f"Job {job_id} confirmed CANCELLED: {reason}")

    def _run_job_wrapper(self, job_id: str, target_fn: Callable, *args, **kwargs):
        now = datetime.datetime.utcnow().isoformat()
        if self.is_cancellation_requested(job_id):
            self.cancel_job_confirmed(job_id, "Cancelled before worker began execution")
            return

        self.update_job(job_id, status="RUNNING", started_at=now, log_line="Starting worker execution...")
        try:
            def cancel_check() -> bool:
                return self.is_cancellation_requested(job_id)

            def step_callback(step_info: Dict[str, Any]):
                prog = step_info.get("progress")
                current_step = step_info.get("current_step") or step_info.get("type", "working")
                log = step_info.get("log")
                telemetry_data = step_info.get("data")
                current_telemetry = step_info.get("current_telemetry") or telemetry_data
                self.update_job(
                    job_id,
                    progress=prog,
                    current_step=str(current_step),
                    log_line=log,
                    telemetry_data=telemetry_data,
                    current_telemetry=current_telemetry,
                )

            result = target_fn(*args, step_callback=step_callback, cancel_check=cancel_check, **kwargs)
            self.complete_job(job_id, result)
        except CancellationError as ce:
            logger.info(f"Job {job_id} gracefully aborted via CancellationError: {ce}")
            self.cancel_job_confirmed(job_id, str(ce))
        except Exception as e:
            logger.exception(f"Job {job_id} encountered fatal error")
            self.fail_job(job_id, str(e))
        finally:
            self._cancel_events.pop(job_id, None)
            self._futures.pop(job_id, None)

    def update_job(
        self,
        job_id: str,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        log_line: Optional[str] = None,
        started_at: Optional[str] = None,
        telemetry_data: Optional[Dict[str, Any]] = None,
        current_telemetry: Optional[Dict[str, Any]] = None,
    ):
        if job_id not in self.live_jobs:
            return

        job = self.live_jobs[job_id]
        if status and job["status"] != "CANCELLATION_REQUESTED":
            job["status"] = status
        elif status == "CANCELLATION_REQUESTED":
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
        if telemetry_data:
            if "telemetry" not in job:
                job["telemetry"] = []
            job["telemetry"].append(telemetry_data)
        if current_telemetry:
            job["current_telemetry"] = current_telemetry

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
        if "telemetry" not in job:
            job["telemetry"] = []
        if isinstance(result, dict) and "history" in result and not job["telemetry"]:
            job["telemetry"] = result["history"]
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
            "telemetry": json.loads(row["result"]).get("history", []) if row["result"] and isinstance(json.loads(row["result"]), dict) and "history" in json.loads(row["result"]) else [],
            "current_telemetry": None,
            "error_message": row["error_message"],
            "result": json.loads(row["result"]) if row["result"] else None,
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }

