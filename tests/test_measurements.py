import pytest
import numpy as np
from app.services.quantitative import QuantitativeAnalyzer


def test_circle_measurements():
    r = 30
    spacing = 0.5
    y, x = np.ogrid[:120, :120]
    mask = ((y - 60) ** 2 + (x - 60) ** 2 <= r ** 2).astype(np.uint8)

    analyzer = QuantitativeAnalyzer(pixel_spacing=spacing, spacing_source="test")
    res = analyzer.compute_morphometrics(mask)

    expected_area = np.pi * (r * spacing) ** 2
    expected_d = 2 * r * spacing  # in mm (30.0 mm)

    # Area within 3%
    assert abs(res["area_mm2"] - expected_area) / expected_area < 0.03
    # d1 and d2 within 1 pixel (0.5 mm)
    assert abs(res["d1_mm"] - expected_d) <= 0.5
    assert abs(res["d2_mm"] - expected_d) <= 0.5
    assert res["tumor_detected"] is True
    assert res["product_mm2"] > 0


def test_empty_mask_gives_zeros():
    empty = np.zeros((128, 128), dtype=np.uint8)
    analyzer = QuantitativeAnalyzer(pixel_spacing=0.5, spacing_source="test")
    res = analyzer.compute_morphometrics(empty)

    assert res["tumor_detected"] is False
    assert res["pixel_count"] == 0
    assert res["area_mm2"] == 0.0
    assert res["area_cm2"] == 0.0
    assert res["d1_mm"] == 0.0
    assert res["d2_mm"] == 0.0
    assert res["product_mm2"] == 0.0
    assert res["d1_px"] == 0.0
    assert res["d2_px"] == 0.0
    assert res["product_px2"] == 0.0


def test_no_spacing_provided():
    r = 20
    y, x = np.ogrid[:80, :80]
    mask = ((y - 40) ** 2 + (x - 40) ** 2 <= r ** 2).astype(np.uint8)

    analyzer = QuantitativeAnalyzer(pixel_spacing=None)
    res = analyzer.compute_morphometrics(mask)

    assert res["spacing_source"] == "not provided"
    assert res["area_mm2"] is None
    assert res["d1_mm"] is None
    assert res["d1_px"] > 0
    assert res["product_px2"] > 0
