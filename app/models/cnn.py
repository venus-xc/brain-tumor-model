"""Custom CNN and Squeeze-and-Excitation CNN (SE-CNN) architectures.
Trained from scratch for 4-class brain tumor classification.
Architecture: 4 conv blocks [32, 64, 128, 256] -> GAP -> FC(128) -> Dropout(0.4) -> FC(4).
se=True adds an SEBlock at the end of each conv block.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class SEBlock(nn.Module):
    """Squeeze-and-Excitation block: z = GAP(X); s = sigmoid(W2 relu(W1 z)); X~ = s * X"""

    def __init__(self, c: int, r: int = 8):
        super().__init__()
        self.fc1 = nn.Linear(c, c // r)
        self.fc2 = nn.Linear(c // r, c)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = x.mean((2, 3))
        s = torch.sigmoid(self.fc2(F.relu(self.fc1(z))))
        return x * s[:, :, None, None]


def conv_block(cin: int, cout: int, se: bool = False) -> nn.Sequential:
    layers = [
        nn.Conv2d(cin, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
    ]
    if se:
        layers.append(SEBlock(cout))
    layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)


class BrainCNN(nn.Module):
    """Custom CNN / SE-CNN classifier.
    Display names:
      - se=False: "Custom CNN"
      - se=True:  "SE-CNN"
    """

    def __init__(self, n_classes: int = 4, se: bool = False, in_ch: int = 1):
        super().__init__()
        self.se = se
        ch = [32, 64, 128, 256]
        blocks = []
        c = in_ch
        for o in ch:
            blocks.append(conv_block(c, o, se))
            c = o
        self.features = nn.Sequential(*blocks)
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(c, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(128, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        f = self.features(x)
        return self.head(F.adaptive_avg_pool2d(f, 1))
