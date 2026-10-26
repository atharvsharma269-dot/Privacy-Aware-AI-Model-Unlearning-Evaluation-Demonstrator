"""
TOFU Dataset Loader & Auxiliary Text-Classification Proxy.

Scientific Clarification:
The official TOFU benchmark (Maini et al., 2024) is a generative language-model question-answering
benchmark. This module provides a fast, reproducible CPU-friendly AUXILIARY TEXT-CLASSIFICATION PROXY
(Author Identity Disclosure & Attribution).

TOFU Dataset Breakdown:
  - Total QA pairs: 4,000
  - Total fictitious authors: 200 (Author IDs 0..199, exactly 20 questions each)
  - Official forget10 split: 20 authors (Author IDs 180..199, indices 3600..3999, exactly 400 QA pairs)
  - Official retain90 split: 180 authors (Author IDs 0..179, indices 0..3599, exactly 3,600 QA pairs)
  - 10-Cohort Mapping: Cohort c in 0..9 contains all authors where (author_id % 10 == c).
    Each cohort comprises exactly 20 fictitious authors (400 QA pairs per cohort).
"""

import io
import os
import base64
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import torch
from torch.utils.data import Dataset, Subset
from sklearn.feature_extraction.text import TfidfVectorizer
from datasets import load_dataset
from .loader import IndexedDataset

TOFU_CLASSES = [
    "Cohort 0 (Jaime Vasquez + 19 authors)",
    "Cohort 1 (Chukwu Akabueze + 19 authors)",
    "Cohort 2 (Evelyn Desmet + 19 authors)",
    "Cohort 3 (Anara Yusifova + 19 authors)",
    "Cohort 4 (Jordan Sinclair + 19 authors)",
    "Cohort 5 (Aurelio Beltrán + 19 authors)",
    "Cohort 6 (Elliot Benson + 19 authors)",
    "Cohort 7 (Alejandro Tomasino + 19 authors)",
    "Cohort 8 (Ingrid Christensen + 19 authors)",
    "Cohort 9 (Simon Makoni + 19 authors)",
]

_CACHED_TOFU_DATA: Optional[Dict[str, Any]] = None


