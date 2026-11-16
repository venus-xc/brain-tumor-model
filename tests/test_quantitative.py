import pytest
import numpy as np
from app.services.quantitative import QuantitativeAnalyzer
from app.services.longitudinal import LongitudinalAnalyzer

def test_quantitative_empty_mask():
    analyzer = QuantitativeAnalyzer()
    empty_mask = np.zeros((224, 224), dtype=np.uint8)
    metrics = analyzer.compute_morphometrics(empty_mask)
    assert metrics["tumor_detected"] is False
    assert metrics["surface_area_cm2"] == 0.0
    assert metrics["estimated_volume_cm3"] == 0.0
    assert metrics["clinical_stage_estimate"].startswith("T0")

def test_quantitative_circular_lesion():
    analyzer = QuantitativeAnalyzer()
    # Create circular mask of radius 20 pixels
    mask = np.zeros((224, 224), dtype=np.uint8)
    y, x = np.ogrid[:224, :224]
    dist = np.sqrt((x - 112)**2 + (y - 112)**2)
    mask[dist <= 20] = 1
    
    metrics = analyzer.compute_morphometrics(mask)
    assert metrics["tumor_detected"] is True
    assert metrics["surface_area_cm2"] > 0
    assert metrics["estimated_volume_cm3"] > 0
    # Sphericity for a circle should be high (> 0.70)
    assert metrics["sphericity_index"] > 0.70

def test_longitudinal_partial_response():
    base_metrics = {"estimated_volume_cm3": 4.0, "surface_area_cm2": 1.3, "tumor_detected": True}
    follow_metrics = {"estimated_volume_cm3": 1.2, "surface_area_cm2": 0.4, "tumor_detected": True}
    comp = LongitudinalAnalyzer.compare_timepoints(base_metrics, follow_metrics, days_between=90)
    assert comp["response_code"] == "PARTIAL_RESPONSE"
    assert comp["trend"] == "Regression"
    assert comp["percent_change_volume"] == -70.0

def test_longitudinal_progressive_disease():
    base_metrics = {"estimated_volume_cm3": 2.0, "surface_area_cm2": 0.8, "tumor_detected": True}
    follow_metrics = {"estimated_volume_cm3": 3.0, "surface_area_cm2": 1.2, "tumor_detected": True}
    comp = LongitudinalAnalyzer.compare_timepoints(base_metrics, follow_metrics, days_between=60)
    assert comp["response_code"] == "PROGRESSIVE_DISEASE"
    assert comp["trend"] == "Progression"
    assert comp["percent_change_volume"] == 50.0
