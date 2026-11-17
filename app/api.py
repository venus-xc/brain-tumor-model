"""FastAPI Application Server for Brain Tumor Academic Prototype.
Provides REST API endpoints for:
- 4-class Classification: HOG+SVM, Custom CNN, SE-CNN, EfficientNet-B0
- Lesion Segmentation: Biomedical U-Net, Attention U-Net
- Dual XAI: Grad-CAM and Grad-CAM++
- Quantitative 2D morphometrics (area, d1, d2, product)
- RANO longitudinal response assessment
- Academic PDF report generation
- Real evaluated metrics from results/
"""
import json
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    STATIC_DIR,
    SAMPLES_DIR,
    REPORTS_DIR,
    UPLOADS_DIR,
    PROJECT_ROOT,
    CLASS_NAMES,
    CLASS_DESCRIPTIONS,
    ACADEMIC_DISCLAIMER,
)
from app.models.pipeline import (
    BrainTumorInferencePipeline,
    MODEL_DISPLAY_NAMES,
    SEG_DISPLAY_NAMES,
)
from app.services.longitudinal import LongitudinalAnalyzer
from app.services.report_generator import ClinicalReportGenerator
from app.services.preprocessor import MedicalImagePreprocessor

pipeline: Optional[BrainTumorInferencePipeline] = None

# Verified Real MRI Benchmark Samples (8 classification, 2 segmentation, 1 longitudinal pair)
REAL_SAMPLES_CATALOG = {
    "normal": {
        "key": "normal",
        "label": "No tumor",
        "class_idx": 0,
        "description": "Axial T1 MRI - Normal brain parenchyma without focal lesion (Sartaj test split)",
        "image_url": "/static/samples/sample_normal.png",
        "mask_url": "/static/samples/sample_normal_mask.png",
        "image_path": str(SAMPLES_DIR / "sample_normal.png"),
    },
    "glioma": {
        "key": "glioma",
        "label": "Glioma",
        "class_idx": 1,
        "description": "Axial T1-CE MRI - Infiltrative intra-axial glioma lesion (Sartaj test split)",
        "image_url": "/static/samples/sample_glioma.png",
        "mask_url": "/static/samples/sample_glioma_mask.png",
        "image_path": str(SAMPLES_DIR / "sample_glioma.png"),
    },
    "meningioma": {
        "key": "meningioma",
        "label": "Meningioma",
        "class_idx": 2,
        "description": "Axial T1-CE MRI - Dural-based extra-axial meningioma (Sartaj test split)",
        "image_url": "/static/samples/sample_meningioma.png",
        "mask_url": "/static/samples/sample_meningioma_mask.png",
        "image_path": str(SAMPLES_DIR / "sample_meningioma.png"),
    },
    "pituitary": {
        "key": "pituitary",
        "label": "Pituitary",
        "class_idx": 3,
        "description": "Coronal/Axial MRI - Sellar/parasellar pituitary adenoma (Sartaj test split)",
        "image_url": "/static/samples/sample_pituitary.png",
        "mask_url": "/static/samples/sample_pituitary_mask.png",
        "image_path": str(SAMPLES_DIR / "sample_pituitary.png"),
    },
    "figshare_1": {
        "key": "figshare_1",
        "label": "Meningioma",
        "class_idx": 2,
        "description": "Patient test slice with ground truth boundary (Figshare test patient #3381)",
        "image_url": "/static/samples/figshare_test_1.png",
        "mask_url": "/static/samples/figshare_test_1_mask.png",
        "image_path": str(SAMPLES_DIR / "figshare_test_1.png"),
    },
    "figshare_2": {
        "key": "figshare_2",
        "label": "Glioma",
        "class_idx": 1,
        "description": "Patient test slice with ground truth boundary (Figshare test patient #3394)",
        "image_url": "/static/samples/figshare_test_2.png",
        "mask_url": "/static/samples/figshare_test_2_mask.png",
        "image_path": str(SAMPLES_DIR / "figshare_test_2.png"),
    },
    "longitudinal_pair": {
        "key": "longitudinal_pair",
        "description": "Paired baseline and follow-up examinations for RANO response monitoring",
        "baseline_url": "/static/samples/longitudinal_baseline.png",
        "followup_url": "/static/samples/longitudinal_followup.png",
        "baseline_path": str(SAMPLES_DIR / "longitudinal_baseline.png"),
        "followup_path": str(SAMPLES_DIR / "longitudinal_followup.png"),
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    print("Initializing Multi-Task Deep Learning Pipeline...")
    pipeline = BrainTumorInferencePipeline()
    print("Brain Tumor AI System is ready!")
    yield


app = FastAPI(
    title="Brain Tumor Academic Decision-Support System",
    description="Multi-task AI system for Brain Tumor Detection, U-Net Segmentation, Grad-CAM XAI & Longitudinal Monitoring (Academic Prototype)",
    version="2.0.0",
    lifespan=lifespan,
)

# Static and Templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
async def index_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "classes": CLASS_NAMES,
            "descriptions": CLASS_DESCRIPTIONS,
            "models": MODEL_DISPLAY_NAMES,
            "seg_models": SEG_DISPLAY_NAMES,
            "disclaimer": ACADEMIC_DISCLAIMER,
        },
    )


