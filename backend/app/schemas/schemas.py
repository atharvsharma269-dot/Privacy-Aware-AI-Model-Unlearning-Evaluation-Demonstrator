from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class DatasetSample(BaseModel):
    index: int
    label: int
    class_name: str
    image_base64: str


class DatasetSummary(BaseModel):
    name: str
    total_train: int
    total_test: int
    num_classes: int
    classes: List[str]
    class_distribution_train: Dict[str, int]


class TrainConfig(BaseModel):
    epochs: int = Field(default=5, ge=1, le=50)
    batch_size: int = Field(default=64, ge=8, le=512)
    learning_rate: float = Field(default=0.001, gt=0.0)
    optimizer: str = Field(default="adam")
    weight_decay: float = Field(default=1e-4, ge=0.0)
    subsample_size: Optional[int] = Field(default=None, description="Optional training subset size for rapid experimentation")


class ForgettingRequest(BaseModel):
    strategy: str = Field(..., description="'random', 'class', 'sample_ids', 'group', or 'tofu_forget10'")
    percentage: Optional[float] = Field(default=None, ge=0.01, le=1.0)
    target_class: Optional[int] = Field(default=None, ge=0, le=9)
    sample_ids: Optional[List[int]] = None
    group_id: Optional[int] = Field(default=None, ge=0)
    num_groups: int = Field(default=10, ge=2)


class RetrainRequest(BaseModel):
    epochs: int = Field(default=5, ge=1, le=50)
    batch_size: int = Field(default=64, ge=8, le=512)
    learning_rate: float = Field(default=0.001, gt=0.0)
    optimizer: str = Field(default="adam")
    weight_decay: float = Field(default=1e-4, ge=0.0)


class UnlearnRequest(BaseModel):
    algorithm: str = Field(default="retain_fine_tuning", description="'retain_fine_tuning' or 'gradient_ascent'")
    epochs: int = Field(default=3, ge=1, le=30)
    batch_size: int = Field(default=64, ge=8, le=512)
    learning_rate: float = Field(default=0.0003, gt=0.0)
    alpha_ascent: float = Field(default=0.4, ge=0.0, le=5.0)
    beta_proximity: float = Field(default=0.01, ge=0.0, le=1.0)
    max_forget_loss: float = Field(default=2.35, ge=0.5, le=10.0)


class ExperimentCreate(BaseModel):
    name: str = Field(default="Fashion-MNIST Unlearning Study")
    description: Optional[str] = "Evaluation of approximate unlearning vs exact retraining"
    dataset_name: str = Field(default="fashion_mnist")
    model_name: str = Field(default="mlp")
    seed: int = Field(default=42)
    train_config: Optional[TrainConfig] = None


class JobResponse(BaseModel):
    id: str
    experiment_id: str
    job_type: str
    status: str  # 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED'
    progress: float
    current_step: Optional[str] = None
    logs: List[str] = []
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExperimentResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    dataset_name: str
    model_name: str
    status: str
    seed: int
    created_at: str
    updated_at: str
    train_config: Optional[Dict[str, Any]] = None
    partition_manifest: Optional[Dict[str, Any]] = None
    unlearn_config: Optional[Dict[str, Any]] = None
    original_checkpoint_path: Optional[str] = None
    retrained_checkpoint_path: Optional[str] = None
    unlearned_checkpoint_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    insights: Optional[Dict[str, Any]] = None

