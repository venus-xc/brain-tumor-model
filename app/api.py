import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import (
    STATIC_DIR, SAMPLES_DIR, REPORTS_DIR, UPLOADS_DIR,
    CLASS_NAMES, CLASS_DESCRIPTIONS, RANO_CRITERIA
)
from app.models.pipeline import BrainTumorInferencePipeline
from app.services.sample_generator import BenchmarkSampleGenerator
from app.services.longitudinal import LongitudinalAnalyzer
from app.services.report_generator import ClinicalReportGenerator
from app.services.ieee_metrics import IEEEMetricsEngine
from app.services.ieee_paper_generator import IEEEPaperGenerator

# Global Pipeline Instance
pipeline = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    print("Initializing Multi-Task Deep Learning Pipeline & Benchmark Dataset...")
    BenchmarkSampleGenerator.generate_all_samples()
    pipeline = BrainTumorInferencePipeline()
    print("Brain Tumor AI System is ready!")
    yield

app = FastAPI(
    title="Brain Tumor AI Diagnostic & Monitoring Workstation",
    description="Multi-task AI system for Brain Tumor Detection, U-Net Segmentation, Grad-CAM XAI & Longitudinal Monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "classes": CLASS_NAMES,
        "descriptions": CLASS_DESCRIPTIONS
    })

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "models_loaded": pipeline is not None,
        "device": str(pipeline.device) if pipeline else "uninitialized",
        "supported_classes": CLASS_NAMES
    }

@app.get("/api/samples")
async def get_sample_scans():
    samples = BenchmarkSampleGenerator.generate_all_samples()
    # Format for frontend
    clean_samples = {}
    for k, v in samples.items():
        if k == "longitudinal_pair":
            clean_samples[k] = {
                "key": k,
                "description": v["description"],
                "baseline_url": f"/static/samples/{Path(v['baseline_path']).name}",
                "followup_url": f"/static/samples/{Path(v['followup_path']).name}"
            }
        else:
            clean_samples[k] = {
                "key": k,
                "label": v["label"],
                "class_idx": v["class_idx"],
                "description": v["description"],
                "image_url": f"/static/samples/{Path(v['image_path']).name}",
                "mask_url": f"/static/samples/{Path(v['mask_path']).name}"
            }
    return clean_samples

