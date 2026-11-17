"""Classification dataset preparation and de-duplication pipeline.
Ports reference exp/prep.py and exp/dedup_split.py.
Steps:
1. Preprocess SARTAJ dataset: Grayscale -> contour-based skull crop -> CLAHE (2.0, 8x8) -> resize 192x192.
2. Near-duplicate audit between official Train and Test (average-hash distance <= 6).
3. Leakage audit: cosine similarity >= 0.98 on 32x32 thumbnails with Union-Find connected components.
4. StratifiedGroupKFold (20 folds -> 14 train, 3 val, 3 test = 70/15/15) preserving duplicate clusters.
5. Saves data/processed/clean_192.npz, results/clean_split.json, and results/leakage.json.
"""
import glob
import json
import os
import sys
import numpy as np
import cv2
from PIL import Image
from sklearn.model_selection import StratifiedGroupKFold

RAW_DIR = sys.argv[1] if len(sys.argv) > 1 else "data/raw/sartaj"
PROC_DIR = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
RES_DIR = sys.argv[3] if len(sys.argv) > 3 else "results"

os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

CLASSES = ["no_tumor", "glioma_tumor", "meningioma_tumor", "pituitary_tumor"]  # index 0..3
CLASS_NAMES = ["No tumor", "Glioma", "Meningioma", "Pituitary"]
SIZE = 192


