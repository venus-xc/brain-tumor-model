"""Extracts real test images from SARTAJ and Figshare datasets for UI demonstration.
Replaces all synthetic sample images with real public MRI slices.
Generates:
  - 8 classification test images (2 per class: No tumor, Glioma, Meningioma, Pituitary)
  - 2 Figshare segmentation test images with ground-truth masks
  - 1 Real baseline test slice and simulated follow-up (erosion for PR, dilation for PD)
  - app/static/samples/ATTRIBUTION.md citing Bhuvaji et al. and Cheng et al.
"""
import os
import cv2
import numpy as np
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "app", "static", "samples")
CLS_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "clean_192.npz")
SEG_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "seg_256.npz")

os.makedirs(SAMPLES_DIR, exist_ok=True)

CLASS_MAP = {
    0: "normal",
    1: "glioma",
    2: "meningioma",
    3: "pituitary",
}


def main():
    print("Generating real test samples...")
    if not os.path.exists(CLS_PATH) or not os.path.exists(SEG_PATH):
        raise FileNotFoundError("Processed datasets missing. Run prepare scripts first.")

    # 1. Classification test samples (split == 2)
    d_cls = np.load(CLS_PATH)
    X_cls = d_cls["X"][d_cls["split"] == 2]
    y_cls = d_cls["y"][d_cls["split"] == 2]

    # Pick 2 per class
    for c_id, c_name in CLASS_MAP.items():
        indices = np.where(y_cls == c_id)[0]
        # Choose two distinct test images
        img1 = X_cls[indices[5]]
        img2 = X_cls[indices[12]]

        p1 = os.path.join(SAMPLES_DIR, f"sample_{c_name}_1.png")
        p2 = os.path.join(SAMPLES_DIR, f"sample_{c_name}_2.png")
        Image.fromarray(img1).save(p1)
        Image.fromarray(img2).save(p2)

        # Primary alias for UI button
        alias_p = os.path.join(SAMPLES_DIR, f"sample_{c_name}.png")
        Image.fromarray(img1).save(alias_p)
        print(f"Saved {c_name} samples: {p1}, {p2}")

    # 2. Figshare segmentation test samples (split == 2)
    d_seg = np.load(SEG_PATH)
    X_seg = d_seg["X"][d_seg["split"] == 2]
    M_seg = d_seg["M"][d_seg["split"] == 2]
    L_seg = d_seg["label"][d_seg["split"] == 2]

    # Find two distinct test slices with clear tumor masks
    mening_idx = np.where(L_seg == 1)[0]
    # Pick one with solid area
    areas_m = [M_seg[i].sum() for i in mening_idx]
    best_m = mening_idx[np.argsort(-np.array(areas_m))[0]]

    glioma_idx = np.where(L_seg == 2)[0]
    areas_g = [M_seg[i].sum() for i in glioma_idx]
    best_g = glioma_idx[np.argsort(-np.array(areas_g))[0]]

    # Save figshare test images & masks
    f1_img = X_seg[best_m]
    f1_mask = (M_seg[best_m] * 255).astype(np.uint8)
    Image.fromarray(f1_img).save(os.path.join(SAMPLES_DIR, "figshare_test_1.png"))
    Image.fromarray(f1_mask).save(os.path.join(SAMPLES_DIR, "figshare_test_1_mask.png"))

    f2_img = X_seg[best_g]
    f2_mask = (M_seg[best_g] * 255).astype(np.uint8)
    Image.fromarray(f2_img).save(os.path.join(SAMPLES_DIR, "figshare_test_2.png"))
    Image.fromarray(f2_mask).save(os.path.join(SAMPLES_DIR, "figshare_test_2_mask.png"))
    print("Saved Figshare segmentation test samples.")

    # 3. Longitudinal demonstration pair from real Figshare test image
    # Baseline: real test image (meningioma)
    baseline_img = f1_img
    baseline_mask = f1_mask

    # Simulated follow-up (erosion for PR demo, dilation for PD demo)
    kernel = np.ones((5, 5), np.uint8)
    eroded_mask = cv2.erode(baseline_mask, kernel, iterations=3)
    dilated_mask = cv2.dilate(baseline_mask, kernel, iterations=3)

    # Blend eroded mask into follow-up image to show realistic regression
    followup_img_pr = baseline_img.copy()
    # Mask area that shrank: slightly darken or blend with tissue
    shrunk_region = (baseline_mask > 0) & (eroded_mask == 0)
    followup_img_pr[shrunk_region] = (followup_img_pr[shrunk_region] * 0.6).astype(np.uint8)

    Image.fromarray(baseline_img).save(os.path.join(SAMPLES_DIR, "longitudinal_baseline.png"))
    Image.fromarray(baseline_mask).save(os.path.join(SAMPLES_DIR, "longitudinal_baseline_mask.png"))
    Image.fromarray(followup_img_pr).save(os.path.join(SAMPLES_DIR, "longitudinal_followup.png"))
    Image.fromarray(eroded_mask).save(os.path.join(SAMPLES_DIR, "longitudinal_followup_mask_pr.png"))
    Image.fromarray(dilated_mask).save(os.path.join(SAMPLES_DIR, "longitudinal_followup_mask_pd.png"))
    print("Saved real longitudinal baseline and simulated follow-up pair.")

    # 4. Attribution document
    attribution_text = """# Sample Dataset Attribution & Origin

All sample images located in this directory (`app/static/samples/`) are extracted directly from held-out test splits of peer-reviewed, publicly available neuro-imaging datasets. **No synthetic, cartoon, or generative images are used.**

---

## 1. Multi-Class Classification Test Samples
* **Files**:
  - `sample_normal.png` / `sample_normal_1.png` / `sample_normal_2.png` (Class: No tumor)
  - `sample_glioma.png` / `sample_glioma_1.png` / `sample_glioma_2.png` (Class: Glioma)
  - `sample_meningioma.png` / `sample_meningioma_1.png` / `sample_meningioma_2.png` (Class: Meningioma)
  - `sample_pituitary.png` / `sample_pituitary_1.png` / `sample_pituitary_2.png` (Class: Pituitary Tumor)
* **Dataset**: SARTAJ Brain Tumor Classification (MRI) Dataset
* **Citation**: Sartaj Bhuvaji, Ankita Kadam, Prajakta Bhumkar, Sameer Dedge, Swati Kanchan. *Brain Tumor Classification (MRI)*. Kaggle (2020). DOI: [10.34740/KAGGLE/DSV/1183165](https://doi.org/10.34740/KAGGLE/DSV/1183165).
* **Provenance**: Drawn strictly from the held-out de-duplicated test split (`data/processed/clean_192.npz`, split index 2).

---

## 2. Semantic Lesion Segmentation Test Samples
* **Files**:
  - `figshare_test_1.png` & `figshare_test_1_mask.png` (Meningioma lesion with expert annotation)
  - `figshare_test_2.png` & `figshare_test_2_mask.png` (Glioma lesion with expert annotation)
* **Dataset**: Figshare Brain Tumor Dataset
* **Citation**: Jun Cheng, Wei Huang, Shuang Shen, Zeyu Peng, Tao Zeng, Xiaokang Wang, Wei Yang. *Brain Tumor Dataset*. Figshare (2017). DOI: [10.6084/m9.figshare.1512427.v5](https://doi.org/10.6084/m9.figshare.1512427.v5).
* **Licence**: Creative Commons Attribution 4.0 International (CC BY 4.0).
* **Provenance**: Patient-level held-out test split (`data/processed/seg_256.npz`, split index 2).

---

## 3. Longitudinal Demonstration Pair
* **Files**:
  - `longitudinal_baseline.png` & `longitudinal_baseline_mask.png`
  - `longitudinal_followup.png` (Simulated follow-up with mask erosion/dilation for demonstration)
* **Origin**: Real T1-CE axial MRI slice from Figshare test patient, modified via morphological erosion/dilation strictly to illustrate the automated RANO-inspired response calculation (PR / PD) without fabricating patient identities.
* **Disclaimer**: Academic decision-support prototype — not for clinical diagnosis.
"""
    with open(os.path.join(SAMPLES_DIR, "ATTRIBUTION.md"), "w") as f:
        f.write(attribution_text)
    print("Created ATTRIBUTION.md")


if __name__ == "__main__":
    main()
