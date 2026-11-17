"""Comprehensive End-to-End API Integration Tests.
Tests:
- Health check (device detection & loaded models)
- Real metrics retrieval (/api/metrics)
- Inference (/api/predict) across all 4 classifiers: HOG+SVM, Custom CNN, SE-CNN, EfficientNet-B0
- 2D planar morphometrics with & without pixel calibration
- Longitudinal RANO 2D evaluation (/api/longitudinal)
- Academic PDF Report Generation (/api/report)
"""
import pytest
from fastapi.testclient import TestClient
from app.api import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "device" in data
    assert data["device"] in ["mps", "cuda", "cpu"]
    assert "models_loaded" in data
    assert "Academic decision-support prototype" in data["disclaimer"]


def test_samples_endpoint(client):
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    for key in ["normal", "glioma", "meningioma", "pituitary", "longitudinal_pair"]:
        assert key in data


def test_metrics_endpoint(client):
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "disclaimer" in data
    assert "models" in data
    assert "leakage" in data


@pytest.mark.parametrize("classifier", ["effb0", "secnn", "cnn", "svm"])
def test_predict_all_classifiers(client, classifier):
    response = client.post("/api/predict", data={
        "sample_key": "glioma",
        "classifier": classifier,
        "seg_architecture": "attunet",
        "mask_threshold": 0.5,
        "gradcam_alpha": 0.45,
    })
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "segmentation" in data
    assert "quantitative_metrics" in data
    assert "visualizations" in data

    pred = data["prediction"]
    assert pred["classifier_key"] == classifier
    assert len(pred["distribution"]) == 4
    assert "No tumor" in pred["distribution"]
    assert "Glioma" in pred["distribution"]

    qm = data["quantitative_metrics"]
    assert "d1_px" in qm
    assert "d2_px" in qm
    assert "product_px2" in qm
    assert "volume_cm3" not in qm
    assert "surface_area_cm2" not in qm
    assert "sphericity_index" not in qm

    vis = data["visualizations"]
    assert vis["original_base64"].startswith("data:image/png;base64,")
    assert vis["segmentation_overlay_base64"].startswith("data:image/png;base64,")


def test_predict_with_calibrated_spacing(client):
    response = client.post("/api/predict", data={
        "sample_key": "meningioma",
        "classifier": "effb0",
        "seg_architecture": "attunet",
        "pixel_spacing_mm": 0.9375,
    })
    assert response.status_code == 200
    data = response.json()
    qm = data["quantitative_metrics"]

    assert qm["pixel_spacing_mm"] == [0.9375, 0.9375]
    if qm["pixel_count"] > 0:
        assert qm["area_mm2"] is not None and qm["area_mm2"] > 0
        assert qm["d1_mm"] is not None and qm["d1_mm"] > 0
        assert qm["d2_mm"] is not None and qm["d2_mm"] > 0
        assert qm["product_mm2"] is not None and qm["product_mm2"] > 0


def test_longitudinal_endpoint(client):
    response = client.post("/api/longitudinal", data={
        "baseline_sample": "longitudinal_pair",
        "followup_sample": "longitudinal_pair",
        "classifier": "effb0",
        "seg_architecture": "attunet",
        "pixel_spacing_mm": 0.9375,
        "days_between": 90,
    })
    assert response.status_code == 200
    data = response.json()
    assert "comparison" in data
    assert "delta_map_base64" in data
    assert data["delta_map_base64"].startswith("data:image/png;base64,")

    comp = data["comparison"]
    assert comp["category"] in ["CR", "PR", "SD", "PD"]
    assert "percent_change_product" in comp
    assert "neutral_note" in comp
    assert "Imaging change only" in comp["neutral_note"]


def test_report_generation(client):
    response = client.post("/api/report", data={
        "patient_name": "Test Subject",
        "patient_id": "TEST-2026-001",
        "classifier": "effb0",
        "seg_architecture": "attunet",
        "sample_key": "glioma",
        "pixel_spacing_mm": 0.9375,
        "include_longitudinal": True,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "download_url" in data

    # Verify download
    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert dl_res.content.startswith(b"%PDF-")
    assert len(dl_res.content) > 5000
