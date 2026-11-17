"""Deep Learning Classifier Training & Evaluation Script.
Ports reference_code/exp/train_cls.py.
Models:
  - cnn:   BrainCNN (se=False) [32, 64, 128, 256], 128px, 15 epochs, lr 2e-3
  - secnn: BrainCNN (se=True)  [32, 64, 128, 256], 128px, 15 epochs, lr 2e-3
  - effb0: EfficientNet-B0 transfer learning,     160px, 12 epochs, lr 1e-3
Splits:
  - clean:    Leakage-free 70/15/15 stratified group split
  - official: Sartaj official train/test split (used for leakage quantification)
Device: Auto-selects mps -> cuda -> cpu.
"""
import argparse
import json
import os
import sys
import time
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.models.cnn import BrainCNN
from app.models.efficientnet import build_efficientnet_b0

WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "weights")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "processed")

os.makedirs(WEIGHTS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def select_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def parse_args():
    parser = argparse.ArgumentParser(description="Train brain tumor classification models")
    parser.add_argument("--model", choices=["cnn", "secnn", "effb0"], default="cnn")
    parser.add_argument("--split", choices=["clean", "official"], default="clean")
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--bs", type=int, default=32)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main():
    args = parse_args()

    # Set hyperparameters based on specifications if not explicitly given
    if args.size is None:
        args.size = 160 if args.model == "effb0" else 128
    if args.epochs is None:
        if args.model == "effb0":
            args.epochs = 6 if args.split == "official" else 12
        else:
            args.epochs = 15
    if args.lr is None:
        args.lr = 1e-3 if args.model == "effb0" else 2e-3

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = select_device()
    print(f"Selected compute device: {device.type.upper()}")

    tag = f"{args.model}_{args.split}"
    print(f"\n==========================================")
    print(f"Training: {tag} | Resolution: {args.size}x{args.size} | Epochs: {args.epochs} | LR: {args.lr}")
    print(f"==========================================")

    # Load data
    if args.split == "clean":
        clean_npz = os.path.join(DATA_DIR, "clean_192.npz")
        if not os.path.exists(clean_npz):
            clean_npz = os.path.join(PROJECT_ROOT, "data", "clean_192.npz")
        d = np.load(clean_npz)
        X, y, sp = d["X"], d["y"], d["split"]
        Xtr, ytr = X[sp == 0], y[sp == 0]
        Xva, yva = X[sp == 1], y[sp == 1]
        Xte, yte = X[sp == 2], y[sp == 2]
    else:
        cache_npz = os.path.join(DATA_DIR, "cache_192.npz")
        if not os.path.exists(cache_npz):
            cache_npz = os.path.join(PROJECT_ROOT, "data", "cache_192.npz")
        d = np.load(cache_npz)
        rng = np.random.RandomState(42)
        idx = rng.permutation(len(d["ytr"]))
        nv = int(0.15 * len(idx))
        Xva, yva = d["Xtr"][idx[:nv]], d["ytr"][idx[:nv]]
        Xtr, ytr = d["Xtr"][idx[nv:]], d["ytr"][idx[nv:]]
        Xte, yte = d["Xte"], d["yte"]

    def resize_batch(arr):
        if arr.shape[1] != args.size:
            return np.stack([cv2.resize(img, (args.size, args.size), interpolation=cv2.INTER_AREA) for img in arr])
        return arr

    Xtr = resize_batch(Xtr)
    Xva = resize_batch(Xva)
    Xte = resize_batch(Xte)

    rgb = args.model == "effb0"
    MEAN = (0.485, 0.456, 0.406)
    STD = (0.229, 0.224, 0.225)

    def to_tensor(arr):
        t = torch.from_numpy(arr).float().div(255.0).unsqueeze(1)
        if rgb:
            t = t.repeat(1, 3, 1, 1)
            t = (t - torch.tensor(MEAN)[None, :, None, None]) / torch.tensor(STD)[None, :, None, None]
        else:
            t = (t - 0.5) / 0.25
        return t

    Ttr = to_tensor(Xtr)
    Tva = to_tensor(Xva)
    Tte = to_tensor(Xte)
    Ytr = torch.from_numpy(ytr).long()

    def augment(xb):
        if torch.rand(1) < 1.0:
            flip = torch.rand(xb.size(0)) < 0.5
            xb[flip] = xb[flip].flip(-1)
        ang = (torch.rand(xb.size(0)) * 20 - 10) * np.pi / 180
        sc = torch.rand(xb.size(0)) * 0.2 + 0.9
        cos, sin = torch.cos(ang) / sc, torch.sin(ang) / sc
        theta = torch.stack(
            [torch.stack([cos, -sin, torch.zeros_like(cos)], 1), torch.stack([sin, cos, torch.zeros_like(cos)], 1)], 1
        )
        grid = F.affine_grid(theta, xb.shape, align_corners=False)
        xb = F.grid_sample(xb, grid, padding_mode="border", align_corners=False)
        xb = xb * (torch.rand(xb.size(0), 1, 1, 1) * 0.2 + 0.9) + (torch.rand(xb.size(0), 1, 1, 1) * 0.2 - 0.1)
        return xb

    # Build model
    if args.model == "effb0":
        model = build_efficientnet_b0(n_classes=4, pretrained=True)
    elif args.model == "secnn":
        model = BrainCNN(n_classes=4, se=True, in_ch=1)
    else:
        model = BrainCNN(n_classes=4, se=False, in_ch=1)

    model = model.to(device)
    nparams = sum(p.numel() for p in model.parameters())
    print(f"Model: {args.model.upper()} | Parameters: {nparams:,} | Train: {len(ytr)} | Val: {len(yva)} | Test: {len(yte)}")

    # Class-weighted loss with label smoothing
    cw = torch.tensor(len(ytr) / (4.0 * np.bincount(ytr, minlength=4)), dtype=torch.float32).to(device)
    crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * int(np.ceil(len(ytr) / args.bs))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.2)

    @torch.no_grad()
    def predict(T):
        model.eval()
        out = []
        for i in range(0, len(T), 64):
            batch = T[i : i + 64].to(device)
            out.append(F.softmax(model(batch), 1).cpu())
        return torch.cat(out).numpy()

    hist = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    best_val_acc = -1.0
    best_state = None
    t0 = time.time()

    for ep in range(args.epochs):
        model.train()
        perm = torch.randperm(len(Ytr))
        tl, tc = 0.0, 0
        for i in range(0, len(perm), args.bs):
            b = perm[i : i + args.bs]
            xb = augment(Ttr[b].clone()).to(device)
            yb = Ytr[b].to(device)
            logits = model(xb)
            loss = crit(logits, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tl += loss.item() * len(b)
            tc += (logits.argmax(1) == yb).sum().item()

        pv = predict(Tva)
        vl = F.nll_loss(torch.log(torch.from_numpy(pv) + 1e-8), torch.from_numpy(yva).long()).item()
        va = float((pv.argmax(1) == yva).mean())

        hist["train_loss"].append(tl / len(Ytr))
        hist["train_acc"].append(tc / len(Ytr))
        hist["val_loss"].append(vl)
        hist["val_acc"].append(va)

        if va > best_val_acc:
            best_val_acc = va
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        print(f"Epoch {ep + 1:2d}/{args.epochs:2d} | Train Loss: {tl / len(Ytr):.4f} | Train Acc: {tc / len(Ytr):.4f} | Val Loss: {vl:.4f} | Val Acc: {va:.4f} ({time.time() - t0:.0f}s)")

    train_time = time.time() - t0
    model.load_state_dict(best_state)

    # Save weights to weights/ directory and results/ directory
    weight_dest = os.path.join(WEIGHTS_DIR, f"{tag}.pth")
    torch.save(best_state, weight_dest)
    print(f"\nSaved best model weights to {weight_dest}")
    torch.save(best_state, os.path.join(RESULTS_DIR, f"{tag}.pth"))

    # Test set evaluation
    t1 = time.time()
    pt = predict(Tte)
    infer_ms = (time.time() - t1) / len(Tte) * 1000
    pred = pt.argmax(1)

    p, r, f, _ = precision_recall_fscore_support(yte, pred, labels=[0, 1, 2, 3], zero_division=0)
    acc = float(accuracy_score(yte, pred))
    mf1 = float(f1_score(yte, pred, average="macro"))
    mprec = float(p.mean())
    mrec = float(r.mean())
    auc_score = float(roc_auc_score(yte, pt, multi_class="ovr", average="macro"))

    res = {
        "model": args.model,
        "split": args.split,
        "size": args.size,
        "epochs": args.epochs,
        "params": nparams,
        "accuracy": acc,
        "macro_f1": mf1,
        "macro_precision": mprec,
        "macro_recall": mrec,
        "per_class": {"precision": p.tolist(), "recall": r.tolist(), "f1": f.tolist()},
        "roc_auc_ovr_macro": auc_score,
        "confusion": confusion_matrix(yte, pred, labels=[0, 1, 2, 3]).tolist(),
        "best_val_acc": float(best_val_acc),
        "train_time_s": float(train_time),
        "cpu_infer_ms_per_img": float(infer_ms),
        "history": hist,
    }

    res_path = os.path.join(RESULTS_DIR, f"{tag}.json")
    with open(res_path, "w") as f:
        json.dump(res, f, indent=1)
    np.save(os.path.join(RESULTS_DIR, f"{tag}_probs.npy"), pt)
    np.save(os.path.join(RESULTS_DIR, f"{tag}_ytrue.npy"), yte)

    print(f"\n=== TEST EVALUATION ({tag.upper()}) ===")
    print(f"Accuracy:  {acc:.4f} ({acc * 100:.2f}%)")
    print(f"Macro F1:  {mf1:.4f}")
    print(f"ROC-AUC:   {auc_score:.4f}")
    print(f"Saved results to {res_path}")


if __name__ == "__main__":
    main()
