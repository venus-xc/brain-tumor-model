import torch, torch.nn as nn, torch.nn.functional as F


class SEBlock(nn.Module):
    """Squeeze-and-Excitation: z = GAP(X); s = sigmoid(W2 relu(W1 z)); X~ = s * X"""
    def __init__(self, c, r=8):
        super().__init__()
        self.fc1 = nn.Linear(c, c // r); self.fc2 = nn.Linear(c // r, c)

    def forward(self, x):
        z = x.mean((2, 3))
        s = torch.sigmoid(self.fc2(F.relu(self.fc1(z))))
        return x * s[:, :, None, None]


def conv_block(cin, cout, se=False):
    layers = [nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
              nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True)]
    if se:
        layers.append(SEBlock(cout))
    layers.append(nn.MaxPool2d(2))
    return nn.Sequential(*layers)


class BrainCNN(nn.Module):
    """Custom CNN trained from scratch: 4 conv blocks [32,64,128,256] -> GAP -> FC(128) -> Dropout -> FC(4).
    se=True adds a Squeeze-and-Excitation block at the end of every conv block (SE-CNN)."""
    def __init__(self, n_classes=4, se=False, in_ch=1):
        super().__init__()
        ch = [32, 64, 128, 256]
        blocks, c = [], in_ch
        for o in ch:
            blocks.append(conv_block(c, o, se)); c = o
        self.features = nn.Sequential(*blocks)
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(c, 128), nn.ReLU(inplace=True), nn.Dropout(0.4), nn.Linear(128, n_classes))

    def forward(self, x):
        f = self.features(x)
        return self.head(F.adaptive_avg_pool2d(f, 1))


def efficientnet_b0(n_classes=4, weights=None):
    import timm
    m = timm.create_model("efficientnet_b0", pretrained=False, num_classes=1000)
    if weights:
        sd = torch.load(weights, map_location="cpu")
        missing, unexpected = m.load_state_dict(sd, strict=False)
        print("loaded ImageNet weights; missing", len(missing), "unexpected", len(unexpected))
    m.reset_classifier(n_classes)
    return m
