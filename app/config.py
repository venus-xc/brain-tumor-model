import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
STATIC_DIR = APP_DIR / "static"
SAMPLES_DIR = STATIC_DIR / "samples"
REPORTS_DIR = STATIC_DIR / "reports"
UPLOADS_DIR = STATIC_DIR / "uploads"
WEIGHTS_DIR = BASE_DIR / "weights"
RESULTS_DIR = BASE_DIR / "results"
FIGS_DIR = BASE_DIR / "figs"

# Ensure directories exist
for directory in [STATIC_DIR, SAMPLES_DIR, REPORTS_DIR, UPLOADS_DIR, WEIGHTS_DIR, RESULTS_DIR, FIGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Diagnostic Classes (Strict index 0..3)
CLASS_NAMES = ["No tumor", "Glioma", "Meningioma", "Pituitary"]
CLASS_DESCRIPTIONS = {
    "No tumor": "No pathological mass effect or abnormal hyperintensity observed in parenchyma.",
    "Glioma": "Infiltrative neuroepithelial primary brain tumor arising from glial tissue, characteristically displaying heterogeneous core and diffuse edema boundaries.",
    "Meningioma": "Extra-axial tumor arising from arachnoid cap cells, typically showing well-circumscribed, homogeneous enhancement and dural tail sign.",
    "Pituitary": "Neuroendocrine neoplasm situated in the sella turcica, commonly microadenoma or macroadenoma with suprasellar extension.",
}

# Model Display Names
CLASSIFIER_NAMES = {
    "svm": "HOG + SVM",
    "cnn": "Custom CNN",
    "secnn": "SE-CNN",
    "effb0": "EfficientNet-B0 (transfer learning)",
}

SEGMENTATION_NAMES = {
    "unet": "U-Net",
    "attunet": "Attention U-Net",
}

# Image Preprocessing & Model Specifications
CLASSIFIER_SIZES = {
    "svm": 128,
    "cnn": 128,
    "secnn": 128,
    "effb0": 160,
}
SEGMENTATION_SIZE = (256, 256)

NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]

# Mandatory Academic Prototype Disclaimer
ACADEMIC_DISCLAIMER = "Academic decision-support prototype — not for clinical diagnosis."

# Server Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
