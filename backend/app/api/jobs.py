from fastapi import APIRouter, HTTPException
from ..services.job_service import JobService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
job_service = JobService()


@router.get("/{job_id}")
def get_job_status(job_id: str):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

