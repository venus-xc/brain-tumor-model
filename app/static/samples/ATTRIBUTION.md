# Sample Dataset Attribution & Origin

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
