import copy
import time
from typing import Callable, Dict, Optional, Any, List
import psutil
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..utils.hardware import get_device, get_hardware_info
from ..training.trainer import ModelTrainer


class RetainFineTuningUnlearner:
    """
    Approximate Machine Unlearning via Retain-Set Fine-Tuning.
    
    Research Concept:
    Fine-tuning the original model weights using exclusively the retained training set
    causes gradual catastrophic forgetting of non-retained patterns without full retraining.
    Typically uses a lower learning rate, early stopping, and regularized parameter drift.
    """

    def __init__(
        self,
        base_model: nn.Module,
        learning_rate: float = 0.0003,
        weight_decay: float = 1e-4,
        device: Optional[torch.device] = None,
    ):
        self.device = device or get_device()
        # Create an independent clone of the original model
        self.model = copy.deepcopy(base_model).to(self.device)
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay,
        )
        self.criterion = nn.CrossEntropyLoss()

    def unlearn(
        self,
        retain_dataset: Dataset,
        val_dataset: Optional[Dataset] = None,
        forget_dataset: Optional[Dataset] = None,
        epochs: int = 3,
        batch_size: int = 64,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes unlearning by fine-tuning on retain samples only.
        """
        retain_loader = DataLoader(
            retain_dataset,
            batch_size=batch_size,
            shuffle=True,
            drop_last=False,
        )

        history: List[Dict[str, Any]] = []
        start_time = time.time()
        process = psutil.Process()
        peak_ram_mb = 0.0

        for epoch in range(1, epochs + 1):
            epoch_start = time.time()
            self.model.train()
            running_loss = 0.0
            correct = 0
            total = 0

            for batch_data in retain_loader:
                if len(batch_data) == 3:
                    _, inputs, labels = batch_data
                else:
                    inputs, labels = batch_data

                inputs = inputs.to(self.device)
                labels = labels.to(self.device)

                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = self.criterion(outputs, labels)
                loss.backward()
                self.optimizer.step()

                running_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                total += labels.size(0)
                correct += predicted.eq(labels).sum().item()

            retain_loss = running_loss / max(1, total)
            retain_acc = (correct / max(1, total)) * 100.0

            # Monitor validation & forget accuracy if provided
            val_acc = None
            forget_acc = None
            if val_dataset is not None:
                trainer_eval = ModelTrainer(self.model, device=self.device)
                val_acc = trainer_eval.evaluate(val_dataset, batch_size=batch_size)["accuracy"]
            if forget_dataset is not None:
                trainer_eval = ModelTrainer(self.model, device=self.device)
                forget_acc = trainer_eval.evaluate(forget_dataset, batch_size=batch_size)["accuracy"]

            current_ram = process.memory_info().rss / (1024 * 1024)
            peak_ram_mb = max(peak_ram_mb, current_ram)
            epoch_time = time.time() - epoch_start

            epoch_record = {
                "epoch": epoch,
                "epochs_total": epochs,
                "retain_loss": round(retain_loss, 4),
                "retain_accuracy": round(retain_acc, 2),
                "val_accuracy": round(val_acc, 2) if val_acc is not None else None,
                "forget_accuracy": round(forget_acc, 2) if forget_acc is not None else None,
                "epoch_time_seconds": round(epoch_time, 2),
                "ram_usage_mb": round(current_ram, 1),
            }
            history.append(epoch_record)

            if progress_callback:
                progress_callback({
                    "type": "unlearn_epoch_complete",
                    "epoch": epoch,
                    "epochs": epochs,
                    "data": epoch_record,
                    "elapsed_seconds": round(time.time() - start_time, 2),
                })

        total_duration = time.time() - start_time
        return {
            "method": "retain_fine_tuning",
            "history": history,
            "unlearning_time_seconds": round(total_duration, 3),
            "peak_memory_mb": round(peak_ram_mb, 1),
            "final_retain_loss": history[-1]["retain_loss"] if history else None,
            "final_retain_accuracy": history[-1]["retain_accuracy"] if history else None,
            "hardware": get_hardware_info(),
        }
