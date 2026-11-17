"""Static diagrams + data figures (no model results needed)."""
import numpy as np, cv2, json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image
from skimage.feature import hog

OUT = "figs"; os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "savefig.dpi": 220, "savefig.bbox": "tight"})
BLUE, PINK, YEL, GRN, ORG, INK, GREY = "#5B7FC8", "#EE8F8B", "#F2C64B", "#8DBA7A", "#F29A4A", "#1F2937", "#6B7280"
LIGHT = {BLUE: "#E3EAF8", PINK: "#FCE5E3", YEL: "#FDF3D3", GRN: "#E6F1E0", ORG: "#FDE9D7", GREY: "#F1F2F4"}
CLS = ["No tumor", "Glioma", "Meningioma", "Pituitary"]

def box(ax, x, y, w, h, title, sub="", col=BLUE, fs=10, sfs=8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=LIGHT.get(col, "#fff"), ec=col, lw=1.6))
    if sub:
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center", fontsize=fs, weight="bold", color=INK)
        ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center", fontsize=sfs, color=GREY, linespacing=1.25)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, weight="bold", color=INK, linespacing=1.25)

def arrow(ax, p, q, col=INK, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=12, color=col, lw=1.3, connectionstyle=f"arc3,rad={rad}"))

def canvas(w, h, W, H):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off"); return fig, ax

# ---------- Fig: system architecture ----------
fig, ax = canvas(12, 5.6, 24, 11.2)
F1, F2 = 9, 7.5
box(ax, 0.1, 4.8, 3.0, 1.6, "MRI slice", "T1 / T1-CE\nJPG / PNG / DICOM", GREY, F1, F2)
box(ax, 3.8, 4.8, 3.0, 1.6, "Preprocessing", "crop - CLAHE\nresize - normalise", BLUE, F1, F2)
box(ax, 7.7, 8.4, 4.4, 1.6, "Classical ML baselines", "HOG + SVM / RF\nk-NN / Logistic Reg.", YEL, F1, F2)
box(ax, 7.7, 6.2, 4.4, 1.6, "Custom CNN / SE-CNN", "trained from scratch\n4 conv blocks", ORG, F1, F2)
box(ax, 7.7, 4.0, 4.4, 1.6, "EfficientNet-B0", "ImageNet transfer\nlearning (fine-tuned)", PINK, F1, F2)
box(ax, 7.7, 1.2, 4.4, 1.6, "U-Net / Attention U-Net", "tumour segmentation\n(Figshare masks)", GRN, F1, F2)
box(ax, 13.0, 6.2, 4.4, 1.6, "4-class prediction", "softmax probabilities", PINK, F1, F2)
box(ax, 13.0, 4.0, 4.4, 1.6, "Explainability", "Grad-CAM / Grad-CAM++", PINK, F1, F2)
box(ax, 13.0, 1.2, 4.4, 1.6, "Tumour measurements", "area (cm²), longest\ndiameter (mm)", GRN, F1, F2)
box(ax, 18.3, 1.2, 5.4, 1.6, "Follow-up comparison", "RANO-inspired change\n(2D product of diameters)", GRN, F1, F2)
box(ax, 18.3, 5.0, 5.4, 2.2, "FastAPI web app", "upload - view overlays\nPDF report download", BLUE, F1, F2)
for y in [9.2, 7.0, 4.8, 2.0]:
    arrow(ax, (6.8, 5.6), (7.7, y))
arrow(ax, (12.1, 9.2), (13.0, 7.3), rad=-0.15); arrow(ax, (12.1, 7.0), (13.0, 7.0)); arrow(ax, (12.1, 4.8), (13.0, 6.6), rad=0.1)
arrow(ax, (12.1, 4.8), (13.0, 4.8)); arrow(ax, (12.1, 2.0), (13.0, 2.0)); arrow(ax, (17.4, 2.0), (18.3, 2.0))
arrow(ax, (17.4, 7.0), (18.3, 6.4)); arrow(ax, (17.4, 4.8), (18.3, 5.6)); arrow(ax, (21.0, 2.8), (21.0, 5.0))
arrow(ax, (3.1, 5.6), (3.8, 5.6))
ax.text(9.9, 10.6, "Models compared on the same leakage-free split", ha="center", fontsize=9, color=GREY, style="italic")
fig.savefig(f"{OUT}/fig_architecture.png"); plt.close(fig)

