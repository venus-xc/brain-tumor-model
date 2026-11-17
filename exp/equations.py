"""Single source of truth for equations: LaTeX used for Word (OMML via pandoc) and PPT (PNG via mathtext)."""
EQ = {
    "conv": r"(I * K)(i,j) = \sum_{m}\sum_{n} I(i+m,\, j+n)\, K(m,n)",
    "relu": r"\mathrm{ReLU}(x) = \max(0,\, x)",
    "softmax": r"p_c = \frac{e^{z_c}}{\sum_{j=1}^{4} e^{z_j}}",
    "ce": r"\mathcal{L}_{CE} = -\frac{1}{N}\sum_{i=1}^{N}\sum_{c=1}^{4} w_c\, \tilde{y}_{i,c}\, \log p_{i,c}",
    "smooth": r"\tilde{y}_{i,c} = (1-\varepsilon)\, y_{i,c} + \frac{\varepsilon}{4}, \quad \varepsilon = 0.05",
    "cw": r"w_c = \frac{N}{4\, N_c}",
    "squeeze": r"z_c = \frac{1}{H \times W}\sum_{i=1}^{H}\sum_{j=1}^{W} X_c(i,j)",
    "excite": r"\mathbf{s} = \sigma\left(W_2\, \delta(W_1 \mathbf{z})\right), \quad \tilde{X}_c = s_c \cdot X_c",
    "hog": r"G = \sqrt{G_x^2 + G_y^2}, \quad \theta = \arctan\left(\frac{G_y}{G_x}\right)",
    "svm": r"\min_{\mathbf{w},b,\xi}\ \frac{1}{2}\lVert \mathbf{w} \rVert^2 + C\sum_{i=1}^{N} \xi_i",
    "rbf": r"K(\mathbf{x},\mathbf{x}') = \exp\left(-\gamma \lVert \mathbf{x}-\mathbf{x}' \rVert^2\right)",
    "acc": r"\mathrm{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}",
    "prec": r"\mathrm{Precision} = \frac{TP}{TP + FP}, \quad \mathrm{Recall} = \frac{TP}{TP + FN}",
    "f1": r"F_1 = \frac{2 \cdot \mathrm{Precision} \cdot \mathrm{Recall}}{\mathrm{Precision} + \mathrm{Recall}}",
    "dice": r"\mathrm{Dice}(P,G) = \frac{2\,\lvert P \cap G \rvert}{\lvert P \rvert + \lvert G \rvert}",
    "segloss": r"\mathcal{L}_{seg} = \mathcal{L}_{BCE} + \left(1 - \frac{2\sum_i y_i \hat{y}_i + 1}{\sum_i y_i + \sum_i \hat{y}_i + 1}\right)",
    "ag": r"q = \psi^{T}\, \mathrm{ReLU}\left(W_x^{T} x_i + W_g^{T} g_i + b_g\right) + b_{\psi}, \quad \alpha_i = \sigma(q)",
    "gc_w": r"\alpha_k^c = \frac{1}{Z}\sum_{i}\sum_{j} \frac{\partial y^c}{\partial A_{ij}^k}",
    "gc_map": r"L_{\mathrm{GradCAM}}^c = \mathrm{ReLU}\left(\sum_k \alpha_k^c A^k\right)",
    "gcpp": r"w_{ij}^{kc} = \frac{\left(\partial y^c / \partial A_{ij}^k\right)^2}{2\left(\partial y^c / \partial A_{ij}^k\right)^2 + \sum_{a}\sum_{b} A_{ab}^k \left(\partial y^c / \partial A_{ij}^k\right)^3}",
    "area": r"A_{tumour} = N_{pix} \cdot \Delta x \cdot \Delta y",
    "rano": r"P = d_1 \times d_2, \quad \%\Delta P = \frac{P_{1} - P_{0}}{P_{0}} \times 100",
}

if __name__ == "__main__":
    import os, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    os.makedirs("figs/eq", exist_ok=True)
    import subprocess, tempfile, shutil
    tmp = tempfile.mkdtemp()
    for k, v in EQ.items():
        doc = (r"\documentclass[border=3pt,varwidth=40cm]{standalone}\usepackage{amsmath,amssymb,bm,xcolor}"
               r"\definecolor{ink}{HTML}{1F2937}\begin{document}\color{ink}\Large $\displaystyle " + v + r"$\end{document}")
        open(f"{tmp}/{k}.tex", "w").write(doc)
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-output-directory", tmp, f"{tmp}/{k}.tex"], capture_output=True, check=True)
        subprocess.run(["pdftoppm", "-r", "400", "-png", "-singlefile", "-transp" if False else "-png", f"{tmp}/{k}.pdf", f"figs/eq/{k}"], check=True)
        # make white background transparent
        from PIL import Image; import numpy as np
        im = np.array(Image.open(f"figs/eq/{k}.png").convert("RGB")).astype(np.float32)
        a = 255 - im.min(2); rgba = np.dstack([np.full(im.shape[:2] + (3,), [31, 41, 55]), a]).astype(np.uint8)
        img = Image.fromarray(rgba, "RGBA"); bb = img.getbbox(); img = img.crop((max(bb[0]-12,0), max(bb[1]-12,0), bb[2]+12, bb[3]+12)); img.save(f"figs/eq/{k}.png")
    shutil.rmtree(tmp); print("equations rendered", len(EQ))
