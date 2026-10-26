import torch
import torch.nn as nn
import torch.nn.functional as F


class FashionMLP(nn.Module):
    """
    Multilayer Perceptron baseline for 28x28 grayscale image classification.
    Architecture: Flatten(784) -> Linear(256) -> BatchNorm1d -> ReLU -> Dropout(0.2)
                 -> Linear(128) -> BatchNorm1d -> ReLU -> Dropout(0.2)
                 -> Linear(10)
    """

    def __init__(self, input_dim: int = 784, hidden_dim1: int = 256, hidden_dim2: int = 128, num_classes: int = 10):
        super().__init__()
        self.input_dim = input_dim
        self.fc1 = nn.Linear(input_dim, hidden_dim1)
        self.bn1 = nn.BatchNorm1d(hidden_dim1)
        self.dropout1 = nn.Dropout(0.2)
        
        self.fc2 = nn.Linear(hidden_dim1, hidden_dim2)
        self.bn2 = nn.BatchNorm1d(hidden_dim2)
        self.dropout2 = nn.Dropout(0.2)
        
        self.fc3 = nn.Linear(hidden_dim2, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = self.dropout1(F.relu(self.bn1(self.fc1(x))))
        x = self.dropout2(F.relu(self.bn2(self.fc2(x))))
        logits = self.fc3(x)
        return logits

    def get_features(self, x: torch.Tensor) -> torch.Tensor:
        """Extract pen-ultimate layer representation for analysis."""
        if x.dim() > 2:
            x = x.view(x.size(0), -1)
        x = F.relu(self.bn1(self.fc1(x)))
        x = F.relu(self.bn2(self.fc2(x)))
        return x
