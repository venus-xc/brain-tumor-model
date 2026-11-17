# Brain MRI Analysis, Segmentation & Longitudinal Monitoring (Academic Prototype)

> **Academic Disclaimer**: This software is an **academic decision-support prototype** developed as a final-year B.Tech project. It is **not intended or certified for clinical diagnosis, patient management, or treatment planning**. All evaluations were performed on retrospective, anonymized public research datasets.

---

## 1. Project Information & Institutional Affiliation

- **Project Title**: Brain Tumor Detection and Monitoring Using Artificial Intelligence and Machine Learning
- **Institution**: Department of Computer Science and Engineering, Odisha University of Technology and Research (OUTR), Bhubaneswar, Odisha, India
- **Degree**: Bachelor of Technology (B.Tech) in Computer Science and Engineering (Artificial Intelligence & Machine Learning)
- **Student Investigators**:
  - **Chinmayee Patra** (Registration No: `23110206`)
  - **Shruti Sameekshya Dehury** (Registration No: `23110234`)
- **Project Supervisor**: **Mrs. Swarna Lata Pati**, Assistant Professor, Department of CSE, OUTR Bhubaneswar

---

## 2. Research Benchmark Datasets

This project uses exclusively public research datasets with complete academic attribution. **No synthetic data is used for classifier or segmenter training or evaluation.**

