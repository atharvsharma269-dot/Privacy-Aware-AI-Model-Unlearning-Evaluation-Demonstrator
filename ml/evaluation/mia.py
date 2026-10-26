from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from ..utils.hardware import get_device


class MembershipInferenceEvaluator:
    """
    Evaluates membership privacy leakage using loss-entropy-confidence attack models
    with strictly disjoint attack-training and attack-evaluation partitions.
    """

    def __init__(self, device: Optional[torch.device] = None, seed: int = 42):
        self.device = device or get_device()
        self.seed = seed

    def _extract_attack_features(
        self,
        model: nn.Module,
        dataset: Dataset,
        batch_size: int = 128,
    ) -> np.ndarray:
        """
        Extracts 5-dimensional feature vectors per sample:
        [loss, max_confidence, entropy, margin_top1_top2, is_correct]
        """
        model.eval()
        model.to(self.device)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        features: List[List[float]] = []

        with torch.no_grad():
            for batch in loader:
                if len(batch) == 3:
                    _, x, y = batch
                else:
                    x, y = batch

                x = x.to(self.device)
                y = y.to(self.device)

                logits = model(x)
                probs = torch.softmax(logits, dim=1)
                sorted_probs, _ = torch.sort(probs, dim=1, descending=True)

                eps = 1e-12
                # Cross-entropy loss per sample
                loss_per_sample = -torch.log(probs[torch.arange(x.size(0)), y] + eps)
                # Prediction entropy: -sum(p * log(p))
                entropy = -torch.sum(probs * torch.log(probs + eps), dim=1)
                # Max confidence
                max_conf = sorted_probs[:, 0]
                # Margin between top-1 and top-2
                margin = sorted_probs[:, 0] - sorted_probs[:, 1]
                # Correctness boolean
                _, preds = probs.max(dim=1)
                is_correct = (preds == y).float()

                batch_feat = torch.stack(
                    [loss_per_sample, max_conf, entropy, margin, is_correct],
                    dim=1,
                ).cpu().numpy()

                features.extend(batch_feat.tolist())

        return np.array(features, dtype=np.float32)

    def evaluate_forget_set_mia(
        self,
        model: nn.Module,
        retain_dataset: Dataset,
        forget_dataset: Dataset,
        test_dataset: Dataset,
        batch_size: int = 128,
    ) -> Dict[str, Any]:
        """
        Trains an attack model on disjoint shadow splits of retain (members) and test (non-members),
        then evaluates membership inference vulnerability specifically on the forget set.
        """
        rng = np.random.RandomState(self.seed)

        # 1. Extract features
        feat_retain = self._extract_attack_features(model, retain_dataset, batch_size=batch_size)
        feat_forget = self._extract_attack_features(model, forget_dataset, batch_size=batch_size)
        feat_test = self._extract_attack_features(model, test_dataset, batch_size=batch_size)

        n_retain = len(feat_retain)
        n_test = len(feat_test)
        n_forget = len(feat_forget)

        if n_forget == 0 or n_retain == 0 or n_test == 0:
            return {
                "roc_auc": 0.5,
                "attack_advantage": 0.0,
                "fpr": [0.0, 1.0],
                "tpr": [0.0, 1.0],
                "interpretation": "Insufficient samples for MIA evaluation.",
            }

        # 2. Construct disjoint Attack-Training split from a fraction of retain (members) and test (non-members)
        # Use at most half of retain and test to train the attacker, leaving the rest unseen
        n_attack_train_members = min(1000, n_retain // 2)
        n_attack_train_non_members = min(1000, n_test // 2)

        idx_retain_perm = rng.permutation(n_retain)
        idx_test_perm = rng.permutation(n_test)

        train_member_idx = idx_retain_perm[:n_attack_train_members]
        train_non_member_idx = idx_test_perm[:n_attack_train_non_members]

        eval_test_non_member_idx = idx_test_perm[n_attack_train_non_members:]

        X_attack_train = np.vstack([
            feat_retain[train_member_idx],
            feat_test[train_non_member_idx],
        ])
        y_attack_train = np.hstack([
            np.ones(len(train_member_idx)),
            np.zeros(len(train_non_member_idx)),
        ])

        # Train standard logistic regression attacker
        attacker = LogisticRegression(random_state=self.seed, max_iter=500)
        attacker.fit(X_attack_train, y_attack_train)

        # 3. Evaluate attacker on Forget set (hypothetical members) vs Unseen Test set (non-members)
        # If model truly forgot the forget set, attacker probability on forget set should match test set!
        n_eval_test = min(len(eval_test_non_member_idx), n_forget * 2)
        eval_non_members = feat_test[eval_test_non_member_idx[:n_eval_test]]

        X_eval = np.vstack([feat_forget, eval_non_members])
        y_eval = np.hstack([np.ones(n_forget), np.zeros(len(eval_non_members))])

        pred_scores = attacker.predict_proba(X_eval)[:, 1]

        # ROC Curve & AUC
        fpr, tpr, thresholds = roc_curve(y_eval, pred_scores)
        auc_score = float(roc_auc_score(y_eval, pred_scores))

        # Standard Error of ROC-AUC via Hanley & McNeil (1982) formulation
        n_pos = float(n_forget)
        n_neg = float(len(eval_non_members))
        q1 = auc_score / (2.0 - auc_score) if auc_score < 1.0 else 1.0
        q2 = (2.0 * (auc_score ** 2)) / (1.0 + auc_score) if auc_score > 0 else 0.0
        var_auc = (
            auc_score * (1.0 - auc_score)
            + (n_pos - 1.0) * (q1 - auc_score ** 2)
            + (n_neg - 1.0) * (q2 - auc_score ** 2)
        ) / max(1.0, (n_pos * n_neg))
        auc_se = float(np.sqrt(max(0.0, var_auc)))

        # Attack Advantage: max |TPR - FPR|
        # Standard privacy literature defines advantage as ability to distinguish members from non-members
        tpr_minus_fpr = tpr - fpr
        directional_advantage = float(np.max(tpr_minus_fpr))
        absolute_advantage = float(np.max(np.abs(tpr_minus_fpr)))

        # Subsample ROC points for concise JSON payload
        sample_step = max(1, len(fpr) // 25)
        curve_data = [
            {"fpr": round(float(f), 4), "tpr": round(float(t), 4)}
            for f, t in zip(fpr[::sample_step], tpr[::sample_step])
        ]
        if curve_data[-1]["fpr"] != 1.0 or curve_data[-1]["tpr"] != 1.0:
            curve_data.append({"fpr": 1.0, "tpr": 1.0})

        # Mean predicted probability that forget samples are members
        forget_member_prob = float(np.mean(attacker.predict_proba(feat_forget)[:, 1]))
        test_member_prob = float(np.mean(attacker.predict_proba(eval_non_members)[:, 1]))

        # Scientific interpretation of the attack score
        if auc_score >= 0.70:
            interpretation = (
                f"Elevated empirical privacy leakage (ROC-AUC={auc_score:.4f} ± {auc_se:.4f}). "
                "The shadow classifier reliably separates forget samples from unseen test samples based on confidence/loss signatures."
            )
        elif auc_score <= 0.35:
            interpretation = (
                f"Inverted distribution signal (ROC-AUC={auc_score:.4f} ± {auc_se:.4f}). "
                "Forget samples produce higher loss / lower confidence than holdout test samples, indicating severe non-membership or distribution divergence."
            )
        else:
            interpretation = (
                f"Near-chance empirical privacy preservation (ROC-AUC={auc_score:.4f} ± {auc_se:.4f}). "
                "Under this specific logistic shadow model, forget-sample loss/confidence profiles are statistically indistinguishable from unseen test controls."
            )

        return {
            "roc_auc": round(auc_score, 4),
            "roc_auc_standard_error": round(auc_se, 4),
            "attack_advantage": round(directional_advantage, 4),
            "absolute_advantage": round(absolute_advantage, 4),
            "roc_curve": curve_data,
            "forget_membership_prob": round(forget_member_prob, 4),
            "test_membership_prob": round(test_member_prob, 4),
            "num_forget_evaluated": n_forget,
            "num_test_evaluated": len(eval_non_members),
            "num_shadow_train_members": len(train_member_idx),
            "num_shadow_train_non_members": len(train_non_member_idx),
            "interpretation": interpretation,
        }

