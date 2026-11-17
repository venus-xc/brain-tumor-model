"""Generates figs/fig_segmentation.png comparing Ground Truth, U-Net, and Attention U-Net predictions.
Selects 4 representative test cases across different tumor classes.
"""
import os
import cv2
import numpy as np
import torch
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "seg_256.npz")
WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "weights")
FIGS_DIR = os.path.join(PROJECT_ROOT, "figs")

os.makedirs(FIGS_DIR, exist_ok=True)

from app.models.unet import UNet
from app.models.attention_unet import AttentionUNet

LABEL_NAMES = {1: "Meningioma", 2: "Glioma", 3: "Pituitary"}


def main():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing {DATA_PATH}")

    unet_weight = os.path.join(WEIGHTS_DIR, "unet.pth")
    att_weight = os.path.join(WEIGHTS_DIR, "attunet.pth")
    if not os.path.exists(att_weight):
        att_weight = os.path.join(WEIGHTS_DIR, "att_unet.pth")

    if not os.path.exists(unet_weight) or not os.path.exists(att_weight):
        print(f"Weights missing for segmentation figure generation ({unet_weight}, {att_weight}). Skipping for now.")
        return

    # Load data
    d = np.load(DATA_PATH)
    Xte = d["X"][d["split"] == 2]
    Mte = d["M"][d["split"] == 2]
    Lte = d["label"][d["split"] == 2]
    Pte = d["pid"][d["split"] == 2]

    # Load models
    u_model = UNet(in_channels=1, out_channels=1)
    state_u = torch.load(unet_weight, map_location="cpu")
    if "inc.double_conv.0.weight" in state_u and state_u["inc.double_conv.0.weight"].shape[1] == 3:
        state_u["inc.double_conv.0.weight"] = state_u["inc.double_conv.0.weight"].mean(dim=1, keepdim=True)
    u_model.load_state_dict(state_u)
    u_model.eval()

    au_model = AttentionUNet(in_channels=1, out_channels=1)
    state_a = torch.load(att_weight, map_location="cpu")
    if "conv1.conv.0.weight" in state_a and state_a["conv1.conv.0.weight"].shape[1] == 3:
        state_a["conv1.conv.0.weight"] = state_a["conv1.conv.0.weight"].mean(dim=1, keepdim=True)
    au_model.load_state_dict(state_a)
    au_model.eval()

    # Pick 4 distinct test cases: 1 Meningioma, 2 Gliomas, 1 Pituitary
    sel_indices = []
    for target_lbl, count in [(1, 1), (2, 2), (3, 1)]:
        matches = np.where(Lte == target_lbl)[0]
        # Choose ones with substantial tumor area
        areas = [Mte[idx].sum() for idx in matches]
        ranked = matches[np.argsort(-np.array(areas))]
        sel_indices.extend(ranked[:count])

    fig, axs = plt.subplots(4, 4, figsize=(11, 11))
    col_titles = ["Input MRI (256x256)", "Ground Truth Mask", "U-Net Prediction", "Attention U-Net Prediction"]

    def overlay_mask(img, mask, color=(0, 255, 0)):
        # Color overlay on grayscale image
        base = np.stack([img] * 3, axis=-1)
        overlay = base.copy()
        overlay[mask > 0] = color
        return cv2.addWeighted(base, 0.65, overlay, 0.35, 0)

    with torch.no_grad():
        for row, idx in enumerate(sel_indices):
            img = Xte[idx]
            gt = Mte[idx]
            lbl_name = LABEL_NAMES.get(int(Lte[idx]), "Tumor")
            pid = Pte[idx]

            t = torch.from_numpy(img).float().div(255.0).unsqueeze(0).unsqueeze(0)
            u_pred = (u_model(t, return_logits=False)[0, 0].numpy() >= 0.5).astype(np.uint8)
            au_pred = (au_model(t, return_logits=False)[0, 0].numpy() >= 0.5).astype(np.uint8)

            # Column 0: Input image
            axs[row, 0].imshow(img, cmap="gray")
            axs[row, 0].set_ylabel(f"Case {row + 1}\n{lbl_name}\n(PID: {pid})", fontsize=10, weight="bold")

            # Column 1: Ground Truth
            axs[row, 1].imshow(overlay_mask(img, gt, color=(0, 230, 115)))

            # Column 2: U-Net
            # Compute dice
            inter_u = (u_pred * gt).sum()
            dice_u = (2.0 * inter_u) / (u_pred.sum() + gt.sum() + 1e-6)
            axs[row, 2].imshow(overlay_mask(img, u_pred, color=(66, 133, 244)))
            axs[row, 2].set_title(f"Dice: {dice_u:.3f}", fontsize=9)

            # Column 3: Attention U-Net
            inter_au = (au_pred * gt).sum()
            dice_au = (2.0 * inter_au) / (au_pred.sum() + gt.sum() + 1e-6)
            axs[row, 3].imshow(overlay_mask(img, au_pred, color=(234, 67, 53)))
            axs[row, 3].set_title(f"Dice: {dice_au:.3f}", fontsize=9)

    for c, title in enumerate(col_titles):
        axs[0, c].set_title(f"{title}\n" + axs[0, c].get_title() if axs[0, c].get_title() else title, fontsize=10, weight="bold")

    for ax in axs.flat:
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    out_file = os.path.join(FIGS_DIR, "fig_segmentation.png")
    fig.savefig(out_file, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved segmentation comparison figure to {out_file}")


if __name__ == "__main__":
    main()