# ---------- Fig: methodology workflow ----------
steps = [("1", "Collect", "public MRI\ndataset", BLUE), ("2", "Audit", "duplicates &\nlabel conflicts", PINK), ("3", "Split", "70 / 15 / 15\nstratified", YEL),
         ("4", "Preprocess", "crop, CLAHE,\nresize", GRN), ("5", "Train", "ML + CNN +\ntransfer learning", ORG), ("6", "Evaluate", "acc, F1, AUC,\nconfusion", BLUE),
         ("7", "Explain", "Grad-CAM /\nGrad-CAM++", PINK), ("8", "Deploy", "FastAPI app +\nPDF report", GRN)]
fig, ax = canvas(12, 2.4, 24, 4.8)
for i, (n, t, s, c) in enumerate(steps):
    x = 0.2 + i * 3.0
    box(ax, x, 0.4, 2.5, 3.0, t, s, c, fs=10, sfs=8)
    ax.add_patch(plt.Circle((x + 1.25, 3.95), 0.42, color=c)); ax.text(x + 1.25, 3.95, n, ha="center", va="center", color="white", weight="bold")
    if i < len(steps) - 1: arrow(ax, (x + 2.5, 1.9), (x + 3.0, 1.9))
fig.savefig(f"{OUT}/fig_workflow.png"); plt.close(fig)

# ---------- data-based figures ----------
d = np.load("data/cache_192.npz"); paths = json.load(open("data/paths.json"))
clean = np.load("data/clean_192.npz"); split = json.load(open("data/clean_split.json"))
rng = np.random.RandomState(3)

# preprocessing stages on a real image
from importlib.machinery import SourceFileLoader
pidx = paths["train"].index(sorted([p for p in paths["train"] if "meningioma" in p])[40])
raw = np.array(Image.open(paths["train"][pidx]).convert("L"))
blur = cv2.GaussianBlur(raw, (5, 5), 0); _, th = cv2.threshold(blur, 45, 255, cv2.THRESH_BINARY)
th = cv2.dilate(cv2.erode(th, None, iterations=2), None, iterations=2)
cnts, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); c = max(cnts, key=cv2.contourArea)
x, y, w, h = cv2.boundingRect(c); crop = raw[y:y + h, x:x + w]
cl = cv2.createCLAHE(2.0, (8, 8)).apply(crop); rs = cv2.resize(cl, (160, 160), interpolation=cv2.INTER_AREA)
over = cv2.cvtColor(raw, cv2.COLOR_GRAY2RGB); cv2.drawContours(over, [c], -1, (91, 127, 200), 3); cv2.rectangle(over, (x, y), (x + w, y + h), (238, 143, 139), 3)
fig, axs = plt.subplots(1, 5, figsize=(12, 2.9))
for a_, im, t in zip(axs, [raw, over, crop, cl, rs], ["(a) Original slice", "(b) Brain contour + box", "(c) Cropped brain", "(d) CLAHE (clip 2.0, 8x8)", "(e) Resized 160x160"]):
    a_.imshow(im, cmap="gray"); a_.set_title(t, fontsize=10); a_.axis("off")
fig.savefig(f"{OUT}/fig_preprocessing.png"); plt.close(fig)

# sample grid
fig, axs = plt.subplots(4, 5, figsize=(9, 7.4))
for ci in range(4):
    idx = rng.choice(np.where(clean["y"] == ci)[0], 5, replace=False)
    for j, k in enumerate(idx):
        axs[ci, j].imshow(clean["X"][k], cmap="gray"); axs[ci, j].set_xticks([]); axs[ci, j].set_yticks([])
        for s in axs[ci, j].spines.values(): s.set_visible(False)
    axs[ci, 0].set_ylabel(CLS[ci], fontsize=11, weight="bold")
fig.tight_layout(); fig.savefig(f"{OUT}/fig_samples.png"); plt.close(fig)

