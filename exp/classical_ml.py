"""Classical ML baselines: HOG features (+PCA) -> SVM / Random Forest / KNN / Logistic Regression."""
import numpy as np, cv2, json, time
from skimage.feature import hog
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, PredefinedSplit
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score

d = np.load("data/clean_192.npz"); X, y, sp = d["X"], d["y"], d["split"]
def feats(img):
    g = cv2.resize(img, (128, 128), interpolation=cv2.INTER_AREA)
    return hog(g, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), block_norm="L2-Hys")
t = time.time(); F = np.stack([feats(i) for i in X]); print("HOG dim", F.shape, f"{time.time()-t:.1f}s")
trv = sp < 2  # train+val used for grid search with predefined split
ps = PredefinedSplit(np.where(sp[trv] == 1, 0, -1))
models = {
    "SVM (RBF)": (make_pipeline(StandardScaler(), PCA(150, random_state=42), SVC(probability=True, class_weight="balanced", random_state=42)),
                  {"svc__C": [1, 10, 30], "svc__gamma": ["scale", 0.003]}),
    "Random Forest": (RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=1),
                      {"n_estimators": [300], "max_depth": [None, 20]}),
    "k-NN": (make_pipeline(StandardScaler(), PCA(150, random_state=42), KNeighborsClassifier()),
             {"kneighborsclassifier__n_neighbors": [3, 5, 9]}),
    "Logistic Regression": (make_pipeline(StandardScaler(), PCA(150, random_state=42), LogisticRegression(max_iter=3000, class_weight="balanced")),
                            {"logisticregression__C": [0.01, 0.1, 1]}),
}
out = {"hog_dim": int(F.shape[1])}
for name, (est, grid) in models.items():
    t = time.time()
    gs = GridSearchCV(est, grid, cv=ps, scoring="accuracy", refit=False, n_jobs=1).fit(F[trv], y[trv])
    best = est.set_params(**gs.best_params_).fit(F[sp == 0], y[sp == 0])
    te = sp == 2; pt = best.predict_proba(F[te]); pred = pt.argmax(1)
    p, r, f, _ = precision_recall_fscore_support(y[te], pred, labels=[0, 1, 2, 3], zero_division=0)
    out[name] = {"best_params": {k: str(v) for k, v in gs.best_params_.items()}, "accuracy": accuracy_score(y[te], pred),
                 "macro_f1": f1_score(y[te], pred, average="macro"), "macro_precision": float(p.mean()), "macro_recall": float(r.mean()),
                 "roc_auc_ovr_macro": roc_auc_score(y[te], pt, multi_class="ovr", average="macro"),
                 "per_class_recall": r.tolist(), "confusion": confusion_matrix(y[te], pred).tolist(), "fit_time_s": time.time() - t}
    print(name, gs.best_params_, round(out[name]["accuracy"], 4), round(out[name]["macro_f1"], 4), flush=True)
json.dump(out, open("results/classical.json", "w"), indent=1)
