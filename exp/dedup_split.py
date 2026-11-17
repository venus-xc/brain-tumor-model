"""Leakage audit + de-duplicated, group-aware stratified split (70/15/15).
Near-duplicates: cosine similarity >= 0.98 between mean-centred 32x32 thumbnails.
Duplicate clusters are kept inside a single split so no image leaks across splits.
Conflicting-label clusters (same image, different labels) are dropped.
"""
import numpy as np, cv2, json, sys
from sklearn.model_selection import StratifiedGroupKFold

d = np.load("data/cache_192.npz")
X = np.concatenate([d["Xtr"], d["Xte"]]); y = np.concatenate([d["ytr"], d["yte"]])
src = np.array([0] * len(d["ytr"]) + [1] * len(d["yte"]))  # 0 = official train, 1 = official test
n = len(X)
s = np.stack([cv2.resize(x, (32, 32), interpolation=cv2.INTER_AREA) for x in X]).reshape(n, -1).astype(np.float32)
s -= s.mean(1, keepdims=True); s /= np.linalg.norm(s, axis=1, keepdims=True) + 1e-6
S = s @ s.T
parent = list(range(n))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
ii, jj = np.where(np.triu(S, 1) >= 0.98)
for a, b in zip(ii, jj):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb
groups = np.array([find(i) for i in range(n)])
ug, counts = np.unique(groups, return_counts=True)
dup_imgs = int((counts[counts > 1]).sum()); n_clusters_multi = int((counts > 1).sum())
cross = 0
for g in ug[counts > 1]:
    m = groups == g
    if src[m].min() == 0 and src[m].max() == 1: cross += 1
conflict = [g for g in ug[counts > 1] if len(set(y[groups == g])) > 1]
keep = ~np.isin(groups, conflict)
# one representative per cluster (unique images) to avoid over-weighting duplicates
first = {}
for i in np.where(keep)[0]:
    first.setdefault(groups[i], i)
uniq = np.array(sorted(first.values()))
Xu, yu, gu = X[uniq], y[uniq], groups[uniq]
print("total", n, "images in dup clusters", dup_imgs, "clusters", n_clusters_multi,
      "cross-split clusters", cross, "conflicting clusters", len(conflict), "unique kept", len(uniq))
print("unique per class", np.bincount(yu))
# 70/15/15 stratified split on unique images
sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)
folds = np.zeros(len(yu), int)
for k, (_, te) in enumerate(sgkf.split(Xu, yu, gu)): folds[te] = k
split = np.where(folds < 14, 0, np.where(folds < 17, 1, 2))  # 0 train, 1 val, 2 test
for k, nm in enumerate(["train", "val", "test"]):
    print(nm, (split == k).sum(), np.bincount(yu[split == k], minlength=4))
np.savez_compressed("data/clean_192.npz", X=Xu, y=yu, split=split)
json.dump({"total_images": int(n), "images_in_duplicate_clusters": dup_imgs,
           "duplicate_clusters": n_clusters_multi, "clusters_spanning_official_train_test": cross,
           "conflicting_label_clusters": len(conflict), "unique_images_kept": int(len(uniq)),
           "unique_per_class": np.bincount(yu).tolist(),
           "split_sizes": {nm: int((split == k).sum()) for k, nm in enumerate(["train", "val", "test"])},
           "split_per_class": {nm: np.bincount(yu[split == k], minlength=4).tolist() for k, nm in enumerate(["train", "val", "test"])}},
          open("data/clean_split.json", "w"), indent=1)
