import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    """(Convolution => BatchNorm => ReLU) * 2"""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.double_conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.double_conv(x)


class Down(nn.Module):
    """Downscaling with maxpool then double conv"""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.maxpool_conv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.maxpool_conv(x)


class Up(nn.Module):
    """Upscaling then double conv with skip connection"""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class UNet(nn.Module):
    """Biomedical U-Net Architecture for Brain Tumor Semantic Segmentation.
    Display name: "U-Net"
    Input: Single-channel 256x256 brain MRI slice.
    Output: Single-channel binary lesion mask.
    """

    def __init__(self, in_channels: int = 1, out_channels: int = 1, features: list = [32, 64, 128, 256]):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        self.inc = DoubleConv(in_channels, features[0])
        self.down1 = Down(features[0], features[1])
        self.down2 = Down(features[1], features[2])
        self.down3 = Down(features[2], features[3])

        # Bottleneck
        self.bottleneck = DoubleConv(features[3], features[3] * 2)

        # Decoder with skip-connections
        self.up1 = Up(features[3] * 2, features[3])
        self.up2 = Up(features[3], features[2])
        self.up3 = Up(features[2], features[1])
        self.up4 = Up(features[1], features[0])

        # Final 1x1 conv
        self.outc = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor, return_logits: bool = False) -> torch.Tensor:
        if x.size(1) != self.in_channels:
            if x.size(1) == 3 and self.in_channels == 1:
                x = x.mean(dim=1, keepdim=True)
            elif x.size(1) == 1 and self.in_channels == 3:
                x = x.repeat(1, 3, 1, 1)

        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.bottleneck(x4)

        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)

        if return_logits:
            return logits
        return torch.sigmoid(logits)

    def segment(self, x: torch.Tensor, threshold: float = 0.5):
        self.eval()
        with torch.no_grad():
            prob_map = self.forward(x, return_logits=False)
            binary_mask = (prob_map >= threshold).float()
        return prob_map, binary_mask
