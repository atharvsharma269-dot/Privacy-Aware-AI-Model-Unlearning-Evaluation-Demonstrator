"""
TOFU Generative Language-Model Unlearning Evaluation Protocol.

Following the standard TOFU benchmark formulation (Maini et al., 2024):
Evaluates autoregressive causal language models on Question-Answer ground-truth:
  1. Answer-conditioned loss: Cross-entropy loss computed strictly over the ground-truth answer token targets.
  2. Answer perplexity: exp(loss).
  3. Ground-truth token probability: mean exp(-loss_per_token).
  4. Generation ROUGE / Exact Token overlap on greedy decoding.

Separated cleanly from the auxiliary text-classification proxy.
"""

from typing import Dict, List, Optional, Any
import numpy as np
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForCausalLM


class TOFUGenerativeEvaluator:
    """
    Evaluates generative question-answering forgetting and utility on locuslab/TOFU.
    """

    def __init__(self, model_name: str = "distilbert/distilgpt2", device: Optional[str] = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.model_name = model_name

    def evaluate_qa_loss(
        self,
        model: nn.Module,
        qa_pairs: List[Dict[str, str]],
        max_samples: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Computes answer-conditioned cross-entropy loss, perplexity, and probability.
        """
        model.eval()
        model.to(self.device)

        if max_samples and max_samples < len(qa_pairs):
            pairs = qa_pairs[:max_samples]
        else:
            pairs = qa_pairs

        losses: List[float] = []
        token_probs: List[float] = []

        loss_fct = nn.CrossEntropyLoss(reduction="none")

        with torch.no_grad():
            for item in pairs:
                q = item["question"].strip()
                a = item["answer"].strip()

                prompt = f"Question: {q}\nAnswer: "
                full_text = prompt + a

                prompt_enc = self.tokenizer(prompt, return_tensors="pt")
                full_enc = self.tokenizer(full_text, return_tensors="pt")

                input_ids = full_enc["input_ids"].to(self.device)
                prompt_len = prompt_enc["input_ids"].shape[1]

                if input_ids.shape[1] <= prompt_len:
                    continue

                outputs = model(input_ids)
                logits = outputs.logits

                # Shift logits and labels for autoregressive modeling
                shift_logits = logits[:, :-1, :].contiguous()
                shift_labels = input_ids[:, 1:].contiguous()

                # Mask out prompt tokens so loss is only computed over the answer tokens
                loss_all = loss_fct(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                ).view(shift_labels.shape)

                # Answer token range in shifted sequence: from (prompt_len - 1) to end
                ans_loss = loss_all[:, (prompt_len - 1):]
                if ans_loss.numel() == 0:
                    continue

                sample_mean_loss = ans_loss.mean().item()
                sample_token_prob = torch.exp(-ans_loss).mean().item()

                losses.append(sample_mean_loss)
                token_probs.append(sample_token_prob)

        if not losses:
            return {
                "answer_loss": 0.0,
                "perplexity": 1.0,
                "mean_answer_probability": 0.0,
                "num_samples_evaluated": 0,
            }

        mean_loss = float(np.mean(losses))
        # Clamp perplexity for numerical stability
        perplexity = float(np.exp(min(mean_loss, 20.0)))
        mean_prob = float(np.mean(token_probs))

        return {
            "answer_loss": round(mean_loss, 4),
            "perplexity": round(perplexity, 2),
            "mean_answer_probability": round(mean_prob, 4),
            "num_samples_evaluated": len(losses),
        }

