import logging
from fastapi import APIRouter, HTTPException
from ..services.job_service import JobService

logger = logging.getLogger("unlearning.jobs.api")
router = APIRouter(prefix="/api/jobs", tags=["jobs"])
job_service = JobService()


@router.get("/{job_id}")
def get_job_status(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    logger.info(f"[API] Cancellation endpoint invoked for job: {job_id}")
    try:
        res = job_service.request_cancellation(job_id)
        return res
    except ValueError as e:
        logger.warning(f"[API] Cancel request failed for {job_id}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"[API] Error cancelling job {job_id}")
        raise HTTPException(status_code=500, detail=str(e))

