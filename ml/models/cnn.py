import torch
import torch.nn as nn
import torch.nn.functional as F


class FashionCNN(nn.Module):
    """
    Lightweight Convolutional Neural Network for 28x28 grayscale images.
    Architecture: Conv2d(1, 32, 3, pad=1) -> BatchNorm2d -> ReLU -> MaxPool2d(2)
                 -> Conv2d(32, 64, 3, pad=1) -> BatchNorm2d -> ReLU -> MaxPool2d(2)
                 -> Flatten -> Linear(64*7*7, 128) -> ReLU -> Dropout(0.3)
                 -> Linear(128, 10)
    """

    def __init__(self, in_channels: int = 1, num_classes: int = 10):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.3)
        
        # After two poolings of 28x28: 28 -> 14 -> 7
        self.fc1 = nn.Linear(64 * 7 * 7, 128)
        self.bn3 = nn.BatchNorm1d(128)
        self.fc2 = nn.Linear(128, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 3:
            x = x.unsqueeze(1)
        elif x.dim() == 2:
            x = x.view(-1, 1, 28, 28)
            
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        
        x = x.view(x.size(0), -1)
        x = self.dropout(F.relu(self.bn3(self.fc1(x))))
        logits = self.fc2(x)
        return logits

    def get_features(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 3:
            x = x.unsqueeze(1)
        elif x.dim() == 2:
            x = x.view(-1, 1, 28, 28)
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        x = x.view(x.size(0), -1)
        x = F.relu(self.bn3(self.fc1(x)))
        return x
