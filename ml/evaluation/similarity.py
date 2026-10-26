from typing import Dict, List, Optional, Any
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..utils.hardware import get_device


def compute_behavioral_similarity(
    unlearned_model: nn.Module,
    retrained_model: nn.Module,
    eval_dataset: Dataset,
    batch_size: int = 128,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """
    Measures behavioral divergence and prediction fidelity between
    the approximate-unlearned model and the golden exact-retrained reference model.
    """
    dev = device or get_device()
    unlearned_model.eval()
    retrained_model.eval()
    unlearned_model.to(dev)
    retrained_model.to(dev)

    loader = DataLoader(eval_dataset, batch_size=batch_size, shuffle=False)

    all_agreements = []
    kl_divergences = []
    js_divergences = []
    eps = 1e-12

    with torch.no_grad():
        for batch in loader:
            if len(batch) == 3:
                _, x, _ = batch
            else:
                x, _ = batch

            x = x.to(dev)

            logits_u = unlearned_model(x)
            logits_r = retrained_model(x)

            probs_u = torch.softmax(logits_u, dim=1)
            probs_r = torch.softmax(logits_r, dim=1)

            pred_u = probs_u.argmax(dim=1)
            pred_r = probs_r.argmax(dim=1)

            # Prediction agreement
            agreement = (pred_u == pred_r).float().cpu().numpy().tolist()
            all_agreements.extend(agreement)

            # KL Divergence: KL(P_u || P_r) = sum(P_u * log(P_u / P_r))
            kl_batch = torch.sum(
                probs_u * (torch.log(probs_u + eps) - torch.log(probs_r + eps)),
                dim=1,
            ).cpu().numpy().tolist()
            kl_divergences.extend(kl_batch)

            # Jensen-Shannon Divergence: 0.5 * KL(P_u || M) + 0.5 * KL(P_r || M) where M = 0.5 * (P_u + P_r)
            m = 0.5 * (probs_u + probs_r)
            kl_u_m = torch.sum(probs_u * (torch.log(probs_u + eps) - torch.log(m + eps)), dim=1)
            kl_r_m = torch.sum(probs_r * (torch.log(probs_r + eps) - torch.log(m + eps)), dim=1)
            js_batch = (0.5 * kl_u_m + 0.5 * kl_r_m).cpu().numpy().tolist()
            js_divergences.extend(js_batch)

    # Parameter L2 distance between unlearned and retrained model weights
    param_distance = 0.0
    u_params = dict(unlearned_model.named_parameters())
    r_params = dict(retrained_model.named_parameters())
    for name, p_u in u_params.items():
        if name in r_params:
            diff = (p_u.data.cpu() - r_params[name].data.cpu()).float()
            param_distance += torch.sum(diff ** 2).item()
    param_l2_norm = float(np.sqrt(param_distance))

    agreement_pct = (sum(all_agreements) / max(1, len(all_agreements))) * 100.0
    mean_kl = float(np.mean(kl_divergences)) if kl_divergences else 0.0
    mean_js = float(np.mean(js_divergences)) if js_divergences else 0.0

    return {
        "prediction_agreement_percent": round(agreement_pct, 2),
        "mean_kl_divergence": round(mean_kl, 4),
        "mean_js_divergence": round(mean_js, 4),
        "weight_l2_distance": round(param_l2_norm, 4),
        "evaluated_samples": len(all_agreements),
        "caveat": (
            "Behavioral similarity provides empirical evidence of alignment with the retrained reference, "
            "but does not constitute a certified or mathematical guarantee of complete unlearning."
        ),
    }

