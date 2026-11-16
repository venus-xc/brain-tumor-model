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
    assert data["models_loaded"] is True

def test_samples_endpoint(client):
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert "glioma" in data
    assert "normal" in data
    assert "longitudinal_pair" in data

def test_predict_sample(client):
    response = client.post("/api/predict", data={"sample_key": "glioma", "gradcam_alpha": 0.45})
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "segmentation" in data
    assert "quantitative_metrics" in data
    assert "visualizations" in data
    assert data["prediction"]["label"] == "Glioma"

def test_longitudinal_endpoint(client):
    response = client.post("/api/longitudinal", data={
        "baseline_sample": "longitudinal_baseline",
        "followup_sample": "longitudinal_followup",
        "days_between": 90
    })
    assert response.status_code == 200
    data = response.json()
    assert "comparison" in data
    assert "delta_volume_cm3" in data["comparison"]
    assert data["comparison"]["response_code"] in ["PARTIAL_RESPONSE", "COMPLETE_RESPONSE"]

def test_report_generation(client):
    response = client.post("/api/report", data={
        "patient_name": "Test Patient",
        "patient_id": "TEST-101",
        "age_gender": "45 / M",
        "sample_key": "glioma",
        "include_longitudinal": True
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "download_url" in data
    
    # Test download
    dl_res = client.get(data["download_url"])
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 1000  # Non-trivial PDF size
