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

# Ensure directories exist
for directory in [STATIC_DIR, SAMPLES_DIR, REPORTS_DIR, UPLOADS_DIR, WEIGHTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Diagnostic Classes
CLASS_NAMES = ["Healthy / No Tumor", "Glioma", "Meningioma", "Pituitary Tumor"]
CLASS_DESCRIPTIONS = {
    "Healthy / No Tumor": "No pathological mass effect or abnormal hyperintensity observed in parenchyma.",
    "Glioma": "Infiltrative neuroepithelial primary brain tumor arising from glial tissue, characteristically displaying heterogeneous core and diffuse edema boundaries.",
    "Meningioma": "Extra-axial tumor arising from arachnoid cap cells, typically showing well-circumscribed, homogeneous enhancement and dural tail sign.",
    "Pituitary Tumor": "Neuroendocrine neoplasm situated in the sella turcica, commonly microadenoma or macroadenoma with suprasellar extension."
}

# Image Preprocessing & Model Specifications
IMAGE_SIZE = (224, 224)
SEGMENTATION_SIZE = (224, 224)
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]

# Standard Clinical MRI Voxel Specifications
DEFAULT_PIXEL_SPACING_MM = (0.9375, 0.9375)  # In-plane resolution (dx, dy)
DEFAULT_SLICE_THICKNESS_MM = 3.0             # Slice thickness (dz)

# Longitudinal RANO / RECIST Response Criteria Thresholds
RANO_CRITERIA = {
    "COMPLETE_RESPONSE": "Complete disappearance of all enhancing measurable and nonmeasurable lesions.",
    "PARTIAL_RESPONSE": ">= 50% decrease in the sum of products of perpendicular diameters or >= 50% volumetric reduction.",
    "STABLE_DISEASE": "Does not qualify for Complete Response, Partial Response, or Progression (< 25% increase, < 50% decrease).",
    "PROGRESSIVE_DISEASE": ">= 25% increase in lesion volume/area or appearance of new lesions."
}

# Server Settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
