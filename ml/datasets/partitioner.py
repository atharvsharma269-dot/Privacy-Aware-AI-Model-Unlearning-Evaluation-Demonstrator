import hashlib
import json
from typing import Dict, List, Optional, Set, Tuple, Any
import numpy as np
import torch
from torch.utils.data import Subset


class DatasetPartitioner:
    """
    Manages partitioning of training data into Retain, Forget, and Validation sets,
    with strict non-overlapping guarantees, reproducible seeds, and audit logging.
    """

    def __init__(
        self,
        train_dataset,
        val_ratio: float = 0.1,
        seed: int = 42,
        subsample_size: Optional[int] = None,
    ):
        self.train_dataset = train_dataset
        self.val_ratio = val_ratio
        self.seed = seed
        self.total_raw_len = len(train_dataset)

        # Base reproducible RNG
        rng = np.random.RandomState(seed)

        # Optional subsampling for rapid laptop experimentation
        if subsample_size and subsample_size < self.total_raw_len:
            pool_indices = rng.permutation(self.total_raw_len)[:subsample_size]
        else:
            pool_indices = np.arange(self.total_raw_len)

        # Shuffle indices
        shuffled_indices = rng.permutation(pool_indices)

        # Split into pool-train and pool-val
        val_size = int(len(shuffled_indices) * val_ratio)
        self.val_indices = set(shuffled_indices[:val_size].tolist())
        self.available_train_indices = shuffled_indices[val_size:].tolist()

        # Cache targets for fast category filtering
        self._targets_cache: Dict[int, int] = {}
        for idx in pool_indices:
            # IndexedDataset returns (idx, img, target)
            _, _, target = train_dataset[idx]
            self._targets_cache[int(idx)] = int(target)

        # State for active forget/retain partition
        self.forget_indices: Set[int] = set()
        self.retain_indices: Set[int] = set(self.available_train_indices)
        self.split_metadata: Dict[str, Any] = {
            "val_ratio": val_ratio,
            "seed": seed,
            "subsample_size": subsample_size,
            "total_available_train": len(self.available_train_indices),
            "val_count": len(self.val_indices),
        }

    def create_partition(
        self,
        strategy: str,
        percentage: Optional[float] = None,
        target_class: Optional[int] = None,
        sample_ids: Optional[List[int]] = None,
        group_id: Optional[int] = None,
        num_groups: int = 10,
    ) -> Dict[str, Any]:
        """
        Partition available training samples into Retain and Forget subsets.

        Strategies:
        - 'random': Random percentage (e.g., 0.05, 0.10, 0.20) of available training samples
        - 'class': Specific target class (either entirely or a percentage)
        - 'sample_ids': Explicit user-provided list of indices
        - 'group': Synthetic group identifier (e.g. user group 0..num_groups-1)
        """
        rng = np.random.RandomState(self.seed)
        candidate_pool = list(self.available_train_indices)
        chosen_forget: List[int] = []

        if strategy == "random":
            pct = percentage if percentage is not None else 0.10
            n_forget = int(round(len(candidate_pool) * pct))
            n_forget = max(1, min(n_forget, len(candidate_pool) - 1))
            shuffled = rng.permutation(candidate_pool)
            chosen_forget = shuffled[:n_forget].tolist()

        elif strategy == "class":
            if target_class is None:
                raise ValueError("target_class must be specified for class-based forgetting")
            class_samples = [idx for idx in candidate_pool if self._targets_cache[idx] == target_class]
            if percentage is not None:
                n_forget = int(round(len(class_samples) * percentage))
                n_forget = max(1, min(n_forget, len(class_samples)))
                shuffled = rng.permutation(class_samples)
                chosen_forget = shuffled[:n_forget].tolist()
            else:
                chosen_forget = class_samples

        elif strategy == "sample_ids":
            if not sample_ids:
                raise ValueError("sample_ids list must not be empty")
            valid_set = set(candidate_pool)
            chosen_forget = [s for s in sample_ids if s in valid_set]
            if not chosen_forget:
                raise ValueError("None of the requested sample_ids exist in the active training partition")

        elif strategy in ["tofu_single_author", "single_author"]:
            # Single fictitious author erasure (exactly 20 questions for the selected author ID)
            target_author = target_class if target_class is not None else 0
            chosen_forget = [idx for idx in candidate_pool if (idx // 20) == target_author]
            if not chosen_forget:
                raise ValueError(f"Author ID {target_author} has no samples in the active training partition")

        elif strategy in ["tofu_forget10", "tofu_official_forget10"]:
            # Official TOFU forget10: designated fictitious authors (indices 3600..3999 or Author Cohort 0)
            chosen_forget = [idx for idx in candidate_pool if idx >= 3600 or (idx // 20) in range(180, 200)]
            if not chosen_forget:
                chosen_forget = [idx for idx in candidate_pool if (idx // 20) == 0 or self._targets_cache.get(idx) == 0]

        elif strategy == "group":
            # Assign synthetic group deterministically based on hash of index
            if group_id is None:
                raise ValueError("group_id must be provided for group unlearning")
            chosen_forget = [
                idx for idx in candidate_pool
                if (idx % num_groups) == (group_id % num_groups)
            ]
        else:
            raise ValueError(f"Unknown unlearning partition strategy: {strategy}")

        self.forget_indices = set(chosen_forget)
        self.retain_indices = set(candidate_pool) - self.forget_indices

        # Strict validation checks
        assert len(self.forget_indices.intersection(self.retain_indices)) == 0, "Retain and forget sets overlap!"
        assert len(self.forget_indices.intersection(self.val_indices)) == 0, "Forget set overlaps with validation set!"
        assert len(self.retain_indices.intersection(self.val_indices)) == 0, "Retain set overlaps with validation set!"
        assert len(self.forget_indices) + len(self.retain_indices) == len(candidate_pool), "Partition sizes do not sum to total available train pool!"

        # Compute class distributions
        forget_class_counts: Dict[int, int] = {}
        for idx in self.forget_indices:
            c = self._targets_cache[idx]
            forget_class_counts[c] = forget_class_counts.get(c, 0) + 1

        retain_class_counts: Dict[int, int] = {}
        for idx in self.retain_indices:
            c = self._targets_cache[idx]
            retain_class_counts[c] = retain_class_counts.get(c, 0) + 1

        manifest = {
            "strategy": strategy,
            "percentage": percentage,
            "target_class": target_class,
            "group_id": group_id,
            "seed": self.seed,
            "total_samples": len(candidate_pool),
            "retain_count": len(self.retain_indices),
            "forget_count": len(self.forget_indices),
            "val_count": len(self.val_indices),
            "forget_ratio": round(len(self.forget_indices) / len(candidate_pool), 4),
            "forget_class_distribution": forget_class_counts,
            "retain_class_distribution": retain_class_counts,
            "manifest_hash": self._compute_hash(list(self.retain_indices), list(self.forget_indices)),
        }
        self.split_metadata.update(manifest)
        return manifest

    def _compute_hash(self, retain: List[int], forget: List[int]) -> str:
        s = f"retain:{sorted(retain)}|forget:{sorted(forget)}|seed:{self.seed}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

    def get_subsets(self) -> Tuple[Subset, Subset, Subset]:
        """Returns (retain_dataset, forget_dataset, val_dataset) as PyTorch Subsets."""
        retain_ds = Subset(self.train_dataset, sorted(list(self.retain_indices)))
        forget_ds = Subset(self.train_dataset, sorted(list(self.forget_indices)))
        val_ds = Subset(self.train_dataset, sorted(list(self.val_indices)))
        return retain_ds, forget_ds, val_ds

    def get_indices_dict(self) -> Dict[str, List[int]]:
        return {
            "retain_indices": sorted(list(self.retain_indices)),
            "forget_indices": sorted(list(self.forget_indices)),
            "val_indices": sorted(list(self.val_indices)),
        }
