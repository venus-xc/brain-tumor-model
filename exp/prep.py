"""Preprocess the public SARTAJ Brain Tumor Classification (MRI) dataset.
Steps: grayscale -> brain-region crop (largest contour) -> CLAHE -> resize.
Caches arrays to data/cache_{size}.npz and runs a near-duplicate audit (train vs test).
"""
import glob, os, sys, json
import numpy as np, cv2
from PIL import Image

ROOT = sys.argv[1] if len(sys.argv) > 1 else "data/sartaj"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data"
CLASSES = ["no_tumor", "glioma_tumor", "meningioma_tumor", "pituitary_tumor"]  # index 0..3
SIZE = 192

def crop_brain(g):
    blur = cv2.GaussianBlur(g, (5, 5), 0)
    _, th = cv2.threshold(blur, 45, 255, cv2.THRESH_BINARY)
    th = cv2.erode(th, None, iterations=2); th = cv2.dilate(th, None, iterations=2)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return g
    c = max(cnts, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    if w * h < 0.1 * g.shape[0] * g.shape[1]:
        return g
    return g[y:y + h, x:x + w]

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

def load(path):
    g = np.array(Image.open(path).convert("L"))
    g = crop_brain(g)
    g = clahe.apply(g)
    return cv2.resize(g, (SIZE, SIZE), interpolation=cv2.INTER_AREA)

def ahash(img):
    s = cv2.resize(img, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
    return (s > s.mean()).flatten()

out = {}
for split, folder in [("train", "Training"), ("test", "Testing")]:
    X, y, paths = [], [], []
    for ci, c in enumerate(CLASSES):
        for p in sorted(glob.glob(f"{ROOT}/{folder}/{c}/*")):
            X.append(load(p)); y.append(ci); paths.append(p)
    out[split] = (np.stack(X), np.array(y), paths)
    print(split, out[split][0].shape, np.bincount(y))

np.savez_compressed(f"{OUT}/cache_{SIZE}.npz",
                    Xtr=out["train"][0], ytr=out["train"][1],
                    Xte=out["test"][0], yte=out["test"][1])
json.dump({"train": out["train"][2], "test": out["test"][2]}, open(f"{OUT}/paths.json", "w"))

# near-duplicate audit (average-hash, Hamming distance <= 6 of 256 bits)
Htr = np.stack([ahash(i) for i in out["train"][0]])
Hte = np.stack([ahash(i) for i in out["test"][0]])
dups = 0
for h in Hte:
    d = (Htr != h).sum(1)
    if d.min() <= 6:
        dups += 1
print("test images with near-duplicate in train:", dups, "of", len(Hte))
json.dump({"near_dup_test_in_train": int(dups), "n_test": int(len(Hte))}, open(f"{OUT}/dup_audit.json", "w"))