1. **4-Class Brain Tumor Classification Dataset (Sartaj Benchmark)**:
   - **Citation**: Sartaj Bhuvaji, Ankita Kadam, Prajakta Bhumkar, Sameer Dedge, and Swati Kanchan, *Brain Tumor Classification (MRI)*, Kaggle, 2020. [doi:10.34740/KAGGLE/DSV/1183165](https://doi.org/10.34740/KAGGLE/DSV/1183165).
   - **Composition**: 3,264 axial T1-weighted / T1-contrast-enhanced MRI scans across 4 classes:
     - `No tumor`: Normal brain parenchyma (Index `0`)
     - `Glioma`: Intra-axial neuroepithelial tumor (Index `1`)
     - `Meningioma`: Extra-axial dural-based tumor (Index `2`)
     - `Pituitary`: Sellar / parasellar adenoma (Index `3`)

2. **Brain Tumor Segmentation Dataset (Figshare Benchmark)**:
   - **Citation**: Jun Cheng, Wei Huang, Shuang Shen, Zeyu Peng, Tao Zeng, Xiaokang Wang, and Zhaoxiang Chen, *Brain tumor dataset*, Figshare, 2017. [doi:10.6084/m9.figshare.1512427.v5](https://doi.org/10.6084/m9.figshare.1512427.v5). License: CC BY 4.0.
   - **Composition**: 3,064 T1-weighted contrast-enhanced (T1-CE) slices from 233 patients with expert ground-truth manual segmentation masks and Patient IDs (PIDs).

---

## 3. Data Integrity & Leakage-Free Protocol

A major scientific contribution of this project is the **empirical identification and resolution of cross-partition data leakage** in public benchmarks:

- **Sartaj De-duplication Audit**: Using 32×32 cosine similarity ($\ge 0.98$) and connected-component clustering, we identified **69 near-duplicate image groups spanning the official train and test folders**, which artificially inflates reported test metrics.
- **Clean Split**: We established a leakage-free 70/15/15 partition using `StratifiedGroupKFold` (seed 42), retaining 2,803 unique images (Train: 1,962, Val: 421, Test: 420) with **zero duplicate groups crossing partitions**.
- **Figshare Patient-Level Partition**: 3,064 slices were partitioned strictly by `PID` using `GroupShuffleSplit` (seed 42) into Train (2,153 slices, 163 patients), Validation (457 slices, 35 patients), and Test (454 slices, 35 patients), ensuring **zero patient overlap across subsets**.

---

## 4. Empirical Evaluation Results

All deep learning and classical ML models were evaluated on the held-out test split (seed 42, evaluated exactly once):

### 4.1. 4-Class Classification Comparison (Held-Out Test Set, $n=420$)

| Model Architecture | Input Resolution | Parameters | Test Accuracy | Macro F1 | ROC-AUC (OvR) | Notes |
|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **HOG + Logistic Regression** | $128 \times 128$ | -- | 72.14% | 0.6976 | 0.9123 | Linear baseline (PCA-150) |
| **HOG + Random Forest** | $128 \times 128$ | -- | 77.38% | 0.7612 | 0.9388 | Ensemble baseline (300 trees) |
| **HOG + k-NN ($k=5$)** | $128 \times 128$ | -- | 79.05% | 0.7788 | 0.9254 | Metric distance baseline |
| **HOG + SVM (RBF kernel)** | $128 \times 128$ | -- | **84.76%** | **0.8381** | **0.9661** | Best classical ML pipeline |
| **Custom CNN (Baseline)** | $128 \times 128$ | 1,206,052 | 75.48% | 0.7491 | 0.9563 | 4 stages: [32, 64, 128, 256] |
| **SE-CNN (Channel Attention)** | $128 \times 128$ | 1,228,352 | **80.48%** | **0.7888** | **0.9520** | **+5.0% gain from SE attention** |
| **EfficientNet-B0 (Transfer Learning)** | $160 \times 160$ | 4,012,672 | **96.67%** | **0.9701** | **0.9965** | Best overall (Clean Split) |
| *EfficientNet-B0 (Official Split)* | $160 \times 160$ | 4,012,672 | *80.46%* | *0.7862* | *0.9421* | Demonstrates impact of split leakage |

### 4.2. Lesion Segmentation on Held-Out Patients (35 Unseen Patients, 454 Slices)

| Architecture | Input Resolution | Parameters | Mean Dice (DSC) | Mean IoU | Meningioma Dice | Glioma Dice | Pituitary Dice |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Biomedical U-Net** | $256 \times 256$ | 7,762,465 | 0.781 | 0.672 | 0.842 | 0.741 | 0.797 |
| **Attention U-Net** | $256 \times 256$ | 8,105,201 | **0.812** | **0.705** | **0.866** | **0.779** | **0.821** |

---

## 5. Architectural & Methodological Highlights

1. **Dual Explainable AI (XAI)**:
   - First-order **Grad-CAM** (Selvaraju et al., ICCV 2017) and higher-order **Grad-CAM++** (Chattopadhay et al., IEEE ISM 2018) computed directly via autograd on feature extractor layers.
   - Attention Gate activation maps extracted from Attention U-Net skip connections to visualize selective spatial filtering.
2. **Quantitative 2D Morphometrics (Index Slice)**:
   - **Planar Area**: $\text{Area}_{\text{mm}^2} = N_{\text{pixels}} \cdot \Delta x \cdot \Delta y$ (and $\text{cm}^2$).
   - **Principal Diameters**: Longest diameter $d_1$ (PCA major axis) and perpendicular diameter $d_2$ (orthogonal PCA span).
   - **Perpendicular Product**: $P = d_1 \times d_2$ (used in 2D RANO clinical trial criteria).
   - Strictly 2D; no unscientific 3D volumetric claims from single 2D slices.
3. **Longitudinal RANO Follow-Up Assessment**:
   - Compares baseline ($P_0$) and follow-up ($P_1$) scans: $\% \Delta P = \frac{P_1 - P_0}{P_0} \times 100$.
   - Evaluates response: **Partial Response (PR)** ($\% \Delta P \le -50\%$), **Progressive Disease (PD)** ($\% \Delta P \ge +25\%$), **Complete Response (CR)** (resolution of measurable lesion), and **Stable Disease (SD)**.
   - Generates chromatic difference maps (Green = Regression, Red = Progression, Yellow = Stable).
4. **Academic PDF Report Generator**:
   - Generates multi-page academic PDF reports using ReportLab with patient demographics, model predictions, interpretability panels, 2D measurements, and disclaimer banners.

---

## 6. Project Structure

```
brain_tumor/
├── app/
│   ├── api.py                     # FastAPI server with all REST endpoints
│   ├── config.py                  # Core configuration, paths, and class labels
│   ├── models/
│   │   ├── cnn.py                 # BrainCNN: Custom CNN & SE-CNN implementations
│   │   ├── efficientnet.py        # EfficientNet-B0 transfer learning wrapper
│   │   ├── classical.py           # HOG feature extractor & SVM pipeline loader
│   │   ├── unet.py                # Biomedical U-Net (256x256 single-channel)
│   │   ├── attention_unet.py      # Attention U-Net with skip-connection attention gates
│   │   ├── gradcam.py             # Autograd Grad-CAM engine
│   │   ├── gradcam_plus_plus.py   # Higher-order Grad-CAM++ engine
│   │   └── pipeline.py            # Unified multi-task inference pipeline
│   ├── services/
│   │   ├── preprocessor.py        # CLAHE, intensity rescaling, parenchyma cropping
│   │   ├── quantitative.py        # 2D planar morphometrics (area, d1, d2, product)
│   │   ├── longitudinal.py        # Temporal comparison & RANO response assessment
│   │   └── report_generator.py    # ReportLab academic PDF generator
│   ├── static/                    # Clean light-theme CSS, JS, and verified test samples
│   └── templates/index.html       # Minimalist single-page web workstation
├── data/processed/                # Preprocessed clean_192.npz and seg_256.npz datasets
├── exp/                           # Research experiment scripts for plots & figures
├── figs/                          # Generated high-resolution figures & web app screenshot
├── paper/
│   ├── Final_Report_Brain_Tumor_Detection_OUTR.docx  # 9-Chapter Word Thesis Report (7.4 MB)
│   ├── Final_Report_Brain_Tumor_Detection_OUTR.pdf   # 9-Chapter PDF Thesis Report (3.8 MB)
│   ├── Brain_Tumor_Detection_Presentation.pptx      # 26-Slide Defense Presentation (4.9 MB)
│   └── report_builder/            # Document building engine (build_report.py, build_ppt.js)
├── results/                       # Empirical JSON results and predictions
├── scripts/
│   ├── download_data.sh           # Data acquisition script for Sartaj & Figshare
│   ├── prepare_classification.py  # CLAHE + crop + de-duplication + clean split
│   ├── prepare_segmentation.py    # Figshare extraction + patient-level split
│   ├── train_classical.py         # Classical ML training (SVM, RF, kNN, LR)
│   ├── train_classifier.py        # Deep classifier training (CNN, SE-CNN, EffB0)
│   ├── train_segmentation.py      # U-Net & Attention U-Net training
│   ├── generate_segmentation_figure.py # Test comparison figure generator
│   └── evaluate_all.sh            # End-to-end master execution pipeline
├── tests/                         # Comprehensive pytest test suite (27 passed)
├── requirements.txt               # Exact pinned dependencies
└── train.py                       # CLI execution entry point
```

---

## 7. Quickstart Guide

### 7.1. Environment Setup

```bash
# 1. Clone repository
git clone <repo_url>
cd brain_tumor

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt
```

### 7.2. Run the Web Workstation Locally

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at `http://127.0.0.1:8000`.

### 7.3. Run Unit Tests

```bash
pytest -v
```

All 27 automated tests covering API endpoints, models, exact parameter counts, 2D morphometrics, RANO follow-up, Grad-CAM, de-duplication integrity, and zero hardcoded metrics will execute.

### 7.4. Run End-to-End Evaluation Pipeline

```bash
# Downloads datasets and executes all training, figure rendering, and document builds
bash scripts/evaluate_all.sh
```

---

## 8. Final Academic Deliverables

- **Word Thesis Report**: `paper/Final_Report_Brain_Tumor_Detection_OUTR.docx` (7.4 MB)
- **PDF Thesis Report**: `paper/Final_Report_Brain_Tumor_Detection_OUTR.pdf` (3.8 MB)
- **Defense Slide Deck**: `paper/Brain_Tumor_Detection_Presentation.pptx` (4.9 MB, 26 slides)
- **Evaluation Matrix**: `results/metrics.json` and `results/segmentation.json`
