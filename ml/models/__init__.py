from typing import Optional
import torch.nn as nn
from .mlp import FashionMLP
from .cnn import FashionCNN


def get_model(model_name: str = "mlp", num_classes: int = 10) -> nn.Module:
    """Factory function for model instantiation."""
    name = model_name.lower().strip()
    if name in ["mlp", "fashion_mlp", "multilayer_perceptron"]:
        return FashionMLP(num_classes=num_classes)
    elif name in ["cnn", "fashion_cnn", "convnet"]:
        return FashionCNN(num_classes=num_classes)
    else:
        raise ValueError(f"Unsupported model architecture: {model_name}. Choose 'mlp' or 'cnn'.")
