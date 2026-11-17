"""Train/evaluate a CNN classifier on the de-duplicated split (or the official split).
usage: python train_cls.py --model {cnn,secnn,effb0} --size 128 --epochs 20 --split {clean,official}
"""
import argparse, json, time, os, sys
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
import cv2
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score
sys.path.insert(0, os.path.dirname(__file__))
from models import BrainCNN, efficientnet_b0

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="cnn"); ap.add_argument("--size", type=int, default=128)
ap.add_argument("--epochs", type=int, default=20); ap.add_argument("--bs", type=int, default=32)
ap.add_argument("--lr", type=float, default=1e-3); ap.add_argument("--split", default="clean")
ap.add_argument("--out", default="results"); ap.add_argument("--seed", type=int, default=42)
a = ap.parse_args()
torch.manual_seed(a.seed); np.random.seed(a.seed); torch.set_num_threads(2)
os.makedirs(a.out, exist_ok=True)
tag = f"{a.model}_{a.split}"

if a.split == "clean":
    d = np.load("data/clean_192.npz"); X, y, sp = d["X"], d["y"], d["split"]
    Xtr, ytr, Xva, yva, Xte, yte = X[sp == 0], y[sp == 0], X[sp == 1], y[sp == 1], X[sp == 2], y[sp == 2]
else:  # official SARTAJ split (contains train/test near-duplicates) -> 85/15 train/val from Training
    d = np.load("data/cache_192.npz"); rng = np.random.RandomState(42)
    idx = rng.permutation(len(d["ytr"])); nv = int(0.15 * len(idx))
    Xva, yva = d["Xtr"][idx[:nv]], d["ytr"][idx[:nv]]; Xtr, ytr = d["Xtr"][idx[nv:]], d["ytr"][idx[nv:]]
    Xte, yte = d["Xte"], d["yte"]

def resize(X):
    return np.stack([cv2.resize(x, (a.size, a.size), interpolation=cv2.INTER_AREA) for x in X]) if X.shape[1] != a.size else X
Xtr, Xva, Xte = resize(Xtr), resize(Xva), resize(Xte)
rgb = a.model == "effb0"
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)

def to_tensor(X):
    t = torch.from_numpy(X).float().div(255.).unsqueeze(1)
    if rgb:
        t = t.repeat(1, 3, 1, 1)
        t = (t - torch.tensor(MEAN)[None, :, None, None]) / torch.tensor(STD)[None, :, None, None]
    else:
        t = (t - 0.5) / 0.25
    return t
Ttr, Tva, Tte = to_tensor(Xtr), to_tensor(Xva), to_tensor(Xte)
Ytr = torch.from_numpy(ytr).long()

def augment(xb):
    # random horizontal flip, random rotation (+-10 deg), random scale (0.9-1.1), brightness/contrast jitter
    if torch.rand(1) < 1.0:
        flip = torch.rand(xb.size(0)) < 0.5
        xb[flip] = xb[flip].flip(-1)
    ang = (torch.rand(xb.size(0)) * 20 - 10) * np.pi / 180
    sc = torch.rand(xb.size(0)) * 0.2 + 0.9
    cos, sin = torch.cos(ang) / sc, torch.sin(ang) / sc
    theta = torch.stack([torch.stack([cos, -sin, torch.zeros_like(cos)], 1), torch.stack([sin, cos, torch.zeros_like(cos)], 1)], 1)
    grid = F.affine_grid(theta, xb.shape, align_corners=False)
    xb = F.grid_sample(xb, grid, padding_mode="border", align_corners=False)
    xb = xb * (torch.rand(xb.size(0), 1, 1, 1) * 0.2 + 0.9) + (torch.rand(xb.size(0), 1, 1, 1) * 0.2 - 0.1)
    return xb

if a.model == "effb0":
    model = efficientnet_b0(4, "weights/effb0.pth")
else:
    model = BrainCNN(4, se=(a.model == "secnn"))
nparams = sum(p.numel() for p in model.parameters())
print(tag, "params", nparams, "train", len(ytr), "val", len(yva), "test", len(yte), flush=True)

# class-weighted cross entropy (no_tumor is the minority class)
cw = torch.tensor(len(ytr) / (4 * np.bincount(ytr, minlength=4)), dtype=torch.float32)
crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.05)
opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
steps = a.epochs * int(np.ceil(len(ytr) / a.bs))
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.2)

@torch.no_grad()
def predict(T):
    model.eval(); out = []
    for i in range(0, len(T), 64):
        out.append(F.softmax(model(T[i:i + 64]), 1))
    return torch.cat(out).numpy()

hist = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
best, best_state = -1, None; t0 = time.time()
for ep in range(a.epochs):
    model.train(); perm = torch.randperm(len(Ytr)); tl, tc = 0., 0
    for i in range(0, len(perm), a.bs):
        b = perm[i:i + a.bs]; xb = augment(Ttr[b].clone()); yb = Ytr[b]
        logits = model(xb); loss = crit(logits, yb)
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        tl += loss.item() * len(b); tc += (logits.argmax(1) == yb).sum().item()
    pv = predict(Tva)
    vl = F.nll_loss(torch.log(torch.from_numpy(pv) + 1e-8), torch.from_numpy(yva).long()).item()
    va = (pv.argmax(1) == yva).mean()
    hist["train_loss"].append(tl / len(Ytr)); hist["train_acc"].append(tc / len(Ytr))
    hist["val_loss"].append(vl); hist["val_acc"].append(float(va))
    if va > best:
        best = va; best_state = {k: v.clone() for k, v in model.state_dict().items()}
    print(f"ep {ep + 1}/{a.epochs} loss {tl / len(Ytr):.4f} acc {tc / len(Ytr):.4f} val_loss {vl:.4f} val_acc {va:.4f} t {time.time() - t0:.0f}s", flush=True)

train_time = time.time() - t0
model.load_state_dict(best_state)
torch.save(best_state, f"{a.out}/{tag}.pth")
t1 = time.time(); pt = predict(Tte); infer_ms = (time.time() - t1) / len(Tte) * 1000
pred = pt.argmax(1)
p, r, f, _ = precision_recall_fscore_support(yte, pred, labels=[0, 1, 2, 3], zero_division=0)
res = {"model": a.model, "split": a.split, "size": a.size, "epochs": a.epochs, "params": nparams,
       "accuracy": accuracy_score(yte, pred), "macro_f1": f1_score(yte, pred, average="macro"),
       "macro_precision": float(p.mean()), "macro_recall": float(r.mean()),
       "per_class": {"precision": p.tolist(), "recall": r.tolist(), "f1": f.tolist()},
       "roc_auc_ovr_macro": roc_auc_score(yte, pt, multi_class="ovr", average="macro"),
       "confusion": confusion_matrix(yte, pred, labels=[0, 1, 2, 3]).tolist(),
       "best_val_acc": float(best), "train_time_s": train_time, "cpu_infer_ms_per_img": infer_ms, "history": hist}
json.dump(res, open(f"{a.out}/{tag}.json", "w"), indent=1)
np.save(f"{a.out}/{tag}_probs.npy", pt); np.save(f"{a.out}/{tag}_ytrue.npy", yte)
print("TEST", tag, {k: res[k] for k in ["accuracy", "macro_f1", "roc_auc_ovr_macro"]}, flush=True)
