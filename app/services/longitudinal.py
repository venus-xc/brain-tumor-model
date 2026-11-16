import numpy as np
from PIL import Image
from app.config import RANO_CRITERIA

class LongitudinalAnalyzer:
    """
    Longitudinal Patient Monitoring and Treatment-Response Assessment Engine.
    Evaluates successive MRI scans (Baseline vs. Follow-up), tracks volumetric
    trajectories, and assigns standardized clinical response categories (RANO/RECIST).
    """

    @staticmethod
    def compare_timepoints(baseline_metrics: dict, followup_metrics: dict, days_between: int = 90) -> dict:
        """
        Compares quantitative metrics between baseline and follow-up examinations.
        """
        v_base = baseline_metrics.get("estimated_volume_cm3", 0.0)
        v_follow = followup_metrics.get("estimated_volume_cm3", 0.0)
        a_base = baseline_metrics.get("surface_area_cm2", 0.0)
        a_follow = followup_metrics.get("surface_area_cm2", 0.0)
        
        delta_v = v_follow - v_base
        delta_a = a_follow - a_base

        if v_base > 0:
            pct_change_v = (delta_v / v_base) * 100.0
            pct_change_a = (delta_a / a_base) * 100.0
        else:
            if v_follow > 0:
                pct_change_v = 100.0
                pct_change_a = 100.0
            else:
                pct_change_v = 0.0
                pct_change_a = 0.0

        # Monthly growth/shrinkage velocity (cm³ per 30 days)
        if days_between > 0:
            growth_velocity_cm3_per_month = (delta_v / days_between) * 30.0
        else:
            growth_velocity_cm3_per_month = 0.0

        # RANO Response Criteria Assessment
        if v_base > 0 and v_follow == 0:
            response_code = "COMPLETE_RESPONSE"
            response_name = "Complete Response (CR)"
            response_summary = "Complete disappearance of the enhancing tumor lesion."
            trend = "Resolution"
            color_theme = "emerald"
        elif pct_change_v <= -50.0:
            response_code = "PARTIAL_RESPONSE"
            response_name = "Partial Response (PR)"
            response_summary = f"Significant tumor regression ({abs(pct_change_v):.1f}% volume reduction). Favorable response to current therapeutic regimen."
            trend = "Regression"
            color_theme = "blue"
        elif pct_change_v >= 25.0:
            response_code = "PROGRESSIVE_DISEASE"
            response_name = "Progressive Disease (PD)"
            response_summary = f"Significant tumor progression (+{pct_change_v:.1f}% volume increase). Indicates treatment refractoriness or disease recurrence."
            trend = "Progression"
            color_theme = "red"
        else:
            response_code = "STABLE_DISEASE"
            response_name = "Stable Disease (SD)"
            response_summary = f"Tumor remains morphologically stable ({pct_change_v:+.1f}% volume variation within acceptable margins)."
            trend = "Stable"
            color_theme = "amber"

        return {
            "days_between": days_between,
            "baseline": {
                "volume_cm3": round(v_base, 3),
                "area_cm2": round(a_base, 3),
                "diameter_mm": baseline_metrics.get("equivalent_diameter_mm", 0.0),
                "detected": baseline_metrics.get("tumor_detected", False)
            },
            "followup": {
                "volume_cm3": round(v_follow, 3),
                "area_cm2": round(a_follow, 3),
                "diameter_mm": followup_metrics.get("equivalent_diameter_mm", 0.0),
                "detected": followup_metrics.get("tumor_detected", False)
            },
            "delta_volume_cm3": round(delta_v, 3),
            "percent_change_volume": round(pct_change_v, 1),
            "delta_area_cm2": round(delta_a, 3),
            "percent_change_area": round(pct_change_a, 1),
            "growth_velocity_cm3_per_month": round(growth_velocity_cm3_per_month, 3),
            "response_category": response_name,
            "response_code": response_code,
            "response_summary": response_summary,
            "criteria_definition": RANO_CRITERIA.get(response_code, ""),
            "trend": trend,
            "color_theme": color_theme
        }

    @staticmethod
    def generate_longitudinal_delta_map(base_mask: np.ndarray, follow_mask: np.ndarray) -> Image.Image:
        """
        Creates an intuitive color-coded spatial difference map:
        - Green: Regressed / Shrunk tumor region (present at baseline, cleared at follow-up)
        - Red: Progressive / New tumor growth region (absent at baseline, newly present at follow-up)
        - Yellow: Persistent tumor core (present at both baseline and follow-up)
        """
        b = base_mask > 0.5
        f = follow_mask > 0.5
        
        h, w = b.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        
        persistent = b & f
        regressed = b & (~f)
        progressed = (~b) & f
        
        # Yellow for persistent core (RGBA: 250, 204, 21, 190)
        rgba[persistent] = [250, 204, 21, 200]
        # Green for regressed tissue (RGBA: 34, 197, 94, 200)
        rgba[regressed] = [34, 197, 94, 200]
        # Red for progressed/growth tissue (RGBA: 239, 68, 68, 200)
        rgba[progressed] = [239, 68, 68, 200]
        
        return Image.fromarray(rgba, mode="RGBA")
