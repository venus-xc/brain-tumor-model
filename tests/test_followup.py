import pytest
from app.services.longitudinal import LongitudinalAnalyzer


def test_followup_rano_categories():
    # -60% change -> PR
    res_pr = LongitudinalAnalyzer.compare_timepoints(
        baseline_metrics={"product_mm2": 1000.0, "pixel_count": 500},
        followup_metrics={"product_mm2": 400.0, "pixel_count": 200},
    )
    assert res_pr["response_category"] == "PR"

    # -20% change -> SD
    res_sd = LongitudinalAnalyzer.compare_timepoints(
        baseline_metrics={"product_mm2": 1000.0, "pixel_count": 500},
        followup_metrics={"product_mm2": 800.0, "pixel_count": 400},
    )
    assert res_sd["response_category"] == "SD"

    # +30% change -> PD
    res_pd = LongitudinalAnalyzer.compare_timepoints(
        baseline_metrics={"product_mm2": 1000.0, "pixel_count": 500},
        followup_metrics={"product_mm2": 1300.0, "pixel_count": 650},
    )
    assert res_pd["response_category"] == "PD"

    # Empty follow-up -> CR
    res_cr = LongitudinalAnalyzer.compare_timepoints(
        baseline_metrics={"product_mm2": 1000.0, "pixel_count": 500},
        followup_metrics={"product_mm2": 0.0, "pixel_count": 0},
    )
    assert res_cr["response_category"] == "CR"