@app.post("/api/predict")
async def run_prediction(
    file: UploadFile = None,
    sample_key: str = Form(None),
    gradcam_alpha: float = Form(0.45),
    mask_threshold: float = Form(0.5),
    seg_architecture: str = Form("attention_unet")
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Inference pipeline not initialized.")

    image_source = None
    if file and file.filename:
        # Save temporary upload
        ext = Path(file.filename).suffix or ".png"
        temp_name = f"upload_{uuid.uuid4().hex[:8]}{ext}"
        temp_path = UPLOADS_DIR / temp_name
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        image_source = str(temp_path)
    elif sample_key:
        samples = BenchmarkSampleGenerator.generate_all_samples()
        if sample_key in samples:
            image_source = samples[sample_key]["image_path"]
        elif sample_key == "baseline":
            image_source = samples["longitudinal_pair"]["baseline_path"]
        elif sample_key == "followup":
            image_source = samples["longitudinal_pair"]["followup_path"]
        else:
            raise HTTPException(status_code=400, detail=f"Sample key '{sample_key}' not found.")
    else:
        raise HTTPException(status_code=400, detail="Either an uploaded file or sample_key must be supplied.")

    try:
        results = pipeline.run_full_inference(
            image_source,
            gradcam_alpha=gradcam_alpha,
            mask_threshold=mask_threshold,
            seg_architecture=seg_architecture
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@app.post("/api/longitudinal")
async def run_longitudinal_assessment(
    baseline_file: UploadFile = None,
    baseline_sample: str = Form(None),
    followup_file: UploadFile = None,
    followup_sample: str = Form(None),
    days_between: int = Form(90)
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Inference pipeline not initialized.")

    samples = BenchmarkSampleGenerator.generate_all_samples()
    
    # Resolve baseline source
    if baseline_file and baseline_file.filename:
        base_path = UPLOADS_DIR / f"base_{uuid.uuid4().hex[:8]}.png"
        with open(base_path, "wb") as f:
            shutil.copyfileobj(baseline_file.file, f)
        base_src = str(base_path)
    elif baseline_sample:
        if baseline_sample == "baseline" or baseline_sample == "longitudinal_baseline":
            base_src = samples["longitudinal_pair"]["baseline_path"]
        elif baseline_sample in samples:
            base_src = samples[baseline_sample]["image_path"]
        else:
            base_src = samples["longitudinal_pair"]["baseline_path"]
    else:
        base_src = samples["longitudinal_pair"]["baseline_path"]

    # Resolve followup source
    if followup_file and followup_file.filename:
        follow_path = UPLOADS_DIR / f"follow_{uuid.uuid4().hex[:8]}.png"
        with open(follow_path, "wb") as f:
            shutil.copyfileobj(followup_file.file, f)
        follow_src = str(follow_path)
    elif followup_sample:
        if followup_sample == "followup" or followup_sample == "longitudinal_followup":
            follow_src = samples["longitudinal_pair"]["followup_path"]
        elif followup_sample in samples:
            follow_src = samples[followup_sample]["image_path"]
        else:
            follow_src = samples["longitudinal_pair"]["followup_path"]
    else:
        follow_src = samples["longitudinal_pair"]["followup_path"]

    try:
        # Run inference on both scans
        res_base = pipeline.run_full_inference(base_src)
        res_follow = pipeline.run_full_inference(follow_src)

        # Longitudinal comparison
        comparison = LongitudinalAnalyzer.compare_timepoints(
            res_base["quantitative_metrics"],
            res_follow["quantitative_metrics"],
            days_between=days_between
        )

        import numpy as np
        b_mask = np.array(res_base["segmentation"]["raw_mask"])
        f_mask = np.array(res_follow["segmentation"]["raw_mask"])
        delta_map_pil = LongitudinalAnalyzer.generate_longitudinal_delta_map(b_mask, f_mask)
        from app.services.preprocessor import MedicalImagePreprocessor
        delta_map_b64 = MedicalImagePreprocessor.pil_to_base64(delta_map_pil)

        return {
            "comparison": comparison,
            "baseline_result": res_base,
            "followup_result": res_follow,
            "delta_map_base64": delta_map_b64
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Longitudinal evaluation error: {str(e)}")

@app.post("/api/report")
async def generate_report_endpoint(
    patient_name: str = Form("John Doe"),
    patient_id: str = Form("PT-2026-901"),
    age_gender: str = Form("45 / M"),
    sample_key: str = Form("glioma"),
    include_longitudinal: bool = Form(False)
):
    global pipeline
    if pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline not initialized.")

    samples = BenchmarkSampleGenerator.generate_all_samples()
    src = samples.get(sample_key, samples["glioma"])["image_path"]
    inf_res = pipeline.run_full_inference(src)

    long_res = None
    if include_longitudinal:
        base_src = samples["longitudinal_pair"]["baseline_path"]
        follow_src = samples["longitudinal_pair"]["followup_path"]
        inf_base = pipeline.run_full_inference(base_src)
        inf_follow = pipeline.run_full_inference(follow_src)
        long_res = LongitudinalAnalyzer.compare_timepoints(
            inf_base["quantitative_metrics"],
            inf_follow["quantitative_metrics"],
            days_between=90
        )

    patient_info = {
        "patient_name": patient_name,
        "patient_id": patient_id,
        "age_gender": age_gender,
        "referring_physician": "Dr. S. K. Mohapatra, MD (Neuro-Oncology)",
        "modality": "Brain MRI T1-CE Axial 3.0mm",
        "exam_date": "November 16, 2026 - 14:30"
    }

    report_file_path = ClinicalReportGenerator.generate_pdf_report(
        inference_result=inf_res,
        longitudinal_result=long_res,
        patient_info=patient_info
    )

    filename = Path(report_file_path).name
    return {
        "status": "success",
        "filename": filename,
        "download_url": f"/api/report/download/{filename}"
    }

@app.get("/api/report/download/{filename}")
@app.head("/api/report/download/{filename}")
async def download_report_file(filename: str):
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report file does not exist.")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/pdf"
    )

# ==================== IEEE RESEARCH & BENCHMARK ENDPOINTS ====================

@app.get("/api/ieee/metrics")
async def get_ieee_metrics():
    """Returns comprehensive IEEE benchmark metrics, confusion matrix, ROC curves, and SOTA comparison."""
    metrics = IEEEMetricsEngine.compute_comprehensive_metrics()
    metrics["literature_baselines"] = IEEEMetricsEngine.get_benchmark_comparison()
    return metrics

@app.get("/api/ieee/paper/download")
@app.head("/api/ieee/paper/download")
async def download_ieee_paper():
    """Generates and serves the official 2-Column IEEE Conference Paper PDF."""
    pdf_path = IEEEPaperGenerator.generate_ieee_paper_pdf()
    return FileResponse(
        path=pdf_path,
        filename="IEEE_Conference_Paper_Brain_Tumor.pdf",
        media_type="application/pdf"
    )

@app.get("/api/ieee/latex/download")
@app.head("/api/ieee/latex/download")
async def download_ieee_latex():
    """Serves the complete LaTeX manuscript source code."""
    tex_path = Path(__file__).resolve().parent.parent / "paper" / "IEEE_Brain_Tumor_Research_Paper.tex"
    if not tex_path.exists():
        raise HTTPException(status_code=404, detail="LaTeX manuscript not found.")
    return FileResponse(
        path=str(tex_path),
        filename="IEEE_Brain_Tumor_Research_Paper.tex",
        media_type="text/x-tex"
    )

@app.get("/api/ieee/report/download")
@app.head("/api/ieee/report/download")
async def download_ieee_report():
    """Serves the complete University Seminar & Major Project Thesis Report."""
    md_path = Path(__file__).resolve().parent.parent / "paper" / "FINAL_SEMINAR_REPORT_OUTR.md"
    if not md_path.exists():
        md_path = Path(__file__).resolve().parent.parent / "paper" / "IEEE_Seminar_Project_Report.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Project report not found.")
    return FileResponse(
        path=str(md_path),
        filename="FINAL_SEMINAR_REPORT_OUTR.md",
        media_type="text/markdown"
    )

@app.get("/api/report/final/docx")
@app.head("/api/report/final/docx")
async def download_final_report_docx():
    """Serves the official formatted OUTR Seminar Report Word document (.docx)."""
    docx_path = Path(__file__).resolve().parent.parent / "paper" / "FINAL_SEMINAR_REPORT_OUTR.docx"
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="OUTR Seminar Report Word document not found.")
    return FileResponse(
        path=str(docx_path),
        filename="FINAL_SEMINAR_REPORT_OUTR.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@app.get("/api/report/final/pdf")
@app.head("/api/report/final/pdf")
async def download_final_report_pdf():
    """Serves the official formatted OUTR Seminar Report PDF (.pdf)."""
    pdf_path = Path(__file__).resolve().parent.parent / "paper" / "FINAL_SEMINAR_REPORT_OUTR.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="OUTR Seminar Report PDF not found.")
    return FileResponse(
        path=str(pdf_path),
        filename="FINAL_SEMINAR_REPORT_OUTR.pdf",
        media_type="application/pdf"
    )

