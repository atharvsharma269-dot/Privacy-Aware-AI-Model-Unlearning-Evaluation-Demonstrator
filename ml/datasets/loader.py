import os
from typing import Tuple, Dict, Any, List
import numpy as np
import torch
from torch.utils.data import Dataset, Subset
import torchvision
from torchvision import transforms

FASHION_MNIST_CLASSES = [
    "T-shirt/top",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle boot",
]

MNIST_CLASSES = [
    "Digit 0",
    "Digit 1",
    "Digit 2",
    "Digit 3",
    "Digit 4",
    "Digit 5",
    "Digit 6",
    "Digit 7",
    "Digit 8",
    "Digit 9",
]

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


class IndexedDataset(Dataset):
    """Wraps a PyTorch Dataset to return (index, image, target)."""

    def __init__(self, base_dataset):
        self.base_dataset = base_dataset

    def __len__(self) -> int:
        return len(self.base_dataset)

    def __getitem__(self, idx: int):
        img, target = self.base_dataset[idx]
        return idx, img, target


def get_dataset_class_names(dataset_name: str) -> List[str]:
    name = dataset_name.lower().replace("-", "").replace("_", "")
    if "tofu" in name:
        return TOFU_CLASSES
    if "fashion" in name:
        return FASHION_MNIST_CLASSES
    return MNIST_CLASSES


def load_raw_dataset(
    dataset_name: str = "fashion_mnist",
    data_dir: str = "./data",
    download: bool = True,
) -> Tuple[Dataset, Dataset, List[str]]:
    """
    Loads training and test datasets.
    Returns: (train_dataset, test_dataset, class_names)
    """
    os.makedirs(data_dir, exist_ok=True)
    name = dataset_name.lower().replace("-", "").replace("_", "")

    if "tofu" in name:
        from .tofu_loader import load_tofu_raw_dataset
        return load_tofu_raw_dataset(data_dir=data_dir)

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.2860,), (0.3530,)) if "fashion" in name else transforms.Normalize((0.1307,), (0.3081,)),
    ])

    if "fashion" in name:
        train_ds = torchvision.datasets.FashionMNIST(
            root=data_dir, train=True, download=download, transform=transform
        )
        test_ds = torchvision.datasets.FashionMNIST(
            root=data_dir, train=False, download=download, transform=transform
        )
        classes = FASHION_MNIST_CLASSES
    else:
        train_ds = torchvision.datasets.MNIST(
            root=data_dir, train=True, download=download, transform=transform
        )
        test_ds = torchvision.datasets.MNIST(
            root=data_dir, train=False, download=download, transform=transform
        )
        classes = MNIST_CLASSES

    return IndexedDataset(train_ds), IndexedDataset(test_ds), classes
