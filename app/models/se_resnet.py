import torch
import torch.nn as nn
import torch.nn.functional as F

class SqueezeExcitation(nn.Module):
    """
    Squeeze-and-Excitation (SE) Block (IEEE TPAMI / IEEE Access).
    Adaptively recalibrates channel-wise feature responses by modeling
    interdependencies between channels:
    - Squeeze: Global Average Pooling across spatial dimensions
    - Excitation: Two Fully Connected layers with reduction ratio r
    - Scale: Sigmoid channel activation
    """
    def __init__(self, channels, reduction=16):
        super().__init__()
        self.fc1 = nn.Linear(channels, max(channels // reduction, 8), bias=False)
        self.relu = nn.ReLU(inplace=True)
        self.fc2 = nn.Linear(max(channels // reduction, 8), channels, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        b, c, _, _ = x.size()
        y = x.view(b, c, -1).mean(dim=2)  # Global Average Pooling [B, C]
        y = self.fc1(y)
        y = self.relu(y)
        y = self.fc2(y)
        y = self.sigmoid(y).view(b, c, 1, 1)  # Excitation weight [B, C, 1, 1]
        return x * y.expand_as(x)


class SEBasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1, reduction=16):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        # Squeeze-and-Excitation Attention
        self.se = SqueezeExcitation(out_channels, reduction=reduction)
        
        # Residual Shortcut
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        residual = self.shortcut(x)
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out = self.se(out)
        out += residual
        return self.relu(out)


class SEResNetClassifier(nn.Module):
    """
    Squeeze-and-Excitation Residual Neural Network (SE-ResNet)
    for Multi-Class Brain Tumor Classification (Glioma, Meningioma, Pituitary, Normal).
    Features channel attention recalibration and exposes final conv layer for Grad-CAM / Grad-CAM++.
    """
    def __init__(self, num_classes=4, in_channels=3):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        )
        
        self.stage1 = SEBasicBlock(32, 64, stride=1)
        self.stage2 = SEBasicBlock(64, 128, stride=2)
        self.stage3 = SEBasicBlock(128, 256, stride=2)
        self.stage4 = SEBasicBlock(256, 512, stride=2)
        
        # Target layer for Grad-CAM and Grad-CAM++
        self.last_conv_layer = self.stage4.conv2
        
        # Global pooling and classification head
        self.gap = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(512, 256),
            nn.LayerNorm(256),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.stem(x)
        x = self.stage1(x)
        x = self.stage2(x)
        x = self.stage3(x)
        x = self.stage4(x)
        x = self.gap(x)
        return self.fc(x)

    def predict_probabilities(self, x):
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return F.softmax(logits, dim=1)