@app.get("/api/health")
async def health_check():
    loaded_status = pipeline.get_loaded_models() if pipeline else {}
    return {
        "status": "healthy",
        "models_loaded": loaded_status,
        "device": str(pipeline.device) if pipeline else "uninitialized",
        "supported_classes": CLASS_NAMES,
        "disclaimer": ACADEMIC_DISCLAIMER,
    }


@app.get("/api/samples")
async def get_sample_scans():
    return REAL_SAMPLES_CATALOG


@app.post("/api/predict")
async def run_prediction(
    file: UploadFile = None,
    sample_key: str = Form(None),
    classifier: str = Form("effb0"),
    seg_architecture: str = Form("attunet"),
    mask_threshold: float = Form(0.5),
    gradcam_alpha: float = Form(0.45),
    pixel_spacing_mm: Optional[float] = Form(None),
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Inference pipeline not initialized.")

    image_source = None
    spacing_source = None
    if pixel_spacing_mm is not None and pixel_spacing_mm > 0:
        spacing_source = f"user_provided ({pixel_spacing_mm:.4f} mm)"

    if file and file.filename:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix or ".png"
        temp_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"
        temp_path = UPLOADS_DIR / temp_name
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_source = str(temp_path)
    elif sample_key:
        if sample_key in REAL_SAMPLES_CATALOG:
            image_source = REAL_SAMPLES_CATALOG[sample_key].get("image_path")
        elif sample_key == "baseline":
            image_source = REAL_SAMPLES_CATALOG["longitudinal_pair"]["baseline_path"]
        elif sample_key == "followup":
            image_source = REAL_SAMPLES_CATALOG["longitudinal_pair"]["followup_path"]
        else:
            raise HTTPException(status_code=400, detail=f"Sample key '{sample_key}' not found.")
    else:
        raise HTTPException(status_code=400, detail="Either an uploaded file or sample_key must be supplied.")

    try:
        results = pipeline.run_full_inference(
            image_source,
            classifier=classifier,
            seg_architecture=seg_architecture,
            mask_threshold=mask_threshold,
            gradcam_alpha=gradcam_alpha,
            pixel_spacing_mm=pixel_spacing_mm,
            spacing_source=spacing_source,
        )
        return results
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=503, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


@app.post("/api/longitudinal")
async def run_longitudinal_assessment(
    baseline_file: UploadFile = None,
    baseline_sample: str = Form(None),
    followup_file: UploadFile = None,
    followup_sample: str = Form(None),
    classifier: str = Form("effb0"),
    seg_architecture: str = Form("attunet"),
    pixel_spacing_mm: Optional[float] = Form(None),
    days_between: int = Form(90),
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Inference pipeline not initialized.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve baseline source
    if baseline_file and baseline_file.filename:
        base_path = UPLOADS_DIR / f"base_{uuid.uuid4().hex[:8]}.png"
        with open(base_path, "wb") as f:
            shutil.copyfileobj(baseline_file.file, f)
        base_src = str(base_path)
    elif baseline_sample in ["longitudinal_pair", "baseline", "longitudinal_baseline"]:
        base_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["baseline_path"]
    elif baseline_sample and baseline_sample in REAL_SAMPLES_CATALOG:
        base_src = REAL_SAMPLES_CATALOG[baseline_sample].get("image_path")
    else:
        base_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["baseline_path"]

    # Resolve followup source
    if followup_file and followup_file.filename:
        follow_path = UPLOADS_DIR / f"follow_{uuid.uuid4().hex[:8]}.png"
        with open(follow_path, "wb") as f:
            shutil.copyfileobj(followup_file.file, f)
        follow_src = str(follow_path)
    elif followup_sample in ["longitudinal_pair", "followup", "longitudinal_followup"]:
        follow_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["followup_path"]
    elif followup_sample and followup_sample in REAL_SAMPLES_CATALOG:
        follow_src = REAL_SAMPLES_CATALOG[followup_sample].get("image_path")
    else:
        follow_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["followup_path"]

    spacing_src = f"user_provided ({pixel_spacing_mm:.4f} mm)" if pixel_spacing_mm else None

    try:
        res_base = pipeline.run_full_inference(
            base_src,
            classifier=classifier,
            seg_architecture=seg_architecture,
            pixel_spacing_mm=pixel_spacing_mm,
            spacing_source=spacing_src,
        )
        res_follow = pipeline.run_full_inference(
            follow_src,
            classifier=classifier,
            seg_architecture=seg_architecture,
            pixel_spacing_mm=pixel_spacing_mm,
            spacing_source=spacing_src,
        )

        comparison = LongitudinalAnalyzer.compare_timepoints(
            res_base["quantitative_metrics"],
            res_follow["quantitative_metrics"],
            days_between=days_between,
        )

        import numpy as np
        b_mask = np.array(res_base["segmentation"]["raw_mask"])
        f_mask = np.array(res_follow["segmentation"]["raw_mask"])
        delta_map_pil = LongitudinalAnalyzer.generate_longitudinal_delta_map(b_mask, f_mask)
        delta_map_b64 = MedicalImagePreprocessor.pil_to_base64(delta_map_pil)

        return {
            "comparison": comparison,
            "baseline_result": res_base,
            "followup_result": res_follow,
            "delta_map_base64": delta_map_b64,
            "disclaimer": ACADEMIC_DISCLAIMER,
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=503, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Longitudinal evaluation error: {str(e)}")


@app.post("/api/report")
async def generate_report_endpoint(
    patient_name: str = Form("Anonymous Subject"),
    patient_id: str = Form("SUBJ-2026-042"),
    sample_key: str = Form("glioma"),
    classifier: str = Form("effb0"),
    seg_architecture: str = Form("attunet"),
    pixel_spacing_mm: Optional[float] = Form(None),
    include_longitudinal: bool = Form(False),
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized.")

    src = REAL_SAMPLES_CATALOG.get(sample_key, REAL_SAMPLES_CATALOG["glioma"]).get("image_path")
    spacing_src = f"user_provided ({pixel_spacing_mm:.4f} mm)" if pixel_spacing_mm else None

    try:
        inf_res = pipeline.run_full_inference(
            src,
            classifier=classifier,
            seg_architecture=seg_architecture,
            pixel_spacing_mm=pixel_spacing_mm,
            spacing_source=spacing_src,
        )

        long_res = None
        if include_longitudinal:
            base_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["baseline_path"]
            follow_src = REAL_SAMPLES_CATALOG["longitudinal_pair"]["followup_path"]
            inf_base = pipeline.run_full_inference(base_src, classifier=classifier, seg_architecture=seg_architecture)
            inf_follow = pipeline.run_full_inference(follow_src, classifier=classifier, seg_architecture=seg_architecture)
            long_res = LongitudinalAnalyzer.compare_timepoints(
                inf_base["quantitative_metrics"],
                inf_follow["quantitative_metrics"],
                days_between=90,
            )

        patient_info = {
            "patient_name": patient_name,
            "patient_id": patient_id,
            "modality": "Brain MRI T1-CE Axial Slice",
            "exam_date": "Academic Verification Run",
        }

        report_file_path = ClinicalReportGenerator.generate_pdf_report(
            inference_result=inf_res,
            longitudinal_result=long_res,
            patient_info=patient_info,
        )

        filename = Path(report_file_path).name
        return {
            "status": "success",
            "filename": filename,
            "download_url": f"/api/report/download/{filename}",
        }
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=503, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@app.get("/api/report/download/{filename}")
@app.head("/api/report/download/{filename}")
async def download_report_file(filename: str):
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report file does not exist.")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf",
    )


@app.get("/api/metrics")
async def get_metrics():
    """Returns measured metrics from results/ directory without fabrication."""
    results_dir = Path(PROJECT_ROOT) / "results"
    output = {
        "disclaimer": ACADEMIC_DISCLAIMER,
        "models": {},
        "segmentation": {},
        "leakage": {},
        "clean_split": {},
    }

    # Load metrics.json if generated
    metrics_path = results_dir / "metrics.json"
    if metrics_path.exists():
        try:
            with open(metrics_path, "r") as f:
                output["models"] = json.load(f)
        except Exception:
            pass

    # Load segmentation.json
    seg_path = results_dir / "segmentation.json"
    if seg_path.exists():
        try:
            with open(seg_path, "r") as f:
                output["segmentation"] = json.load(f)
        except Exception:
            pass

    # Load leakage.json
    leak_path = results_dir / "leakage.json"
    if leak_path.exists():
        try:
            with open(leak_path, "r") as f:
                output["leakage"] = json.load(f)
        except Exception:
            pass

    # Load clean_split.json
    split_path = results_dir / "clean_split.json"
    if split_path.exists():
        try:
            with open(split_path, "r") as f:
                output["clean_split"] = json.load(f)
        except Exception:
            pass

    return output


@app.get("/api/report/final/docx")
@app.head("/api/report/final/docx")
async def download_final_report_docx():
    """Serves the OUTR Seminar Report Word document (.docx)."""
    paper_dir = Path(PROJECT_ROOT) / "paper"
    for name in ["Final_Report_Brain_Tumor_Detection_OUTR.docx", "FINAL_SEMINAR_REPORT_OUTR.docx", "BRAIN_TUMOR_FINAL_REPORT.docx"]:
        p = paper_dir / name
        if p.exists():
            return FileResponse(path=str(p), filename=name, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    raise HTTPException(status_code=404, detail="Word document report not found.")


@app.get("/api/report/final/pdf")
@app.head("/api/report/final/pdf")
async def download_final_report_pdf():
    """Serves the OUTR Seminar Report PDF (.pdf)."""
    paper_dir = Path(PROJECT_ROOT) / "paper"
    for name in ["Final_Report_Brain_Tumor_Detection_OUTR.pdf", "FINAL_SEMINAR_REPORT_OUTR.pdf"]:
        p = paper_dir / name
        if p.exists():
            return FileResponse(path=str(p), filename=name, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="PDF report not found.")
