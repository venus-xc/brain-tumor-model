"""Classical ML training & evaluation script.
Ports reference_code/exp/classical_ml.py.
Extracts HOG features, performs grid search on train+val, fits best estimator on train,
evaluates on held-out test split, saves weights to weights/ and metrics to results/classical.json.
"""
import argparse
import json
import os
import sys
import time
import cv2
import joblib
import numpy as np
from skimage.feature import hog
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, PredefinedSplit
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "clean_192.npz")
WEIGHTS_DIR = os.path.join(PROJECT_ROOT, "weights")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

os.makedirs(WEIGHTS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)


def extract_features(img: np.ndarray) -> np.ndarray:
    g = cv2.resize(img, (128, 128), interpolation=cv2.INTER_AREA)
    return hog(
        g,
        orientations=9,
        pixels_per_cell=(16, 16),
        cells_per_block=(2, 2),
        block_norm="L2-Hys",
    )


def main():
    print(f"Loading dataset from {DATA_PATH}...")
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing {DATA_PATH}. Run scripts/prepare_classification.py first.")

    d = np.load(DATA_PATH)
    X, y, sp = d["X"], d["y"], d["split"]

    t0 = time.time()
    print("Computing HOG features for all images...")
    F = np.stack([extract_features(i) for i in X])
    print(f"Extracted HOG features with dimension {F.shape} in {time.time() - t0:.1f}s")

    trv = sp < 2  # Train (0) + Val (1)
    ps = PredefinedSplit(np.where(sp[trv] == 1, 0, -1))

    models = {
        "SVM (RBF)": (
            make_pipeline(
                StandardScaler(),
                PCA(150, random_state=42),
                SVC(probability=True, class_weight="balanced", random_state=42),
            ),
            {"svc__C": [1, 10, 30], "svc__gamma": ["scale", 0.003]},
            "hog_svm.joblib",
        ),
        "Random Forest": (
            RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=1),
            {"n_estimators": [300], "max_depth": [None, 20]},
            "hog_rf.joblib",
        ),
        "k-NN": (
            make_pipeline(
                StandardScaler(),
                PCA(150, random_state=42),
                KNeighborsClassifier(),
            ),
            {"kneighborsclassifier__n_neighbors": [3, 5, 9]},
            "hog_knn.joblib",
        ),
        "Logistic Regression": (
            make_pipeline(
                StandardScaler(),
                PCA(150, random_state=42),
                LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
            ),
            {"logisticregression__C": [0.01, 0.1, 1]},
            "hog_lr.joblib",
        ),
    }

    out = {"hog_dim": int(F.shape[1])}

    for name, (est, grid, weight_file) in models.items():
        t = time.time()
        print(f"\n--- Training {name} ---")
        gs = GridSearchCV(est, grid, cv=ps, scoring="accuracy", refit=False, n_jobs=1).fit(F[trv], y[trv])
        print(f"Best hyperparameters: {gs.best_params_}")

        best = est.set_params(**gs.best_params_).fit(F[sp == 0], y[sp == 0])

        # Save pipeline to weights/
        weight_path = os.path.join(WEIGHTS_DIR, weight_file)
        joblib.dump(best, weight_path)
        print(f"Saved pipeline weights to {weight_path}")

        # Evaluate on held-out test split (split == 2)
        te = sp == 2
        pt = best.predict_proba(F[te])
        pred = pt.argmax(1)
        p, r, f, _ = precision_recall_fscore_support(y[te], pred, labels=[0, 1, 2, 3], zero_division=0)

        acc = float(accuracy_score(y[te], pred))
        mf1 = float(f1_score(y[te], pred, average="macro"))
        mprec = float(p.mean())
        mrec = float(r.mean())
        auc_score = float(roc_auc_score(y[te], pt, multi_class="ovr", average="macro"))

        out[name] = {
            "best_params": {k: str(v) for k, v in gs.best_params_.items()},
            "accuracy": acc,
            "macro_f1": mf1,
            "macro_precision": mprec,
            "macro_recall": mrec,
            "roc_auc_ovr_macro": auc_score,
            "per_class_recall": r.tolist(),
            "confusion": confusion_matrix(y[te], pred, labels=[0, 1, 2, 3]).tolist(),
            "fit_time_s": float(time.time() - t),
        }
        print(f"{name} Result -> Accuracy: {acc:.4f}, Macro-F1: {mf1:.4f}, ROC-AUC: {auc_score:.4f} ({time.time() - t:.1f}s)")

    out_file = os.path.join(RESULTS_DIR, "classical.json")
    with open(out_file, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nSaved classical ML evaluation results to {out_file}")


if __name__ == "__main__":
    main()
