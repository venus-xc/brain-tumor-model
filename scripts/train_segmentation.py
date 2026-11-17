"""Segmentation Training & Evaluation Script.
Supports U-Net and Attention U-Net on Figshare patient-level split (256x256 single-channel).
Loss: BCEWithLogits + Soft Dice (smooth 1.0).
Optimizer: Adam lr 1e-3, CosineAnnealingLR, 40 epochs, batch size 8.
Augmentation: horizontal flips, +-10 deg rotation applied identically to image & mask.
Evaluates on held-out patient-level test split (Dice, IoU, per-class Dice).
Saves weights to weights/{arch}.pth and updates results/segmentation.json.
"""
import argparse
import json
import os
import sys
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.models.unet import UNet
from app.models.attention_unet import AttentionUNet

WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "weights")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

os.makedirs(WEIGHTS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# 1 = meningioma, 2 = glioma, 3 = pituitary
LABEL_NAMES = {1: "meningioma", 2: "glioma", 3: "pituitary"}


def select_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def dice_loss(pred_probs: torch.Tensor, targets: torch.Tensor, smooth: float = 1.0) -> torch.Tensor:
    intersection = (pred_probs * targets).sum(dim=(2, 3))
    cardinality = pred_probs.sum(dim=(2, 3)) + targets.sum(dim=(2, 3))
    dice = (2.0 * intersection + smooth) / (cardinality + smooth)
    return 1.0 - dice.mean()


def compute_metrics(preds_binary: np.ndarray, masks: np.ndarray):
    """Computes mean per-image Dice and IoU."""
    dices, ious = [], []
    for i in range(len(preds_binary)):
        p = preds_binary[i].astype(np.float32)
        m = masks[i].astype(np.float32)
        inter = (p * m).sum()
        union = p.sum() + m.sum() - inter
        d = (2.0 * inter + 1e-6) / (p.sum() + m.sum() + 1e-6)
        iou = (inter + 1e-6) / (union + 1e-6)
        dices.append(float(d))
        ious.append(float(iou))
    return np.array(dices), np.array(ious)


def main():
    parser = argparse.ArgumentParser(description="Train brain tumor segmentation models")
    parser.add_argument("--arch", choices=["unet", "attunet"], required=True)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--bs", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = select_device()
    print(f"Selected compute device: {device.type.upper()}")

    # Load data
    npz_path = os.path.join(DATA_DIR, "seg_256.npz")
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"Missing {npz_path}. Run scripts/prepare_segmentation.py first.")

    d = np.load(npz_path)
    X, M, labels, pids, split = d["X"], d["M"], d["label"], d["pid"], d["split"]

    Xtr, Mtr = X[split == 0], M[split == 0]
    Xva, Mva = X[split == 1], M[split == 1]
    Xte, Mte, Lte, Pte = X[split == 2], M[split == 2], labels[split == 2], pids[split == 2]

    n_test_imgs = len(Xte)
    n_test_pids = len(np.unique(Pte))

    # Convert to float tensors normalized to [0, 1]
    def make_tensors(x_arr, m_arr):
        xt = torch.from_numpy(x_arr).float().div(255.0).unsqueeze(1)
        mt = torch.from_numpy(m_arr).float().unsqueeze(1)
        return xt, mt

    T_xtr, T_mtr = make_tensors(Xtr, Mtr)
    T_xva, T_mva = make_tensors(Xva, Mva)
    T_xte, T_mte = make_tensors(Xte, Mte)

    # Initialize model
    if args.arch == "unet":
        model = UNet(in_channels=1, out_channels=1)
    else:
        model = AttentionUNet(in_channels=1, out_channels=1)

    model = model.to(device)
    nparams = sum(p.numel() for p in model.parameters())
    print(f"\nTraining Architecture: {args.arch.upper()} | Parameters: {nparams:,}")
    print(f"Train images: {len(Xtr)} | Val images: {len(Xva)} | Test images: {n_test_imgs} ({n_test_pids} patients)")

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)

    def augment(xb, mb):
        # Stack image and mask along channel dimension to ensure identical spatial transform
        combined = torch.cat([xb, mb], dim=1)
        if torch.rand(1) < 1.0:
            flip = torch.rand(combined.size(0)) < 0.5
            combined[flip] = combined[flip].flip(-1)
        # Random rotation +- 10 deg
        ang = (torch.rand(combined.size(0)) * 20 - 10) * np.pi / 180
        cos, sin = torch.cos(ang), torch.sin(ang)
        theta = torch.stack(
            [torch.stack([cos, -sin, torch.zeros_like(cos)], 1), torch.stack([sin, cos, torch.zeros_like(cos)], 1)], 1
        )
        grid = F.affine_grid(theta, combined.shape, align_corners=False)
        combined = F.grid_sample(combined, grid, padding_mode="border", align_corners=False)
        xb_aug = combined[:, :1]
        mb_aug = (combined[:, 1:] > 0.5).float()
        return xb_aug, mb_aug

    @torch.no_grad()
    def evaluate_dice(x_tensors, m_tensors):
        model.eval()
        dices = []
        for i in range(0, len(x_tensors), 16):
            xb = x_tensors[i : i + 16].to(device)
            mb = m_tensors[i : i + 16].to(device)
            logits = model(xb, return_logits=True)
            probs = torch.sigmoid(logits)
            inter = (probs * mb).sum(dim=(2, 3))
            card = probs.sum(dim=(2, 3)) + mb.sum(dim=(2, 3))
            d = (2.0 * inter + 1e-6) / (card + 1e-6)
            dices.extend(d.squeeze(1).cpu().numpy().tolist())
        return float(np.mean(dices))

    best_val_dice = -1.0
    best_state = None
    t0 = time.time()

    for ep in range(args.epochs):
        model.train()
        perm = torch.randperm(len(T_xtr))
        train_loss = 0.0
        n_batches = 0

        for i in range(0, len(perm), args.bs):
            b = perm[i : i + args.bs]
            xb, mb = augment(T_xtr[b].clone(), T_mtr[b].clone())
            xb = xb.to(device)
            mb = mb.to(device)

            optimizer.zero_grad()
            logits = model(xb, return_logits=True)
            loss_bce = F.binary_cross_entropy_with_logits(logits, mb)
            loss_dice = dice_loss(torch.sigmoid(logits), mb, smooth=1.0)
            loss = loss_bce + loss_dice

            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            n_batches += 1

        scheduler.step()
        val_dice = evaluate_dice(T_xva, T_mva)
        avg_train_loss = train_loss / max(n_batches, 1)

        if val_dice > best_val_dice:
            best_val_dice = val_dice
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if (ep + 1) % 5 == 0 or ep == args.epochs - 1 or ep == 0:
            print(f"Epoch {ep + 1:2d}/{args.epochs:2d} | Train Loss: {avg_train_loss:.4f} | Val Dice: {val_dice:.4f} (Best: {best_val_dice:.4f}) | {time.time() - t0:.0f}s")

    print(f"\nTraining completed in {time.time() - t0:.1f}s. Best validation Dice: {best_val_dice:.4f}")
    model.load_state_dict(best_state)

    # Save weights
    weight_path = os.path.join(WEIGHTS_DIR, f"{args.arch}.pth")
    torch.save(best_state, weight_path)
    print(f"Saved weights to {weight_path}")
    if args.arch == "attunet":
        # Also save as att_unet.pth for existing API compatibility
        torch.save(best_state, os.path.join(WEIGHTS_DIR, "att_unet.pth"))

    # Test set evaluation
    model.eval()
    test_probs = []
    with torch.no_grad():
        for i in range(0, len(T_xte), 16):
            xb = T_xte[i : i + 16].to(device)
            logits = model(xb, return_logits=True)
            probs = torch.sigmoid(logits).cpu().numpy()
            test_probs.append(probs)
    test_probs = np.concatenate(test_probs, axis=0)  # [N, 1, 256, 256]
    test_binary = (test_probs >= 0.5).astype(np.float32)

    dices, ious = compute_metrics(test_binary, Mte)
    test_mean_dice = float(np.mean(dices))
    test_mean_iou = float(np.mean(ious))

    per_class_res = {}
    for lbl_id, name in LABEL_NAMES.items():
        cls_idx = np.where(Lte == lbl_id)[0]
        if len(cls_idx) > 0:
            cls_dice = float(np.mean(dices[cls_idx]))
            per_class_res[name] = round(cls_dice, 3)

    print(f"\n=== TEST SET RESULTS ({args.arch.upper()}) ===")
    print(f"Mean Dice Similarity Coefficient (DSC): {test_mean_dice:.4f} ({test_mean_dice * 100:.1f}%)")
    print(f"Mean Intersection over Union (IoU):     {test_mean_iou:.4f} ({test_mean_iou * 100:.1f}%)")
    print(f"Per-Class Dice: {per_class_res}")

    # Save / Update results/segmentation.json
    seg_json_path = os.path.join(RESULTS_DIR, "segmentation.json")
    seg_data = {}
    if os.path.exists(seg_json_path):
        try:
            with open(seg_json_path, "r") as f:
                seg_data = json.load(f)
        except Exception:
            seg_data = {}

    if "per_class_dice" not in seg_data:
        seg_data["per_class_dice"] = {}

    if args.arch == "unet":
        seg_data["unet_dice"] = round(test_mean_dice, 3)
        seg_data["unet_iou"] = round(test_mean_iou, 3)
        seg_data["unet_params"] = nparams
        seg_data["per_class_dice"]["unet"] = per_class_res
    else:
        seg_data["attunet_dice"] = round(test_mean_dice, 3)
        seg_data["attunet_iou"] = round(test_mean_iou, 3)
        seg_data["attunet_params"] = nparams
        seg_data["per_class_dice"]["attunet"] = per_class_res

    seg_data["n_test_images"] = int(n_test_imgs)
    seg_data["n_test_patients"] = int(n_test_pids)

    with open(seg_json_path, "w") as f:
        json.dump(seg_data, f, indent=1)
    print(f"Updated {seg_json_path}")


if __name__ == "__main__":
    main()
