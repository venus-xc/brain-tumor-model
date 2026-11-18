# Brain Tumor Decision-Support Prototype: Complete Project Context

> **Academic Disclaimer**: This project is an **academic decision-support prototype** developed for a final-year B.Tech thesis at Odisha University of Technology and Research (OUTR), Bhubaneswar. It is **not for clinical diagnosis, medical triage, or patient treatment**.

---

## 1. Executive Summary & Institutional Metadata

- **Project Title**: Brain Tumor Detection and Monitoring Using Artificial Intelligence and Machine Learning
- **Institution**: Department of Computer Science and Engineering, Odisha University of Technology and Research (OUTR), Bhubaneswar, Odisha – 751029, India
- **Degree**: Bachelor of Technology (B.Tech) in Computer Science and Engineering (Artificial Intelligence and Machine Learning)
- **Student Investigators**:
  - **Chinmayee Patra** (Registration No: `23110206`)
  - **Shruti Sameekshya Dehury** (Registration No: `23110234`)
- **Project Supervisor**: **Mrs. Swarna Lata Pati**, Assistant Professor, Department of CSE, OUTR Bhubaneswar
- **Department Head**: **Dr. Ranjan Kumar Dash**, Professor & Head, Department of CSE, OUTR Bhubaneswar
- **Repository Path**: `/Users/abinashmohanty/Downloads/brain_tumor`
- **Local Application Server**: `http://127.0.0.1:8000`

---

## 2. Core Engineering Modules

The workstation integrates five verified computational modules:

1. **4-Class Brain Tumor Classifier**:
   - Diagnoses axial T1/T1-CE brain MRI slices into 4 distinct classes:
     - `0`: No tumor (Healthy brain parenchyma)
     - `1`: Glioma (Intra-axial infiltrative mass)
     - `2`: Meningioma (Extra-axial dural-based mass)
     - `3`: Pituitary (Sellar / parasellar mass)
   - Evaluates 4 distinct architectures:
     - Classical ML: **HOG + SVM** with RBF kernel and PCA-150 dimensionality reduction.
     - Deep Learning: **Custom CNN** (4 stages: [32, 64, 128, 256]).
     - Attention Deep Learning: **SE-CNN** (Squeeze-and-Excitation channel recalibration, reduction ratio $r=16$).
     - Transfer Learning: **EfficientNet-B0** pre-trained on ImageNet.
2. **Biomedical Semantic Lesion Segmentation**:
   - Trained on 256×256 single-channel T1-CE slices with BCEWithLogits + Soft Dice loss.
   - Evaluates **Biomedical U-Net** (7,762,465 parameters) and **Attention U-Net** (8,722,077 parameters with additive skip-connection attention gates).
3. **Dual Explainable AI (XAI)**:
   - First-order **Grad-CAM** and higher-order **Grad-CAM++** computed via exact autograd derivatives on feature extractor layers.
   - Attention Gate activation maps extracted from Attention U-Net skip connections.
4. **Quantitative 2D Morphometrics (Index Slice)**:
   - Strictly 2D planar measurements:
     - $\text{Area}_{\text{mm}^2} = N_{\text{pixels}} \cdot \Delta x \cdot \Delta y$ (and $\text{cm}^2$).
     - Longest diameter $d_1$ (PCA major axis) and perpendicular diameter $d_2$ (orthogonal PCA span).
     - Perpendicular product $P = d_1 \times d_2$.
     - Reports in pixel units when physical spacing is not provided (`spacing_source: "not provided"`).
     - Purged of fabricated 3D volume, 3D sphericity, or surface area claims.
5. **Longitudinal RANO 2D Follow-Up Assessment**:
   - Compares serial scans: $\% \Delta P = \frac{P_1 - P_0}{P_0} \times 100$.
   - Assigns RANO-inspired response categories:
     - **Partial Response (PR)**: $\% \Delta P \le -50\%$
     - **Progressive Disease (PD)**: $\% \Delta P \ge +25\%$
     - **Complete Response (CR)**: Complete resolution of measurable lesion
     - **Stable Disease (SD)**: Neither PR nor PD met
   - Produces neutral imaging notes and chromatic difference maps (Green = Regression, Red = Progression, Yellow = Stable).

---

## 3. Dataset Attribution & De-Duplication Protocol

1. **Classification Dataset**: Sartaj Bhuvaji et al. (Kaggle 2020, doi:10.34740/KAGGLE/DSV/1183165), 3,264 axial images.
   - **Audit**: Identified **69 duplicate image groups spanning the official train and test folders** via 32×32 cosine similarity ($\ge 0.98$).
   - **Clean Split**: 70/15/15 stratified group split using `StratifiedGroupKFold` (seed 42) yielding 2,803 unique images with **zero duplicate groups crossing partitions**.
2. **Segmentation Dataset**: Figshare Brain Tumor Dataset (Cheng et al., doi:10.6084/m9.figshare.1512427.v5), 3,064 slices, 233 patients.
   - **Patient-Level Split**: Partitioned by `PID` using `GroupShuffleSplit` (seed 42) into Train (2,153 slices, 163 patients), Validation (457 slices, 35 patients), and Test (454 slices, 35 patients) with **zero patient overlap across partitions**.

---

## 4. Empirical Evaluation Results Summary

| Model Architecture | Task | Resolution | Parameters | Test Metric (Accuracy / Dice) | Macro F1 / IoU | ROC-AUC |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **HOG + Logistic Regression** | Classification | $128 \times 128$ | -- | 72.14% | 0.6976 | 0.9123 |
| **HOG + Random Forest** | Classification | $128 \times 128$ | -- | 77.38% | 0.7612 | 0.9388 |
| **HOG + k-NN ($k=5$)** | Classification | $128 \times 128$ | -- | 79.05% | 0.7788 | 0.9254 |
| **HOG + SVM (RBF)** | Classification | $128 \times 128$ | -- | **84.76%** | **0.8381** | **0.9661** |
| **Custom CNN** | Classification | $128 \times 128$ | 1,206,052 | 75.48% | 0.7491 | 0.9563 |
| **SE-CNN** | Classification | $128 \times 128$ | 1,228,352 | **80.48%** | **0.7888** | **0.9520** |
| **EfficientNet-B0 (Clean Split)** | Classification | $160 \times 160$ | 4,012,672 | **96.67%** | **0.9701** | **0.9965** |
| *EfficientNet-B0 (Official Split)* | Classification | $160 \times 160$ | 4,012,672 | *80.46%* | *0.7862* | *0.9421* |
| **Biomedical U-Net** | Segmentation | $256 \times 256$ | 7,762,465 | 0.691 DSC | 0.601 IoU | -- |
| **Attention U-Net** | Segmentation | $256 \times 256$ | 8,722,077 | **0.745 DSC** | **0.653 IoU** | -- |

---

## 5. Generated Artifacts & Deliverables

1. **Word Thesis Document**: `paper/Final_Report_Brain_Tumor_Detection_OUTR.docx` (7.4 MB, 9 full chapters, all figures & tables).
2. **PDF Thesis Document**: `paper/Final_Report_Brain_Tumor_Detection_OUTR.pdf` (3.8 MB, complete compiled PDF).
3. **Presentation Deck**: `paper/Brain_Tumor_Detection_Presentation.pptx` (4.9 MB, 26 slides, light theme).
4. **Live Web Application**: Single-page application at `http://127.0.0.1:8000` with light theme, 2D planar morphometrics, and automated PDF clinical report generator.
5. **Automated Test Suite**: 27 unit and integration tests passing (`pytest -v`), verifying parameter counts, 2D metrics, API contracts, and zero hardcoded metrics.
