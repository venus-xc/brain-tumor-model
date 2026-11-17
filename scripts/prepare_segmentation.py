"""Segmentation dataset preparation pipeline for the Figshare dataset.
Reads 3,064 .mat v7.3 files (Cheng et al., doi:10.6084/m9.figshare.1512427.v5).
Normalises each image to [0, 255] uint8, resizes image to 256x256 (INTER_AREA) and mask to 256x256 (INTER_NEAREST).
Performs patient-level 70/15/15 split using GroupShuffleSplit on PID (seed 42).
Saves data/processed/seg_256.npz holding X, M, label, pid, split.
"""
import json
import os
import sys
import h5py
import numpy as np
import cv2
from sklearn.model_selection import GroupShuffleSplit

RAW_DIR = sys.argv[1] if len(sys.argv) > 1 else "data/raw/figshare"
PROC_DIR = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
RES_DIR = sys.argv[3] if len(sys.argv) > 3 else "results"

os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(RES_DIR, exist_ok=True)

# Figshare label mapping: 1 = meningioma, 2 = glioma, 3 = pituitary
LABEL_MAP = {1: "Meningioma", 2: "Glioma", 3: "Pituitary"}


def main():
    print("=== Step 1: Loading Figshare .mat files ===")
    X_list = []
    M_list = []
    labels = []
    pids = []

    # Files are 1.mat through 3064.mat
    for idx in range(1, 3065):
        mat_path = os.path.join(RAW_DIR, f"{idx}.mat")
        if not os.path.exists(mat_path):
            raise FileNotFoundError(f"Missing expected file: {mat_path}")

        with h5py.File(mat_path, "r") as f:
            cj = f["cjdata"]
            img = np.array(cj["image"], dtype=np.float32)
            mask = (np.array(cj["tumorMask"]) > 0).astype(np.uint8)
            lbl = int(cj["label"][0, 0])
            pid_chars = [chr(c[0]) for c in cj["PID"]]
            pid = "".join(pid_chars).strip()

        # Normalise to [0, 255] uint8
        img_min, img_max = img.min(), img.max()
        if img_max > img_min:
            img_u8 = ((img - img_min) / (img_max - img_min) * 255.0).astype(np.uint8)
        else:
            img_u8 = np.zeros_like(img, dtype=np.uint8)

        # Resize image with INTER_AREA, mask with INTER_NEAREST
        img_res = cv2.resize(img_u8, (256, 256), interpolation=cv2.INTER_AREA)
        mask_res = cv2.resize(mask, (256, 256), interpolation=cv2.INTER_NEAREST)

        X_list.append(img_res)
        M_list.append(mask_res)
        labels.append(lbl)
        pids.append(pid)

        if idx % 500 == 0 or idx == 3064:
            print(f"Processed {idx}/3064 files...")

    X = np.stack(X_list)
    M = np.stack(M_list)
    labels = np.array(labels, dtype=np.int64)
    pids = np.array(pids)

    unique_pids = np.unique(pids)
    print(f"\nTotal segmentation slices: {len(X)}")
    print(f"Total unique patients (PIDs): {len(unique_pids)}")
    print("Class distribution (total):")
    for lbl_id, name in LABEL_MAP.items():
        print(f"  {name:12s} (label {lbl_id}): {int((labels == lbl_id).sum())} slices")

    # Patient-level 70/15/15 split using GroupShuffleSplit on PID (seed 42)
    print("\n=== Step 2: Patient-Level Group Split (70 / 15 / 15) ===")
    gss1 = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=42)
    train_idx, temp_idx = next(gss1.split(X, labels, groups=pids))

    gss2 = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=42)
    val_sub, test_sub = next(gss2.split(X[temp_idx], labels[temp_idx], groups=pids[temp_idx]))
    val_idx = temp_idx[val_sub]
    test_idx = temp_idx[test_sub]

    split = np.zeros(len(X), dtype=np.int64)
    split[train_idx] = 0  # train
    split[val_idx] = 1    # val
    split[test_idx] = 2   # test

    train_pids = set(pids[train_idx])
    val_pids = set(pids[val_idx])
    test_pids = set(pids[test_idx])

    # Acceptance assertion: 0 PIDs shared across subsets
    assert len(train_pids & val_pids) == 0, f"Shared PIDs between train & val: {train_pids & val_pids}"
    assert len(train_pids & test_pids) == 0, f"Shared PIDs between train & test: {train_pids & test_pids}"
    assert len(val_pids & test_pids) == 0, f"Shared PIDs between val & test: {val_pids & test_pids}"

    split_names = ["train", "val", "test"]
    split_info = {}
    for k, nm in enumerate(split_names):
        m = split == k
        subset_pids = set(pids[m])
        per_cls = {LABEL_MAP[lbl_id]: int((labels[m] == lbl_id).sum()) for lbl_id in [1, 2, 3]}
        split_info[nm] = {
            "n_images": int(m.sum()),
            "n_patients": len(subset_pids),
            "per_class": per_cls,
        }
        print(f"  {nm.upper():5s}: {m.sum():4d} images | {len(subset_pids):3d} patients | Per-class: {per_cls}")

    print("\nVerification passed: 0 PIDs shared across subsets.")

    # Save data/processed/seg_256.npz
    out_path = os.path.join(PROC_DIR, "seg_256.npz")
    np.savez_compressed(
        out_path,
        X=X,
        M=M,
        label=labels,
        pid=pids,
        split=split,
    )
    print(f"Saved processed segmentation dataset to {out_path}")

    # Save summary metadata
    meta_path = os.path.join(RES_DIR, "segmentation_split.json")
    with open(meta_path, "w") as f:
        json.dump({
            "total_images": len(X),
            "total_patients": len(unique_pids),
            "split_info": split_info,
            "shared_pids": 0,
        }, f, indent=1)
    print(f"Saved segmentation split metadata to {meta_path}")


if __name__ == "__main__":
    main()