# class distribution: official vs de-duplicated
orig = np.bincount(np.concatenate([d["ytr"], d["yte"]]), minlength=4); uniq = np.array(split["unique_per_class"])
fig, ax = plt.subplots(figsize=(7, 3.4)); xx = np.arange(4)
b1 = ax.bar(xx - 0.2, orig, 0.38, color=BLUE, label="Original (3,264 images)"); b2 = ax.bar(xx + 0.2, uniq, 0.38, color=PINK, label=f"After de-duplication ({sum(uniq):,})")
for b in list(b1) + list(b2): ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 10, int(b.get_height()), ha="center", fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels(CLS); ax.set_ylabel("Images"); ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.13)); ax.spines[["top", "right"]].set_visible(False)
ax.set_ylim(0, max(orig) * 1.15); fig.savefig(f"{OUT}/fig_class_dist.png"); plt.close(fig)

# leakage example: a test image and its training near-duplicate
def thumbs(X):
    s = np.stack([cv2.resize(x, (32, 32), interpolation=cv2.INTER_AREA) for x in X]).reshape(len(X), -1).astype(np.float32)
    s -= s.mean(1, keepdims=True); return s / (np.linalg.norm(s, axis=1, keepdims=True) + 1e-6)
A, B = thumbs(d["Xtr"]), thumbs(d["Xte"]); C = B @ A.T; m = C.max(1); j = C.argmax(1)
n_leak = int((m >= 0.98).sum())
ex = [i for i in np.argsort(-m) if d["yte"][i] in (1, 2)][5:8]
fig = plt.figure(figsize=(11, 3.3)); gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 0.15, 2.2])
a1 = fig.add_subplot(gs[0]); a1.imshow(d["Xte"][ex[0]], cmap="gray"); a1.set_title("Official TEST image", fontsize=10); a1.axis("off")
a2 = fig.add_subplot(gs[1]); a2.imshow(d["Xtr"][j[ex[0]]], cmap="gray"); a2.set_title(f"Official TRAIN image\n(similarity {m[ex[0]]:.3f})", fontsize=10); a2.axis("off")
a3 = fig.add_subplot(gs[3]); vals = [n_leak, len(m) - n_leak]
a3.barh([0], [vals[0]], color=PINK, label=f"near-duplicate of a training image ({vals[0]})"); a3.barh([0], [vals[1]], left=[vals[0]], color=GRN, label=f"unique ({vals[1]})")
a3.set_yticks([]); a3.set_xlim(0, len(m)); a3.set_xlabel("Official test images (n = 394)"); a3.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.45), fontsize=9)
a3.text(vals[0] / 2, 0, f"{100 * vals[0] / len(m):.0f}%", ha="center", va="center", color="white", weight="bold", fontsize=13)
a3.spines[["top", "right", "left"]].set_visible(False); a3.set_ylim(-0.6, 0.6)
fig.savefig(f"{OUT}/fig_leakage.png"); plt.close(fig)
json.dump({"official_test_near_dup": n_leak, "n_test": int(len(m))}, open("results/leakage.json", "w"))

# HOG visualisation
img = cv2.resize(clean["X"][np.where(clean["y"] == 1)[0][7]], (128, 128))
_, hv = hog(img, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), visualize=True)
fig, axs = plt.subplots(1, 2, figsize=(6, 3)); axs[0].imshow(img, cmap="gray"); axs[0].set_title("Input (128x128)"); axs[1].imshow(hv, cmap="magma"); axs[1].set_title("HOG cells (16x16, 9 bins)")
for a_ in axs: a_.axis("off")
fig.savefig(f"{OUT}/fig_hog.png"); plt.close(fig)

# ---------- CNN architecture ----------
fig, ax = canvas(12, 3.6, 24, 7.2)
layers = [("Input", "1x128x128", GREY, 1.6), ("Block 1", "2xConv3x3 (32)\nBN+ReLU, SE\nMaxPool", BLUE, 2.4), ("Block 2", "2xConv3x3 (64)\nBN+ReLU, SE\nMaxPool", BLUE, 2.4),
          ("Block 3", "2xConv3x3 (128)\nBN+ReLU, SE\nMaxPool", BLUE, 2.4), ("Block 4", "2xConv3x3 (256)\nBN+ReLU, SE\nMaxPool", BLUE, 2.4), ("GAP", "256", YEL, 1.6),
          ("FC 128", "ReLU\nDropout 0.4", ORG, 1.9), ("FC 4", "Softmax", PINK, 1.6)]
