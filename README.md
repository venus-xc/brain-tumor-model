# Brain Tumor Detection and Monitoring Using Artificial Intelligence and Machine Learning

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PyTorch 2.x](https://img.shields.io/badge/PyTorch-2.x-red.svg)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Academic Seminar Project Reference:**  
> **Title:** Brain Tumor Detection and Monitoring Using Artificial Intelligence and Machine Learning  
> **Supervisor / Guide:** Mrs. Swarnalata Pati  
> **Authors:** Chinmayee Patra (Regd. No. 23110206), Shruti Sameekshya Dehury (Regd. No. 23110234)

---

## 🔬 Project Overview

Manual interpretation of brain magnetic resonance imaging (MRI) is time-consuming and prone to inter-observer variability, particularly for irregular margins, diffuse infiltration, or small lesions. 

This system provides a full-stack, clinically motivated deep learning workstation implementing all core capabilities articulated in the research seminar:
1. **Multi-Class Detection & Classification**: Discerning between **Glioma**, **Meningioma**, **Pituitary Tumor**, and **Healthy / No Tumor** with Softmax probability distributions.
2. **Automated Tumor Segmentation (U-Net)**: Pixel-level delineation of lesions, necrotic cores, and diffuse boundaries using a skip-connected encoder-decoder architecture.
3. **Quantitative Volumetric & Morphometric Analysis**: Surface area ($mm^2$, $cm^2$), equivalent diameter, orthogonal RECIST diameters (major/minor axes), perimeter, sphericity/compactness index, and 3D volumetric burden ($cm^3$).
4. **Longitudinal Patient Monitoring & Treatment Response**: Longitudinal tracking across successive scans (Baseline vs. Follow-up) evaluated under neuro-oncology **RANO / RECIST** criteria (Complete Response, Partial Response, Stable Disease, Progressive Disease) and spatial delta difference maps.
5. **Explainable AI (Grad-CAM)**: Visualizing neural decision attribution through Gradient-weighted Class Activation Mapping heatmaps overlaid on MRI scans.
6. **Automated Clinical PDF Reporting**: Generating board-certified style PDF diagnostic reports with embedded imaging triads, metric tables, and structured impressions.
7. **Production Deployment**: Complete Docker, Docker-Compose, and FastAPI REST microservice ready for on-premise or cloud deployment.

---

## 🏛️ System Architecture

```
                    ┌────────────────────────────┐
                    │   Input MRI Examination    │
                    │   (DICOM / PNG / JPEG)     │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │ Medical Image Preprocessor │
                    │ (Parenchyma crop, CLAHE)   │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Classification  │    │ U-Net Biomedical │    │ Explainable AI   │
│  Deep CNN Head   │    │   Segmentation   │    │ (Grad-CAM Hooks) │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         │  Class Probabilities  │ Binary Mask           │ Heatmap Overlay
         └───────────┬───────────┴───────────┬───────────┘
                     ▼                       ▼
      ┌─────────────────────────────┐ ┌─────────────────────────────┐
      │  Quantitative Morphometrics │ │   Longitudinal Monitoring   │
      │   (Volume, Area, RECIST)    │ │   (ΔV, % Change, RANO)      │
      └──────────────┬──────────────┘ └──────────────┬──────────────┘
                     │                               │
                     └───────────────┬───────────────┘
                                     ▼
      ┌─────────────────────────────────────────────────────────────┐
      │        Interactive PACS Workstation & PDF Generator         │
      │           (FastAPI Web UI, ReportLab Engine)                │
      └─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local Setup)

### 1. Clone & Navigate
```bash
cd brain_tumor
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run Benchmark CLI Verification
```bash
python main.py --evaluate
```

### 4. Launch Web Workstation
```bash
python main.py --host 0.0.0.0 --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to access the Clinical PACS Workstation.

---

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
docker compose up --build
```
Access the application on `http://localhost:8000`. Diagnostic reports and model weights are persisted in Docker volumes.

### Using Standalone Docker
```bash
docker build -t brain-tumor-ai .
docker run -p 8000:8000 brain-tumor-ai
```

---

## 🧪 Running Automated Tests

Run the full PyTest suite covering models, quantitative calculations, and API endpoints:
```bash
source .venv/bin/activate
pytest tests/ -v
```

---

## 📡 REST API Documentation

FastAPI provides interactive Swagger documentation at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Clinical Radiologist PACS Web Dashboard |
| `/api/health` | `GET` | Healthcheck and GPU/CPU device status |
| `/api/samples` | `GET` | Returns benchmark sample MRI scans metadata |
| `/api/predict` | `POST` | Multi-task inference (Classification + U-Net + Grad-CAM + Morphometrics) |
| `/api/longitudinal` | `POST` | Longitudinal multi-timepoint analysis (Baseline vs Follow-up) |
| `/api/report` | `POST` | Generates official Clinical Diagnostic PDF Report |
| `/api/report/download/{file}` | `GET` | Downloads generated PDF report |

---

## 📊 Clinical Metric Formulations

- **Surface Area ($mm^2$)**: $A = N_{\text{pixels}} \times s_x \times s_y$
- **Volumetric Approximation ($cm^3$)**: $V = \frac{A \times s_z}{1000}$
- **Equivalent Diameter ($mm$)**: $d = 2 \times \sqrt{\frac{A}{\pi}}$
- **Sphericity Index**: $\psi = \frac{4\pi A}{P^2} \in [0, 1]$
- **RANO Response Classification**:
  - **Complete Response (CR)**: 100% resolution of lesion ($V_2 = 0$)
  - **Partial Response (PR)**: $\% \Delta V \le -50\%$
  - **Stable Disease (SD)**: $-50\% < \% \Delta V < +25\%$
  - **Progressive Disease (PD)**: $\% \Delta V \ge +25\%$
