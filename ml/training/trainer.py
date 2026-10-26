import os
import time
from typing import Callable, Dict, Optional, Any, List
import numpy as np
import psutil
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..utils.hardware import get_device, get_hardware_info
from ..utils.seed import set_seed


class ModelTrainer:
    """
    Standard PyTorch training pipeline with progress tracking,
    hardware telemetry, and checkpoint management.
    """

    def __init__(
        self,
        model: nn.Module,
        device: Optional[torch.device] = None,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-4,
        optimizer_name: str = "adam",
    ):
        self.device = device or get_device()
        self.model = model.to(self.device)
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.optimizer_name = optimizer_name.lower()

        if self.optimizer_name == "sgd":
            self.optimizer = torch.optim.SGD(
                self.model.parameters(),
                lr=learning_rate,
                momentum=0.9,
                weight_decay=weight_decay,
            )
        else:
            self.optimizer = torch.optim.Adam(
                self.model.parameters(),
                lr=learning_rate,
                weight_decay=weight_decay,
            )

        self.criterion = nn.CrossEntropyLoss()

    def train(
        self,
        train_dataset: Dataset,
        val_dataset: Optional[Dataset] = None,
        epochs: int = 5,
        batch_size: int = 64,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes model training loop.
        """
        train_loader = DataLoader(
            train_dataset,
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

            for batch_data in train_loader:
                # IndexedDataset returns (idx, inputs, labels)
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

            train_loss = running_loss / max(1, total)
            train_acc = (correct / max(1, total)) * 100.0

            # Evaluate on validation dataset if provided
            val_loss = None
            val_acc = None
            if val_dataset is not None:
                val_metrics = self.evaluate(val_dataset, batch_size=batch_size)
                val_loss = val_metrics["loss"]
                val_acc = val_metrics["accuracy"]

            current_ram = process.memory_info().rss / (1024 * 1024)
            peak_ram_mb = max(peak_ram_mb, current_ram)
            epoch_time = time.time() - epoch_start

            epoch_record = {
                "epoch": epoch,
                "epochs_total": epochs,
                "train_loss": round(train_loss, 4),
                "train_accuracy": round(train_acc, 2),
                "val_loss": round(val_loss, 4) if val_loss is not None else None,
                "val_accuracy": round(val_acc, 2) if val_acc is not None else None,
                "epoch_time_seconds": round(epoch_time, 2),
                "ram_usage_mb": round(current_ram, 1),
            }
            history.append(epoch_record)

            if progress_callback:
                progress_callback({
                    "type": "epoch_complete",
                    "epoch": epoch,
                    "epochs": epochs,
                    "data": epoch_record,
                    "elapsed_seconds": round(time.time() - start_time, 2),
                })

        total_duration = time.time() - start_time
        num_parameters = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

        return {
            "history": history,
            "training_time_seconds": round(total_duration, 3),
            "peak_memory_mb": round(peak_ram_mb, 1),
            "final_train_loss": history[-1]["train_loss"] if history else None,
            "final_train_accuracy": history[-1]["train_accuracy"] if history else None,
            "final_val_loss": history[-1]["val_loss"] if history else None,
            "final_val_accuracy": history[-1]["val_accuracy"] if history else None,
            "parameters_count": num_parameters,
            "hardware": get_hardware_info(),
        }

    @torch.no_grad()
    def evaluate(self, dataset: Dataset, batch_size: int = 128) -> Dict[str, Any]:
        """Evaluate model loss, accuracy, and average confidence on any dataset."""
        self.model.eval()
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        running_loss = 0.0
        correct = 0
        total = 0
        all_confidences = []

        for batch_data in loader:
            if len(batch_data) == 3:
                _, inputs, labels = batch_data
            else:
                inputs, labels = batch_data

            inputs = inputs.to(self.device)
            labels = labels.to(self.device)

            outputs = self.model(inputs)
            loss = self.criterion(outputs, labels)

            running_loss += loss.item() * inputs.size(0)
            probs = torch.softmax(outputs, dim=1)
            confidences, predicted = probs.max(1)

            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            all_confidences.extend(confidences.cpu().numpy().tolist())

        avg_loss = running_loss / max(1, total)
        acc = (correct / max(1, total)) * 100.0
        avg_conf = float(np.mean(all_confidences)) if all_confidences else 0.0

        return {
            "loss": round(avg_loss, 4),
            "accuracy": round(acc, 2),
            "mean_confidence": round(avg_conf, 4),
            "sample_count": total,
        }

    def save_checkpoint(
        self,
        checkpoint_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Saves weights, optimizer state, and training metadata."""
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "metadata": metadata or {},
            },
            checkpoint_path,
        )

    def load_checkpoint(self, checkpoint_path: str) -> Dict[str, Any]:
        """Loads weights and returns stored metadata."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        if "optimizer_state_dict" in checkpoint:
            self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        return checkpoint.get("metadata", {})
