"""Grad-CAM and Grad-CAM++ for the fine-tuned EfficientNet-B0 on held-out test images.
Also produces an example inference panel (input, prediction bars, overlay)."""
import numpy as np, torch, torch.nn.functional as F, cv2, json, os, sys
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(__file__)); from models import efficientnet_b0
torch.set_num_threads(2)
CLS = ["No tumor", "Glioma", "Meningioma", "Pituitary"]
d = np.load("data/clean_192.npz"); X, y, sp = d["X"][d["split"] == 2], d["y"][d["split"] == 2], None
probs = np.load("results/effb0_clean_probs.npy")
m = efficientnet_b0(4); m.load_state_dict(torch.load("results/effb0_clean.pth")); m.eval()
MEAN, STD = torch.tensor((0.485, 0.456, 0.406))[None, :, None, None], torch.tensor((0.229, 0.224, 0.225))[None, :, None, None]
def prep(img):
    g = cv2.resize(img, (160, 160), interpolation=cv2.INTER_AREA)
    t = torch.from_numpy(g).float().div(255.)[None, None].repeat(1, 3, 1, 1)
    return (t - MEAN) / STD, g
acts = {}
m.conv_head.register_forward_hook(lambda mod, i, o: acts.__setitem__("A", o))

def cams(img, cls=None):
    t, g = prep(img)
    out = m(t); c = int(out.argmax()) if cls is None else cls
    A = acts["A"]; score = out[0, c]
    grads = torch.autograd.grad(score, A)[0][0]; A = A[0].detach()
    # Grad-CAM: alpha_k = mean_ij dY/dA ; L = ReLU(sum_k alpha_k A_k)
    w = grads.mean((1, 2)); gc = F.relu((w[:, None, None] * A).sum(0))
    # Grad-CAM++ (exp-score closed form): w_ij = g^2 / (2 g^2 + sum_ab A_ab g^3)
    g2, g3 = grads ** 2, grads ** 3
    denom = 2 * g2 + A.sum((1, 2), keepdim=True) * g3
    alpha = g2 / torch.where(denom != 0, denom, torch.ones_like(denom))
    wpp = (alpha * F.relu(grads)).sum((1, 2)); gcpp = F.relu((wpp[:, None, None] * A).sum(0))
    def up(h):
        h = h.numpy(); h = cv2.resize(h, (160, 160), interpolation=cv2.INTER_CUBIC); h = np.maximum(h, 0)
        return h / (h.max() + 1e-8)
    return g, up(gc), up(gcpp), c, F.softmax(out, 1)[0].detach().numpy()

def overlay(g, h):
    col = cv2.applyColorMap((h * 255).astype(np.uint8), cv2.COLORMAP_JET)[:, :, ::-1]
    return (0.55 * np.stack([g] * 3, -1) + 0.45 * col).astype(np.uint8)

pred = probs.argmax(1)
sel = []
for c in [1, 2, 3, 0]:
    cand = np.where((y == c) & (pred == c))[0]
    sel.append(cand[np.argsort(-probs[cand, c])][3])
fig, axs = plt.subplots(3, 4, figsize=(10, 7.8))
for j, k in enumerate(sel):
    g, gc, gcpp, c, p = cams(X[k])
    axs[0, j].imshow(g, cmap="gray"); axs[0, j].set_title(f"True: {CLS[y[k]]}\nPred: {CLS[c]} ({100 * p[c]:.1f}%)", fontsize=9)
    axs[1, j].imshow(overlay(g, gc)); axs[2, j].imshow(overlay(g, gcpp))
for a in axs.flat: a.set_xticks([]); a.set_yticks([])
axs[0, 0].set_ylabel("Input", fontsize=11, weight="bold"); axs[1, 0].set_ylabel("Grad-CAM", fontsize=11, weight="bold"); axs[2, 0].set_ylabel("Grad-CAM++", fontsize=11, weight="bold")
fig.tight_layout(); fig.savefig("figs/fig_gradcam.png", dpi=220); plt.close(fig)

# misclassified examples with explanation
wrong = np.where(pred != y)[0][:3]
fig, axs = plt.subplots(2, 3, figsize=(7.6, 5.4))
for j, k in enumerate(wrong):
    g, gc, gcpp, c, p = cams(X[k])
    axs[0, j].imshow(g, cmap="gray"); axs[0, j].set_title(f"True: {CLS[y[k]]}\nPred: {CLS[c]} ({100 * p[c]:.0f}%)", fontsize=9)
    axs[1, j].imshow(overlay(g, gcpp))
for a in axs.flat: a.set_xticks([]); a.set_yticks([])
axs[0, 0].set_ylabel("Input", weight="bold"); axs[1, 0].set_ylabel("Grad-CAM++", weight="bold")
fig.tight_layout(); fig.savefig("figs/fig_errors.png", dpi=220); plt.close(fig)

# inference panel (what the web app shows for one scan)
k = sel[0]; g, gc, gcpp, c, p = cams(X[k])
fig = plt.figure(figsize=(11, 3.4)); gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1.5])
a = fig.add_subplot(gs[0]); a.imshow(g, cmap="gray"); a.set_title("Uploaded slice (preprocessed)", fontsize=9); a.axis("off")
a = fig.add_subplot(gs[1]); a.imshow(overlay(g, gc)); a.set_title("Grad-CAM overlay", fontsize=9); a.axis("off")
a = fig.add_subplot(gs[2]); a.imshow(overlay(g, gcpp)); a.set_title("Grad-CAM++ overlay", fontsize=9); a.axis("off")
a = fig.add_subplot(gs[3]); cols = ["#8DBA7A", "#EE8F8B", "#5B7FC8", "#F2C64B"]
a.barh(range(4), p * 100, color=cols); a.set_yticks(range(4)); a.set_yticklabels(CLS); a.invert_yaxis(); a.set_xlim(0, 105)
for i, v in enumerate(p * 100): a.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=9)
a.set_title("Softmax probabilities (EfficientNet-B0)", fontsize=9); a.spines[["top", "right"]].set_visible(False)
fig.tight_layout(); fig.savefig("figs/fig_inference.png", dpi=220); plt.close(fig)
print("gradcam done; wrong examples", len(np.where(pred != y)[0]))
