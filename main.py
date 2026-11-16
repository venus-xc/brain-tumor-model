import argparse
import uvicorn
from app.config import HOST, PORT

def run_server(host=HOST, port=PORT, reload=False):
    print(f"Starting Brain Tumor AI Diagnostic & Monitoring Workstation on http://{host}:{port}")
    uvicorn.run("app.api:app", host=host, port=port, reload=reload)

def run_cli_evaluation():
    print("Running CLI Evaluation on Benchmark MRI Dataset...")
    from app.models.pipeline import BrainTumorInferencePipeline
    from app.services.sample_generator import BenchmarkSampleGenerator
    from app.services.longitudinal import LongitudinalAnalyzer
    from app.services.report_generator import ClinicalReportGenerator

    samples = BenchmarkSampleGenerator.generate_all_samples()
    pipeline = BrainTumorInferencePipeline()

    print("\n--- Diagnostic Classification & Segmentation Results ---")
    for key in ["normal", "glioma", "meningioma", "pituitary"]:
        s = samples[key]
        res = pipeline.run_full_inference(s["image_path"])
        p = res["prediction"]
        q = res["quantitative_metrics"]
        print(f"[{key.upper()}] -> Pred: {p['label']} ({p['confidence_percent']}%) | Tumor Detected: {p['is_tumor_detected']} | Vol: {q['estimated_volume_cm3']} cm³ | Stage: {q['clinical_stage_estimate']}")

    print("\n--- Longitudinal Monitoring Evaluation ---")
    res_base = pipeline.run_full_inference(samples["longitudinal_pair"]["baseline_path"])
    res_follow = pipeline.run_full_inference(samples["longitudinal_pair"]["followup_path"])
    comp = LongitudinalAnalyzer.compare_timepoints(res_base["quantitative_metrics"], res_follow["quantitative_metrics"], days_between=90)
    print(f"Baseline Vol: {comp['baseline']['volume_cm3']} cm³ -> Follow-up Vol: {comp['followup']['volume_cm3']} cm³")
    print(f"Δ Volume: {comp['delta_volume_cm3']} cm³ ({comp['percent_change_volume']}%)")
    print(f"RANO Response: {comp['response_category']} - {comp['response_summary']}")

    print("\n--- Generating Sample Clinical PDF Report ---")
    pdf_path = ClinicalReportGenerator.generate_pdf_report(res_base, comp)
    print(f"Report successfully generated at: {pdf_path}")
    print("\nAll CLI Evaluations Completed Successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brain Tumor AI Diagnostic & Monitoring Workstation")
    parser.add_argument("--host", default=HOST, help="Host address to bind to")
    parser.add_argument("--port", type=int, default=PORT, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable live auto-reload for development")
    parser.add_argument("--evaluate", action="store_true", help="Run benchmark evaluation in CLI mode without starting web server")

    args = parser.parse_args()

    if args.evaluate:
        run_cli_evaluation()
    else:
        run_server(host=args.host, port=args.port, reload=args.reload)
