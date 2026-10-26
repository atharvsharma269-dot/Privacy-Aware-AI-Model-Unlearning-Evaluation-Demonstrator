from typing import Dict, List, Optional, Any
import numpy as np
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..training.trainer import ModelTrainer
from ..utils.hardware import get_device


def compute_dataset_metrics(
    model: nn.Module,
    dataset: Dataset,
    num_classes: int = 10,
    batch_size: int = 128,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """
    Computes loss, accuracy, mean confidence, per-class metrics, and confusion matrix.
    """
    dev = device or get_device()
    model.eval()
    model.to(dev)

    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    criterion = nn.CrossEntropyLoss(reduction="none")

    all_losses = []
    all_preds = []
    all_targets = []
    all_confidences = []
    all_probs = []

    with torch.no_grad():
        for batch in loader:
            if len(batch) == 3:
                _, x, y = batch
            else:
                x, y = batch

            x = x.to(dev)
            y = y.to(dev)

            logits = model(x)
            loss_batch = criterion(logits, y)
            probs = torch.softmax(logits, dim=1)
            conf, pred = probs.max(dim=1)

            all_losses.extend(loss_batch.cpu().numpy().tolist())
            all_preds.extend(pred.cpu().numpy().tolist())
            all_targets.extend(y.cpu().numpy().tolist())
            all_confidences.extend(conf.cpu().numpy().tolist())
            all_probs.extend(probs.cpu().numpy().tolist())

    n_samples = len(all_targets)
    if n_samples == 0:
        return {
            "loss": 0.0,
            "accuracy": 0.0,
            "mean_confidence": 0.0,
            "sample_count": 0,
            "class_metrics": {},
            "confusion_matrix": [],
        }

    correct = sum(p == t for p, t in zip(all_preds, all_targets))
    accuracy = (correct / n_samples) * 100.0
    mean_loss = float(np.mean(all_losses))
    mean_conf = float(np.mean(all_confidences))

    # Class-wise precision, recall, F1
    prec, rec, f1, support = precision_recall_fscore_support(
        all_targets,
        all_preds,
        labels=list(range(num_classes)),
        zero_division=0,
    )

    class_metrics = {}
    for c in range(num_classes):
        class_metrics[c] = {
            "precision": round(float(prec[c]), 4),
            "recall": round(float(rec[c]), 4),
            "f1": round(float(f1[c]), 4),
            "support": int(support[c]),
        }

    conf_mat = confusion_matrix(
        all_targets,
        all_preds,
        labels=list(range(num_classes)),
    ).tolist()

    return {
        "loss": round(mean_loss, 4),
        "accuracy": round(accuracy, 2),
        "mean_confidence": round(mean_conf, 4),
        "sample_count": n_samples,
        "class_metrics": class_metrics,
        "confusion_matrix": conf_mat,
        "raw_losses": all_losses,
        "raw_confidences": all_confidences,
        "probabilities": all_probs,
        "predictions": all_preds,
        "targets": all_targets,
    }


def compute_utility_degradation(
    original_test_acc: float,
    current_test_acc: float,
) -> float:
    """
    Computes percentage reduction in test utility relative to original model:
    Degradation = max(0, (Orig - Current) / Orig * 100)
    """
    if original_test_acc <= 0:
        return 0.0
    degradation = ((original_test_acc - current_test_acc) / original_test_acc) * 100.0
    return round(float(degradation), 2)

