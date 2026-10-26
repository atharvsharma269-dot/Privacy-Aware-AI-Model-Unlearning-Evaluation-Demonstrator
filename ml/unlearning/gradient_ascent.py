import copy
import math
import time
from typing import Callable, Dict, Optional, Any, List
import psutil
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..utils.hardware import get_device, get_hardware_info
from ..training.trainer import ModelTrainer


class RegularizedGradientAscentUnlearner:
    """
    Constrained Gradient Ascent on Forget Set with Retain-Set Regularization.

    Objective:
      Min L_retain + alpha * (-min(L_forget, tau_bound)) + beta * ||theta - theta_orig||^2

    Safeguards:
      1. Bounded forget loss (tau_bound) to prevent catastrophic model collapse.
      2. Retain set cross-entropy ensures retained knowledge preservation.
      3. Parameter proximity penalty (L2 drift from original weights).
      4. Gradient norm clipping (prevents exploding gradients).
      5. Utility degradation safety valve (halts if retain accuracy plummets).
    """

    def __init__(
        self,
        base_model: nn.Module,
        learning_rate: float = 0.0001,
        alpha_ascent: float = 0.4,
        beta_proximity: float = 0.01,
        max_forget_loss: float = 2.35,  # log(10) ~ 2.302 for 10 classes
        device: Optional[torch.device] = None,
    ):
        self.device = device or get_device()
        self.model = copy.deepcopy(base_model).to(self.device)
        self.original_weights = {
            k: v.clone().detach().to(self.device)
            for k, v in base_model.state_dict().items()
        }
        self.learning_rate = learning_rate
        self.alpha_ascent = alpha_ascent
        self.beta_proximity = beta_proximity
        self.max_forget_loss = max_forget_loss

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.CrossEntropyLoss()
        self.total_trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)

    def unlearn(
        self,
        retain_dataset: Dataset,
        forget_dataset: Dataset,
        val_dataset: Optional[Dataset] = None,
        epochs: int = 3,
        batch_size: int = 64,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes bounded gradient ascent on forget set while regularizing on retain set.
        """
        retain_loader = DataLoader(retain_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
        forget_loader = DataLoader(forget_dataset, batch_size=batch_size, shuffle=True, drop_last=False)

        history: List[Dict[str, Any]] = []
        start_time = time.time()
        process = psutil.Process()
        peak_ram_mb = 0.0

        for epoch in range(1, epochs + 1):
            epoch_start = time.time()
            self.model.train()
            running_retain_loss = 0.0
            running_forget_loss = 0.0
            retain_correct = 0
            retain_total = 0

            forget_iter = iter(forget_loader)

            for batch_retain in retain_loader:
                if len(batch_retain) == 3:
                    _, x_retain, y_retain = batch_retain
                else:
                    x_retain, y_retain = batch_retain

                x_retain = x_retain.to(self.device)
                y_retain = y_retain.to(self.device)

                # Get a batch of forget samples (looping if forget set is smaller)
                try:
                    batch_forget = next(forget_iter)
                except StopIteration:
                    forget_iter = iter(forget_loader)
                    batch_forget = next(forget_iter)

                if len(batch_forget) == 3:
                    _, x_forget, y_forget = batch_forget
                else:
                    x_forget, y_forget = batch_forget

                x_forget = x_forget.to(self.device)
                y_forget = y_forget.to(self.device)

                self.optimizer.zero_grad()

                # 1. Retain Cross-Entropy Loss
                out_retain = self.model(x_retain)
                loss_retain = self.criterion(out_retain, y_retain)

                # 2. Bounded Forget Cross-Entropy Ascent (differentiable clamping)
                out_forget = self.model(x_forget)
                loss_forget_raw = self.criterion(out_forget, y_forget)
                loss_forget_ascent = -torch.clamp(loss_forget_raw, max=self.max_forget_loss)

                # 3. Parameter Proximity Regularization (normalized by parameter count)
                sq_drift = torch.tensor(0.0, device=self.device)
                for name, param in self.model.named_parameters():
                    if name in self.original_weights and param.requires_grad:
                        sq_drift += torch.sum((param - self.original_weights[name]) ** 2)
                loss_proximity = sq_drift / max(1, self.total_trainable_params)

                # Total Objective
                total_loss = (
                    loss_retain
                    + self.alpha_ascent * loss_forget_ascent
                    + self.beta_proximity * loss_proximity
                )

                total_loss.backward()

                # Gradient clipping to prevent instability
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.5)

                self.optimizer.step()

                running_retain_loss += loss_retain.item() * x_retain.size(0)
                running_forget_loss += loss_forget_raw.item() * x_forget.size(0)

                _, pred = out_retain.max(1)
                retain_total += y_retain.size(0)
                retain_correct += pred.eq(y_retain).sum().item()

            epoch_retain_loss = running_retain_loss / max(1, retain_total)
            epoch_retain_acc = (retain_correct / max(1, retain_total)) * 100.0

            # Evaluate on forget set and validation set
            evaluator = ModelTrainer(self.model, device=self.device)
            forget_eval = evaluator.evaluate(forget_dataset, batch_size=batch_size)
            val_eval = evaluator.evaluate(val_dataset, batch_size=batch_size) if val_dataset is not None else None

            current_ram = process.memory_info().rss / (1024 * 1024)
            peak_ram_mb = max(peak_ram_mb, current_ram)
            epoch_time = time.time() - epoch_start

            record = {
                "epoch": epoch,
                "epochs_total": epochs,
                "retain_loss": round(epoch_retain_loss, 4),
                "retain_accuracy": round(epoch_retain_acc, 2),
                "forget_loss": round(forget_eval["loss"], 4),
                "forget_accuracy": round(forget_eval["accuracy"], 2),
                "val_accuracy": round(val_eval["accuracy"], 2) if val_eval else None,
                "epoch_time_seconds": round(epoch_time, 2),
                "ram_usage_mb": round(current_ram, 1),
            }
            history.append(record)

            if progress_callback:
                progress_callback({
                    "type": "unlearn_epoch_complete",
                    "epoch": epoch,
                    "epochs": epochs,
                    "data": record,
                    "elapsed_seconds": round(time.time() - start_time, 2),
                })

            # Safeguard: if retain accuracy falls below 50%, stop early
            if epoch_retain_acc < 50.0:
                break

        total_duration = time.time() - start_time
        return {
            "method": "gradient_ascent_regularized",
            "history": history,
            "unlearning_time_seconds": round(total_duration, 3),
            "peak_memory_mb": round(peak_ram_mb, 1),
            "final_retain_loss": history[-1]["retain_loss"] if history else None,
            "final_retain_accuracy": history[-1]["retain_accuracy"] if history else None,
            "final_forget_accuracy": history[-1]["forget_accuracy"] if history else None,
            "hardware": get_hardware_info(),
        }
