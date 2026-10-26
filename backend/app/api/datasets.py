from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from ..services.dataset_service import DatasetService

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
dataset_service = DatasetService()


@router.get("")
def list_supported_datasets():
    """List available research datasets."""
    return [
        {
            "id": "fashion_mnist",
            "name": "Fashion-MNIST",
            "type": "28x28 Grayscale Image Classification",
            "classes": 10,
            "description": "Zalando research dataset; 60,000 train images, 10,000 test images across 10 apparel categories.",
        },
        {
            "id": "tofu",
            "name": "TOFU (Task of Fictitious Unlearning)",
            "type": "NLP Question-Answering & Author Attribution Benchmark",
            "classes": 10,
            "description": "LocusLab TOFU benchmark containing 4,000 QA pairs across 200 fictitious authors; evaluated on forgetting author biographical associations while preserving retained author utility.",
        },
        {
            "id": "mnist",
            "name": "MNIST",
            "type": "28x28 Grayscale Digit Classification",
            "classes": 10,
            "description": "Classic handwritten digit recognition dataset; 60,000 train images, 10,000 test images.",
        },
    ]


@router.get("/{dataset_id}/summary")
def get_dataset_summary(dataset_id: str):
    """Retrieve class distribution and sample counts for a dataset."""
    try:
        return dataset_service.get_summary(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dataset_id}/samples")
def get_dataset_samples(
    dataset_id: str,
    split: str = Query("train", description="'train' or 'test'"),
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    class_filter: Optional[int] = Query(None, ge=0, le=9),
):
    """Retrieve samples with base64 encoded PNG thumbnails for visualization."""
    try:
        samples = dataset_service.get_samples(
            dataset_name=dataset_id,
            split=split,
            offset=offset,
            limit=limit,
            class_filter=class_filter,
        )
        return {
            "dataset_id": dataset_id,
            "split": split,
            "offset": offset,
            "limit": limit,
            "samples": samples,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

