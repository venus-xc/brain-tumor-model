"""Result figures + consolidated metrics.json from results/*.json"""
import json, os, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "savefig.dpi": 220, "savefig.bbox": "tight"})
CLS = ["No tumor", "Glioma", "Meningioma", "Pituitary"]
BLUE, PINK, YEL, GRN, ORG = "#5B7FC8", "#EE8F8B", "#F2C64B", "#8DBA7A", "#F29A4A"
R = {}
for t in ["effb0_clean", "secnn_clean", "cnn_clean", "effb0_official"]:
    if os.path.exists(f"results/{t}.json"): R[t] = json.load(open(f"results/{t}.json"))
C = json.load(open("results/classical.json"))
NAMES = {"cnn_clean": "Custom CNN", "secnn_clean": "SE-CNN", "effb0_clean": "EfficientNet-B0 (TL)"}

# training curves
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
for t, col in zip(["cnn_clean", "secnn_clean", "effb0_clean"], [ORG, YEL, BLUE]):
    if t not in R: continue
    h = R[t]["history"]; e = np.arange(1, len(h["train_loss"]) + 1)
    axs[0].plot(e, h["train_loss"], color=col, ls="--", lw=1.4); axs[0].plot(e, h["val_loss"], color=col, lw=2, label=NAMES[t])
    axs[1].plot(e, h["train_acc"], color=col, ls="--", lw=1.4); axs[1].plot(e, h["val_acc"], color=col, lw=2, label=NAMES[t])
axs[0].set_title("Loss (dashed = train, solid = validation)"); axs[1].set_title("Accuracy (dashed = train, solid = validation)")
for a in axs: a.set_xlabel("Epoch"); a.grid(alpha=0.25); a.spines[["top", "right"]].set_visible(False); a.legend(frameon=False)
fig.savefig("figs/fig_curves.png"); plt.close(fig)

# confusion matrices (best deep + best classical)
def cm_plot(ax, cm, title):
    cm = np.array(cm); n = cm / cm.sum(1, keepdims=True)
    ax.imshow(n, cmap="Blues", vmin=0, vmax=1)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{cm[i, j]}\n{100 * n[i, j]:.0f}%", ha="center", va="center", fontsize=9, color="white" if n[i, j] > 0.6 else "#1F2937")
    ax.set_xticks(range(4)); ax.set_yticks(range(4)); ax.set_xticklabels(CLS, rotation=20); ax.set_yticklabels(CLS)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(title, fontsize=10)
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6))
cm_plot(axs[0], C["SVM (RBF)"]["confusion"], "HOG + SVM (best classical)")
cm_plot(axs[1], R["effb0_clean"]["confusion"], "EfficientNet-B0 (best overall)")
fig.tight_layout(); fig.savefig("figs/fig_confusion.png"); plt.close(fig)

# ROC (EfficientNet)
p = np.load("results/effb0_clean_probs.npy"); yt = np.load("results/effb0_clean_ytrue.npy")
fig, ax = plt.subplots(figsize=(5.2, 4.6))
for c, col in zip(range(4), [GRN, PINK, BLUE, YEL]):
    fpr, tpr, _ = roc_curve(yt == c, p[:, c]); ax.plot(fpr, tpr, color=col, lw=2, label=f"{CLS[c]} (AUC = {auc(fpr, tpr):.3f})")
ax.plot([0, 1], [0, 1], "--", color="#9CA3AF"); ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
ax.legend(frameon=False, loc="lower right", fontsize=9); ax.set_title("One-vs-rest ROC, EfficientNet-B0"); ax.spines[["top", "right"]].set_visible(False)
fig.savefig("figs/fig_roc.png"); plt.close(fig)

# model comparison
rows = [(k, C[k]["accuracy"], C[k]["macro_f1"]) for k in ["Logistic Regression", "Random Forest", "k-NN", "SVM (RBF)"]]
rows += [(NAMES[t], R[t]["accuracy"], R[t]["macro_f1"]) for t in ["cnn_clean", "secnn_clean", "effb0_clean"] if t in R]
fig, ax = plt.subplots(figsize=(10, 3.8)); x = np.arange(len(rows))
b1 = ax.bar(x - 0.2, [100 * r[1] for r in rows], 0.38, color=BLUE, label="Accuracy"); b2 = ax.bar(x + 0.2, [100 * r[2] for r in rows], 0.38, color=PINK, label="Macro F1")
for b in list(b1) + list(b2): ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.8, f"{b.get_height():.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([r[0].replace(" (TL)", "\n(transfer)").replace("Logistic Regression", "Logistic\nRegression").replace("Random Forest", "Random\nForest") for r in rows], fontsize=9)
ax.axvline(3.5, color="#9CA3AF", ls=":"); ax.text(1.5, 103, "HOG + classical ML", ha="center", color="#6B7280"); ax.text(5, 103, "Deep learning (CNN)", ha="center", color="#6B7280")
ax.set_ylim(50, 108); ax.set_ylabel("%  (held-out test, n = 420)"); ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.16)); ax.spines[["top", "right"]].set_visible(False)
fig.savefig("figs/fig_comparison.png"); plt.close(fig)

# leakage effect
if "effb0_official" in R:
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    vals = [100 * R["effb0_official"]["accuracy"], 100 * R["effb0_clean"]["accuracy"]]
    bs = ax.bar(["Official split\n(test overlaps train)", "De-duplicated split\n(leakage-free)"], vals, color=[PINK, GRN], width=0.55)
    for b in bs: ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.8, f"{b.get_height():.1f}%", ha="center", weight="bold")
    ax.set_ylim(50, 105); ax.set_ylabel("Test accuracy (%)"); ax.set_title("EfficientNet-B0: same model, different split", fontsize=10); ax.spines[["top", "right"]].set_visible(False)
    fig.savefig("figs/fig_split_effect.png"); plt.close(fig)

M = {"classical": C, "deep": {k: {kk: v for kk, v in R[k].items() if kk != "history"} for k in R},
     "split": json.load(open("data/clean_split.json")), "leakage": json.load(open("results/leakage.json"))}
json.dump(M, open("results/metrics.json", "w"), indent=1)
print("result figs done")
