from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from ..schemas.schemas import (
    ExperimentCreate,
    ForgettingRequest,
    RetrainRequest,
    UnlearnRequest,
    TrainConfig,
)
from ..services.experiment_service import ExperimentService
from ..services.job_service import JobService

router = APIRouter(prefix="/api/experiments", tags=["experiments"])
exp_service = ExperimentService()
job_service = JobService()


@router.post("")
def create_experiment(payload: ExperimentCreate):
    try:
        exp = exp_service.create_experiment(
            name=payload.name,
            description=payload.description or "",
            dataset_name=payload.dataset_name,
            model_name=payload.model_name,
            seed=payload.seed,
            train_config=payload.train_config.model_dump() if payload.train_config else None,
        )
        return exp
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_experiments():
    return exp_service.list_experiments()


@router.get("/{experiment_id}")
def get_experiment(experiment_id: str):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp


@router.post("/{experiment_id}/train")
def train_original_model(experiment_id: str, payload: Optional[TrainConfig] = None):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    job_id = job_service.create_job(experiment_id, "TRAIN_ORIGINAL")
    cfg_dict = payload.model_dump() if payload else None

    def task_worker(step_callback):
        return exp_service.train_original_model(
            exp_id=experiment_id,
            config_override=cfg_dict,
            step_callback=step_callback,
        )

    job_service.submit_job(job_id, task_worker)
    return {"job_id": job_id, "message": "Original model training started", "status": "PENDING"}


@router.post("/{experiment_id}/forget")
def request_forgetting(experiment_id: str, payload: ForgettingRequest):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    try:
        manifest = exp_service.request_forgetting(
            exp_id=experiment_id,
            strategy=payload.strategy,
            percentage=payload.percentage,
            target_class=payload.target_class,
            sample_ids=payload.sample_ids,
            group_id=payload.group_id,
            num_groups=payload.num_groups,
        )
        return manifest
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{experiment_id}/retrain")
def retrain_model_from_scratch(experiment_id: str, payload: Optional[RetrainRequest] = None):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if not exp.get("partition_manifest"):
        raise HTTPException(status_code=400, detail="Cannot retrain without a forgetting request partition.")

    job_id = job_service.create_job(experiment_id, "EXACT_RETRAIN")
    cfg_dict = payload.model_dump() if payload else None

    def task_worker(step_callback):
        return exp_service.train_retrained_model(
            exp_id=experiment_id,
            config_override=cfg_dict,
            step_callback=step_callback,
        )

    job_service.submit_job(job_id, task_worker)
    return {"job_id": job_id, "message": "Exact retraining started", "status": "PENDING"}


@router.post("/{experiment_id}/unlearn")
def run_unlearning(experiment_id: str, payload: UnlearnRequest):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if not exp.get("original_checkpoint_path"):
        raise HTTPException(status_code=400, detail="Original model must be trained first.")
    if not exp.get("partition_manifest"):
        raise HTTPException(status_code=400, detail="Forgetting partition must be specified first.")

    job_id = job_service.create_job(experiment_id, f"UNLEARN_{payload.algorithm.upper()}")

    def task_worker(step_callback):
        return exp_service.run_unlearning(
            exp_id=experiment_id,
            algorithm=payload.algorithm,
            epochs=payload.epochs,
            batch_size=payload.batch_size,
            learning_rate=payload.learning_rate,
            alpha_ascent=payload.alpha_ascent,
            beta_proximity=payload.beta_proximity,
            max_forget_loss=payload.max_forget_loss,
            step_callback=step_callback,
        )

    job_service.submit_job(job_id, task_worker)
    return {"job_id": job_id, "message": f"Unlearning job ({payload.algorithm}) started", "status": "PENDING"}


@router.post("/{experiment_id}/evaluate")
def evaluate_experiment(experiment_id: str):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    job_id = job_service.create_job(experiment_id, "EVALUATE_ALL")

    def task_worker(step_callback):
        return exp_service.evaluate_experiment(
            exp_id=experiment_id,
            step_callback=step_callback,
        )

    job_service.submit_job(job_id, task_worker)
    return {"job_id": job_id, "message": "Comprehensive evaluation started", "status": "PENDING"}


@router.get("/{experiment_id}/metrics")
def get_experiment_metrics(experiment_id: str):
    exp = exp_service.get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {
        "experiment_id": experiment_id,
        "status": exp["status"],
        "metrics": exp.get("metrics"),
        "insights": exp.get("insights"),
        "partition_manifest": exp.get("partition_manifest"),
    }

