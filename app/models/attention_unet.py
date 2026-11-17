import torch
import torch.nn as nn
import torch.nn.functional as F

class AttentionGate(nn.Module):
    """
    Attention Gate (AG) as proposed in Oktay et al., 
    'Attention U-Net: Learning Where to Look for the Pancreas', IEEE TMI.
    
    Suppresses irrelevant feature responses in background tissue (skull, ventricles,
    normal brain parenchyma) while accentuating salient tumor regions on skip connections.
    """
    def __init__(self, F_g, F_l, F_int):
        """
        F_g: number of channels in gating signal (from deeper/coarser decoder level)
        F_l: number of channels in skip-connection feature map (from encoder)
        F_int: intermediate channel dimension
        """
        super().__init__()
        self.W_g = nn.Sequential(
            nn.Conv2d(F_g, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(F_int)
        )
        self.W_x = nn.Sequential(
            nn.Conv2d(F_l, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(F_int)
        )
        self.psi = nn.Sequential(
            nn.Conv2d(F_int, 1, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(1),
            nn.Sigmoid()
        )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        """
        g: gating signal [B, F_g, H_g, W_g]
        x: skip connection [B, F_l, H_x, W_x]
        """
        # Downsample or upsample g if dimensions differ
        if g.size()[2:] != x.size()[2:]:
            g = F.interpolate(g, size=x.size()[2:], mode='bilinear', align_corners=True)

        g1 = self.W_g(g)
        x1 = self.W_x(x)
        psi = self.relu(g1 + x1)
        alpha = self.psi(psi)  # Attention coefficients in [0, 1]
        
        # Multiply element-wise by attention mask
        return x * alpha, alpha


class ConvBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)


class UpConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.up = nn.Sequential(
            nn.Upsample(scale_factor=2, mode='bilinear', align_corners=True),
            nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.up(x)


class AttentionUNet(nn.Module):
    """
    Attention U-Net Architecture (IEEE Reference: Oktay et al., IEEE TMI).
    Integrates spatial Attention Gates to adaptively focus on tumor boundaries.
    """
    def __init__(self, in_channels=3, out_channels=1, features=[32, 64, 128, 256]):
        super().__init__()
        
        # Contracting Encoder
        self.conv1 = ConvBlock(in_channels, features[0])
        self.pool1 = nn.MaxPool2d(2)
        
        self.conv2 = ConvBlock(features[0], features[1])
        self.pool2 = nn.MaxPool2d(2)
        
        self.conv3 = ConvBlock(features[1], features[2])
        self.pool3 = nn.MaxPool2d(2)
        
        self.conv4 = ConvBlock(features[2], features[3])
        self.pool4 = nn.MaxPool2d(2)
        
        # Bottleneck
        self.bottleneck = ConvBlock(features[3], features[3] * 2)
        
        # Expanding Decoder with Attention Gates
        self.up4 = UpConv(features[3] * 2, features[3])
        self.ag4 = AttentionGate(F_g=features[3], F_l=features[3], F_int=features[2])
        self.conv_up4 = ConvBlock(features[3] * 2, features[3])
        
        self.up3 = UpConv(features[3], features[2])
        self.ag3 = AttentionGate(F_g=features[2], F_l=features[2], F_int=features[1])
        self.conv_up3 = ConvBlock(features[2] * 2, features[2])
        
        self.up2 = UpConv(features[2], features[1])
        self.ag2 = AttentionGate(F_g=features[1], F_l=features[1], F_int=features[0])
        self.conv_up2 = ConvBlock(features[1] * 2, features[1])
        
        self.up1 = UpConv(features[1], features[0])
        self.ag1 = AttentionGate(F_g=features[0], F_l=features[0], F_int=features[0] // 2)
        self.conv_up1 = ConvBlock(features[0] * 2, features[0])
        
        # 1x1 Convolution Segmentation Output
        self.final = nn.Conv2d(features[0], out_channels, kernel_size=1)
        
        # Cache for latest attention maps for XAI inspection
        self.latest_attention_maps = {}

    def forward(self, x):
        # Encoder
        x1 = self.conv1(x)
        p1 = self.pool1(x1)
        
        x2 = self.conv2(p1)
        p2 = self.pool2(x2)
        
        x3 = self.conv3(p2)
        p3 = self.pool3(x3)
        
        x4 = self.conv4(p3)
        p4 = self.pool4(x4)
        
        # Bottleneck
        bn = self.bottleneck(p4)
        
        # Decoder Stage 4
        d4 = self.up4(bn)
        x4_att, alpha4 = self.ag4(g=d4, x=x4)
        d4 = torch.cat((x4_att, d4), dim=1)
        d4 = self.conv_up4(d4)
        
        # Decoder Stage 3
        d3 = self.up3(d4)
        x3_att, alpha3 = self.ag3(g=d3, x=x3)
        d3 = torch.cat((x3_att, d3), dim=1)
        d3 = self.conv_up3(d3)
        
        # Decoder Stage 2
        d2 = self.up2(d3)
        x2_att, alpha2 = self.ag2(g=d2, x=x2)
        d2 = torch.cat((x2_att, d2), dim=1)
        d2 = self.conv_up2(d2)
        
        # Decoder Stage 1
        d1 = self.up1(d2)
        x1_att, alpha1 = self.ag1(g=d1, x=x1)
        d1 = torch.cat((x1_att, d1), dim=1)
        d1 = self.conv_up1(d1)
        
        out = torch.sigmoid(self.final(d1))
        
        # Store attention maps for visualization
        self.latest_attention_maps = {
            "ag1": alpha1.detach(),
            "ag2": alpha2.detach(),
            "ag3": alpha3.detach(),
            "ag4": alpha4.detach()
        }
        
        return out