class TOFUDataset(Dataset):
    """
    PyTorch Dataset wrapping the TOFU Question-Answering & Author Attribution Benchmark.
    Returns: (features_tensor_784, class_label)
    """

    def __init__(self, features: np.ndarray, labels: List[int], raw_records: List[Dict[str, str]]):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.labels = torch.tensor(labels, dtype=torch.long)
        self.raw_records = raw_records

    def __len__(self) -> int:
        return len(self.labels)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.features[idx], self.labels[idx]

    def get_raw_sample(self, idx: int) -> Dict[str, Any]:
        rec = self.raw_records[idx]
        author_id = idx // 20
        target = (idx // 20) % 10
        return {
            "index": idx,
            "author_id": author_id,
            "cohort_class": target,
            "class_name": TOFU_CLASSES[target],
            "question": rec.get("question", ""),
            "answer": rec.get("answer", ""),
        }


def render_tofu_card_image(sample_info: Dict[str, Any]) -> str:
    """
    Renders an elegant 280x280 card representing a TOFU Question-Answer sample
    and returns a base64 encoded PNG data URI.
    """
    width, height = 280, 280
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Header banner
    draw.rectangle([(0, 0), (width, 50)], fill=(15, 30, 60))
    # Author tag badge
    draw.rounded_rectangle([(10, 10), (width - 10, 40)], radius=6, fill=(28, 55, 90))
    
    # Text drawing with fallback default font
    font = ImageFont.load_default()
    class_name = sample_info.get("class_name", "Author")
    draw.text((18, 18), f"TOFU: {class_name}", fill=(255, 255, 255), font=font)

    # Question Box
    draw.rounded_rectangle([(10, 60), (width - 10, 150)], radius=6, fill=(235, 242, 250), outline=(180, 205, 230))
    draw.text((18, 66), "QUESTION:", fill=(15, 45, 90), font=font)
    
    q_text = sample_info.get("question", "")
    # Word wrap manually for 3 lines
    words = q_text.split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 34:
            lines.append(" ".join(curr[:-1]))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    
    y = 84
    for line in lines[:3]:
        draw.text((18, y), line, fill=(30, 41, 59), font=font)
        y += 18
    if len(lines) > 3:
        draw.text((18, y), "...", fill=(100, 116, 139), font=font)

    # Answer Box
    draw.rounded_rectangle([(10, 160), (width - 10, 260)], radius=6, fill=(240, 253, 244), outline=(187, 247, 208))
    draw.text((18, 166), "ANSWER:", fill=(22, 101, 52), font=font)
    
    a_text = sample_info.get("answer", "")
    a_words = a_text.split()
    a_lines = []
    curr_a = []
    for w in a_words:
        curr_a.append(w)
        if len(" ".join(curr_a)) > 34:
            a_lines.append(" ".join(curr_a[:-1]))
            curr_a = [w]
    if curr_a:
        a_lines.append(" ".join(curr_a))
    
    ya = 184
    for line in a_lines[:3]:
        draw.text((18, ya), line, fill=(20, 83, 45), font=font)
        ya += 18
    if len(a_lines) > 3:
        draw.text((18, ya), "...", fill=(74, 222, 128), font=font)

    # Footer index
    idx_val = sample_info.get("index", 0)
    draw.text((14, 265), f"Sample #{idx_val} | 784-dim TF-IDF Representation", fill=(148, 163, 184), font=font)

    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")


def load_tofu_raw_dataset(
    data_dir: str = "./data",
) -> Tuple[IndexedDataset, IndexedDataset, List[str]]:
    """
    Loads the TOFU ('full') Question-Answering benchmark dataset from HuggingFace,
    transforms the QA texts into dense 784-dimensional feature embeddings,
    and returns (IndexedDataset(train), IndexedDataset(test), TOFU_CLASSES).
    """
    global _CACHED_TOFU_DATA
    if _CACHED_TOFU_DATA is not None:
        return _CACHED_TOFU_DATA["train"], _CACHED_TOFU_DATA["test"], _CACHED_TOFU_DATA["classes"]

    os.makedirs(data_dir, exist_ok=True)

    # Load official TOFU dataset ('full' configuration has 4,000 QA pairs across 200 fictitious authors)
    tofu_hf = load_dataset("locuslab/TOFU", "full")["train"]
    raw_records = [{"question": x["question"], "answer": x["answer"]} for x in tofu_hf]

    texts = [f"{x['question']} {x['answer']}" for x in raw_records]
    targets = [(i // 20) % 10 for i in range(len(raw_records))]

    # Vectorize to 784-dimensional features (compatible with baseline MLP and 28x28 shapes)
    vectorizer = TfidfVectorizer(max_features=784, ngram_range=(1, 2), stop_words="english")
    features = vectorizer.fit_transform(texts).toarray().astype(np.float32)

    # Standard split: 3,200 train samples (first 160 authors), 800 test samples (last 40 authors)
    train_slice = slice(0, 3200)
    test_slice = slice(3200, 4000)

    train_base = TOFUDataset(
        features=features[train_slice],
        labels=targets[train_slice],
        raw_records=raw_records[train_slice],
    )
    test_base = TOFUDataset(
        features=features[test_slice],
        labels=targets[test_slice],
        raw_records=raw_records[test_slice],
    )

    train_indexed = IndexedDataset(train_base)
    test_indexed = IndexedDataset(test_base)

    _CACHED_TOFU_DATA = {
        "train": train_indexed,
        "test": test_indexed,
        "classes": TOFU_CLASSES,
        "raw_train": train_base,
        "raw_test": test_base,
    }

    return train_indexed, test_indexed, TOFU_CLASSES


def get_tofu_raw_sample(idx: int, split: str = "train") -> Dict[str, Any]:
    """Helper to retrieve raw QA and rendered card for a TOFU sample."""
    global _CACHED_TOFU_DATA
    if _CACHED_TOFU_DATA is None:
        load_tofu_raw_dataset()

    base_ds = _CACHED_TOFU_DATA["raw_train"] if split == "train" else _CACHED_TOFU_DATA["raw_test"]
    if idx < 0 or idx >= len(base_ds):
        raise IndexError(f"Sample index {idx} out of range for TOFU {split} split")

    info = base_ds.get_raw_sample(idx)
    card_b64 = render_tofu_card_image(info)
    info["image_base64"] = card_b64
    return info