x = 0.3; hs = [3.0, 5.6, 5.0, 4.4, 3.8, 2.4, 2.4, 2.0]
for (t, s, c, w), h in zip(layers, hs):
    yb = 3.4 - h / 2
    box(ax, x, yb, w, h, t, s, c, fs=10, sfs=7.5)
    nx = x + w + 0.55
    if t != "FC 4": arrow(ax, (x + w, 3.4), (nx, 3.4))
    x = nx
ax.text(12, 6.85, "Feature maps: 128 -> 64 -> 32 -> 16 -> 8 (spatial)   |   SE block optional (SE-CNN vs plain CNN ablation)", ha="center", fontsize=9, color=GREY, style="italic")
fig.savefig(f"{OUT}/fig_cnn.png"); plt.close(fig)

# ---------- SE block ----------
fig, ax = canvas(11, 2.9, 22, 5.8)
seq = [("X", "C x H x W", GREY), ("Squeeze", "global avg pool\n"+r"$z\in\mathbb{R}^C$", BLUE), ("FC + ReLU", "C/r units (r = 8)", YEL), ("FC + Sigmoid", "C units\n"+r"$s\in(0,1)^C$", ORG), ("Scale", r"$\tilde{X}_c = s_c\,X_c$", PINK)]
for i, (t, s, c) in enumerate(seq):
    x = 0.3 + i * 4.4; box(ax, x, 1.0, 3.4, 2.6, t, s, c)
    if i < 4: arrow(ax, (x + 3.4, 2.3), (x + 4.4, 2.3))
arrow(ax, (2.0, 3.6), (19.6, 3.6), col=GREY, rad=-0.12); ax.text(11, 5.05, "identity path: original feature map is re-weighted channel by channel", ha="center", fontsize=8.5, color=GREY)
fig.savefig(f"{OUT}/fig_se.png"); plt.close(fig)

# ---------- EfficientNet transfer learning ----------
fig, ax = canvas(12, 3.0, 24, 6.0)
st = [("Input", "3x160x160\n(grey -> 3 ch)", GREY, 2.2), ("Stem", "Conv3x3 s2\n32 ch", BLUE, 2.0), ("MBConv1", "16 ch", BLUE, 1.8), ("MBConv6 x2", "24 ch", BLUE, 2.0),
      ("MBConv6 x2", "40 ch", BLUE, 2.0), ("MBConv6 x3", "80 / 112 ch", BLUE, 2.2), ("MBConv6 x5", "192 / 320 ch", BLUE, 2.2), ("Conv1x1", "1280 ch\nGrad-CAM layer", PINK, 2.2),
      ("GAP + FC", "4 classes\n(new head)", ORG, 2.2)]
x = 0.2
for i, (t, s, c, w) in enumerate(st):
    box(ax, x, 1.4, w, 2.6, t, s, c, fs=8, sfs=7)
    if i < len(st) - 1: arrow(ax, (x + w, 2.7), (x + w + 0.45, 2.7))
    x += w + 0.45
ax.text(9.5, 4.9, "ImageNet-pretrained backbone (weights loaded, then fine-tuned end-to-end)", ha="center", fontsize=9, color=BLUE, weight="bold")
ax.text(21.7, 4.9, "trained from scratch", ha="center", fontsize=9, color=ORG, weight="bold")
ax.text(12, 0.5, "MBConv = inverted residual block: 1x1 expand -> depthwise 3x3/5x5 -> squeeze-and-excitation -> 1x1 project (+ skip)", ha="center", fontsize=8.5, color=GREY, style="italic")
fig.savefig(f"{OUT}/fig_effnet.png"); plt.close(fig)