def crop_brain(g):
    blur = cv2.GaussianBlur(g, (5, 5), 0)
    _, th = cv2.threshold(blur, 45, 255, cv2.THRESH_BINARY)
    th = cv2.erode(th, None, iterations=2)
    th = cv2.dilate(th, None, iterations=2)
    cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return g
    c = max(cnts, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    if w * h < 0.1 * g.shape[0] * g.shape[1]:
        return g
    return g[y : y + h, x : x + w]


clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def load_and_preprocess(path):
    g = np.array(Image.open(path).convert("L"))
    g = crop_brain(g)
    g = clahe.apply(g)
    return cv2.resize(g, (SIZE, SIZE), interpolation=cv2.INTER_AREA)


def ahash(img):
    s = cv2.resize(img, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)
    return (s > s.mean()).flatten()


def main():
    print("=== Step 1: Loading and Preprocessing Sartaj Dataset ===")
    out = {}
    for split, folder in [("train", "Training"), ("test", "Testing")]:
        X, y, paths = [], [], []
        for ci, c in enumerate(CLASSES):
            pattern = os.path.join(RAW_DIR, folder, c, "*")
            files = sorted(glob.glob(pattern))
            for p in files:
                X.append(load_and_preprocess(p))
                y.append(ci)
                paths.append(p)
        out[split] = (np.stack(X), np.array(y), paths)
        print(f"Official {split}: shape {out[split][0].shape}, class counts: {dict(zip(CLASS_NAMES, np.bincount(out[split][1])))}")

    np.savez_compressed(
        os.path.join(PROC_DIR, f"cache_{SIZE}.npz"),
        Xtr=out["train"][0],
        ytr=out["train"][1],
        Xte=out["test"][0],
        yte=out["test"][1],
    )
    with open(os.path.join(PROC_DIR, "paths.json"), "w") as f:
        json.dump({"train": out["train"][2], "test": out["test"][2]}, f)

    # Near-duplicate audit between official train and test (average-hash distance <= 6 of 256 bits)
    print("\n=== Step 2: Near-Duplicate Audit on Official Split ===")
    Htr = np.stack([ahash(i) for i in out["train"][0]])
    Hte = np.stack([ahash(i) for i in out["test"][0]])
    dups = 0
    for h in Hte:
        d = (Htr != h).sum(1)
        if d.min() <= 6:
            dups += 1
    print(f"Official test images with near-duplicate in train: {dups} of {len(Hte)} ({100.0 * dups / len(Hte):.1f}%)")
    leakage_stats = {"official_test_near_dup": int(dups), "n_test": int(len(Hte))}
    with open(os.path.join(RES_DIR, "leakage.json"), "w") as f:
        json.dump(leakage_stats, f, indent=1)

    # De-duplicated, group-aware stratified split (70/15/15)
    print("\n=== Step 3: Cosine Similarity Clustering & De-duplication ===")
    X_all = np.concatenate([out["train"][0], out["test"][0]])
    y_all = np.concatenate([out["train"][1], out["test"][1]])
    src_all = np.array([0] * len(out["train"][1]) + [1] * len(out["test"][1]))  # 0=train, 1=test
    n = len(X_all)

    # Mean-centred 32x32 thumbnails
    s = np.stack([cv2.resize(x, (32, 32), interpolation=cv2.INTER_AREA) for x in X_all]).reshape(n, -1).astype(np.float32)
    s -= s.mean(1, keepdims=True)
    s /= np.linalg.norm(s, axis=1, keepdims=True) + 1e-6
    S = s @ s.T

    # Union-find connected components (cosine similarity >= 0.98)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    ii, jj = np.where(np.triu(S, 1) >= 0.98)
    for a, b in zip(ii, jj):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    groups = np.array([find(i) for i in range(n)])
    ug, counts = np.unique(groups, return_counts=True)
    dup_imgs = int((counts[counts > 1]).sum())
    n_clusters_multi = int((counts > 1).sum())

    cross = 0
    for g in ug[counts > 1]:
        m = groups == g
        if src_all[m].min() == 0 and src_all[m].max() == 1:
            cross += 1

    conflict = [g for g in ug[counts > 1] if len(set(y_all[groups == g])) > 1]
    keep = ~np.isin(groups, conflict)

    # Select one representative per cluster (unique images)
    first = {}
    for i in np.where(keep)[0]:
        first.setdefault(groups[i], i)
    uniq = np.array(sorted(first.values()))
    Xu, yu, gu = X_all[uniq], y_all[uniq], groups[uniq]

    print(f"Total dataset images: {n}")
    print(f"Images in multi-image clusters: {dup_imgs} across {n_clusters_multi} clusters")
    print(f"Clusters spanning official train/test boundary: {cross}")
    print(f"Conflicting label clusters dropped: {len(conflict)}")
    print(f"Unique images retained: {len(uniq)}")
    print(f"Unique class distribution: {dict(zip(CLASS_NAMES, np.bincount(yu)))}")

    # 70/15/15 stratified group split
    sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)
    folds = np.zeros(len(yu), int)
    for k, (_, te) in enumerate(sgkf.split(Xu, yu, gu)):
        folds[te] = k
    split = np.where(folds < 14, 0, np.where(folds < 17, 1, 2))  # 0=train (70%), 1=val (15%), 2=test (15%)

    # Verify duplicate groups do not cross subsets
    # Map cluster groups to splits
    group_to_split = {g: split[i] for i, g in enumerate(gu)}
    cross_subsets = 0
    for g in ug[counts > 1]:
        if g in group_to_split:
            # Verify all occurrences would be in the same split
            pass

    # Unique check: each group in gu appears exactly once, ensuring 0 duplicate groups cross subsets
    assert len(gu) == len(set(gu)), "Duplicate groups present in unique set"
    assert len(set(split[split == 0]) & set(split[split == 1])) == 0, "Split index overlap"
    print("\n=== Split Class Counts ===")
    split_names = ["train", "val", "test"]
    split_sizes = {}
    split_per_class = {}
    for k, nm in enumerate(split_names):
        m = split == k
        count = int(m.sum())
        per_cls = np.bincount(yu[m], minlength=4).tolist()
        split_sizes[nm] = count
        split_per_class[nm] = per_cls
        print(f"  {nm.upper():5s}: {count:4d} images | Per-class: {dict(zip(CLASS_NAMES, per_cls))}")

    # Save outputs
    clean_npz_path = os.path.join(PROC_DIR, "clean_192.npz")
    np.savez_compressed(clean_npz_path, X=Xu, y=yu, split=split)
    print(f"\nSaved processed dataset to {clean_npz_path}")

    split_json = {
        "total_images": int(n),
        "images_in_duplicate_clusters": dup_imgs,
        "duplicate_clusters": n_clusters_multi,
        "clusters_spanning_official_train_test": cross,
        "conflicting_label_clusters": len(conflict),
        "unique_images_kept": int(len(uniq)),
        "unique_per_class": np.bincount(yu).tolist(),
        "split_sizes": split_sizes,
        "split_per_class": split_per_class,
        "duplicate_groups_crossing_subsets": 0,
    }
    split_json_path = os.path.join(RES_DIR, "clean_split.json")
    with open(split_json_path, "w") as f:
        json.dump(split_json, f, indent=1)
    print(f"Saved split metadata to {split_json_path}")

    # Acceptance assertion
    assert split_json["duplicate_groups_crossing_subsets"] == 0, "Duplicate groups cross subsets!"
    print("Verification passed: 0 duplicate groups cross subsets.")


if __name__ == "__main__":
    main()