# ---------- Attention U-Net ----------
fig, ax = canvas(11, 5.6, 22, 11.2)
enc = [(1.0, 8.6, "Enc 1\n32"), (3.2, 6.6, "Enc 2\n64"), (5.4, 4.6, "Enc 3\n128"), (7.6, 2.6, "Enc 4\n256")]
dec = [(17.6, 8.6, "Dec 1\n32"), (15.4, 6.6, "Dec 2\n64"), (13.2, 4.6, "Dec 3\n128")]
for x, y, t in enc: box(ax, x, y, 2.0, 1.6, t, "", BLUE, fs=9)
box(ax, 10.2, 0.6, 2.0, 1.6, "Bottleneck\n512", "", YEL, fs=9)
for x, y, t in dec: box(ax, x, y, 2.0, 1.6, t, "", GRN, fs=9)
box(ax, 19.8, 8.6, 1.9, 1.6, "1x1 Conv\nSigmoid", "", PINK, fs=8.5)
for (x1, y1, _), (x2, y2, _) in zip(enc[:-1], enc[1:]): arrow(ax, (x1 + 1.0, y1), (x2 + 1.0, y2 + 1.6))
arrow(ax, (8.6, 2.6), (10.6, 2.2)); arrow(ax, (11.8, 2.2), (14.2, 4.6))
for (x1, y1, _), (x2, y2, _) in zip(dec[::-1][:-1], dec[::-1][1:]): arrow(ax, (x1 + 1.0, y1 + 1.6), (x2 + 1.0, y2))
arrow(ax, (19.6, 9.4), (19.8, 9.4))
for (xe, ye, _), (xd, yd, _) in zip(enc[:3], dec):
    gx = (xe + xd) / 2 + 0.6
    ax.add_patch(plt.Circle((gx, ye + 0.8), 0.45, fc=PINK, ec="white")); ax.text(gx, ye + 0.8, "AG", ha="center", va="center", fontsize=8, weight="bold", color="white")
    arrow(ax, (xe + 2.0, ye + 0.8), (gx - 0.45, ye + 0.8), col=GREY); arrow(ax, (gx + 0.45, ye + 0.8), (xd, ye + 0.8), col=GREY)
ax.text(11, 10.7, "Skip connections pass through Attention Gates (AG) that suppress non-tumour regions", ha="center", fontsize=9, color=GREY, style="italic")
box(ax, 14.6, 0.4, 7.2, 2.6, "Attention Gate", r"$q=\psi^{T}\,\mathrm{ReLU}(W_x x+W_g g+b)$"+"\n"+r"$\alpha=\sigma(q),\;\hat{x}=\alpha\odot x$", PINK, fs=10, sfs=8)
fig.savefig(f"{OUT}/fig_unet.png"); plt.close(fig)

# ---------- RANO-inspired decision flow ----------
fig, ax = canvas(12, 3.4, 24, 6.8)
box(ax, 0.2, 2.4, 4.4, 2.0, "Baseline + follow-up", "segment both scans", BLUE, 9, 8)
box(ax, 5.4, 2.4, 4.4, 2.0, "Measure", "longest diameter "+r"$d_1$"+",\nperpendicular "+r"$d_2$", YEL, 9, 8)
box(ax, 10.6, 2.4, 4.4, 2.0, r"$P = d_1 \times d_2$", r"$\%\Delta P=(P_1-P_0)/P_0$", ORG, 10, 8.5)
cats = [("Complete response", "lesion no longer seen", GRN, 5.0), ("Partial response", r"$\%\Delta P \leq -50\%$", GRN, 3.5), ("Stable disease", r"$-50\% < \%\Delta P < +25\%$", YEL, 2.0), ("Progressive disease", r"$\%\Delta P \geq +25\%$"+" or new lesion", PINK, 0.5)]
for t, s, c, y in cats:
    box(ax, 17.0, y, 6.8, 1.3, t, s, c, fs=9, sfs=7.5); arrow(ax, (15.0, 3.4), (17.0, y + 0.65))
arrow(ax, (4.6, 3.4), (5.4, 3.4)); arrow(ax, (9.8, 3.4), (10.6, 3.4))
ax.text(7, 0.6, "Imaging-only decision support; clinical RANO also uses steroid dose & neurological status", fontsize=8, color=GREY, style="italic", ha="center")
fig.savefig(f"{OUT}/fig_rano.png"); plt.close(fig)
print("static figures done")
