"""Longitudinal Assessment & Temporal Follow-up Analysis Engine.
Calculates 2D RANO-inspired perpendicular product change between baseline (P0) and follow-up (P1):
  %ΔP = (P1 - P0) / P0 * 100

Response Criteria:
- Complete Response (CR): Follow-up mask is empty (0 pixels) while baseline was non-empty.
- Partial Response (PR): %ΔP <= -50% (at least 50% reduction in perpendicular product).
- Progressive Disease (PD): %ΔP >= +25% (at least 25% enlargement in perpendicular product).
- Stable Disease (SD): Neither PR nor PD criteria met (-50% < %ΔP < +25%).

Output provides neutral imaging notes without clinical diagnosis claims.
Includes chromatic spatial difference maps (Green = Regression, Red = Progression, Yellow = Stable).
"""
from typing import Dict, Tuple, Optional
import numpy as np
import cv2


class LongitudinalAnalyzer:

    @staticmethod
    def compare_timepoints(baseline_metrics: dict, followup_metrics: dict, days_between: int = 90) -> dict:
        """Compares baseline and follow-up measurements via RANO-inspired 2D product criteria."""
        # Use physical product (product_mm2) if available, otherwise pixel product (product_px2)
        use_mm = (
            baseline_metrics.get("product_mm2") is not None
            and followup_metrics.get("product_mm2") is not None
        )
        if use_mm:
            p0 = float(baseline_metrics["product_mm2"])
            p1 = float(followup_metrics["product_mm2"])
            units = "mm²"
        else:
            p0 = float(baseline_metrics.get("product_px2", 0.0))
            p1 = float(followup_metrics.get("product_px2", 0.0))
            units = "px²"

        n0 = int(baseline_metrics.get("pixel_count", 0))
        n1 = int(followup_metrics.get("pixel_count", 0))

        delta_p = p1 - p0

        # Response classification
        if n0 > 0 and n1 == 0:
            category = "CR"
            response_name = "Complete Response (CR)"
            pct_change_p = -100.0
            trend = "Resolution"
            color_theme = "emerald"
            summary = "Complete disappearance of measurable lesion on follow-up imaging."
        elif p0 > 0:
            pct_change_p = float((delta_p / p0) * 100.0)
            if pct_change_p <= -50.0:
                category = "PR"
                response_name = "Partial Response (PR)"
                trend = "Regression"
                color_theme = "blue"
                summary = f"Significant lesion regression ({abs(pct_change_p):.1f}% reduction in perpendicular product)."
            elif pct_change_p >= 25.0:
                category = "PD"
                response_name = "Progressive Disease (PD)"
                trend = "Progression"
                color_theme = "red"
                summary = f"Lesion progression (+{pct_change_p:.1f}% increase in perpendicular product)."
            else:
                category = "SD"
                response_name = "Stable Disease (SD)"
                trend = "Stable"
                color_theme = "amber"
                summary = f"Lesion dimension remains stable ({pct_change_p:+.1f}% perpendicular product change)."
        else:
            if p1 > 0:
                category = "PD"
                response_name = "Progressive Disease (PD)"
                pct_change_p = 100.0
                trend = "Progression"
                color_theme = "red"
                summary = "New measurable lesion detected on follow-up examination."
            else:
                category = "CR"
                response_name = "Complete Response (CR)"
                pct_change_p = 0.0
                trend = "Stable"
                color_theme = "emerald"
                summary = "No measurable lesion present at either examination."

        return {
            "days_between": days_between,
            "category": category,
            "response_category": category,
            "response_name": response_name,
            "percent_change_product": pct_change_p,
            "pct_change_product": pct_change_p,
            "delta_product": delta_p,
            "product_units": units,
            "baseline_product": p0,
            "followup_product": p1,
            "trend": trend,
            "color_theme": color_theme,
            "summary": summary,
            "framework": "RANO-inspired imaging response",
            "neutral_note": "Imaging change only; clinical RANO also considers steroid dose and neurological status.",
            "note": "Imaging change only; clinical RANO also considers steroid dose and neurological status.",
            "disclaimer": "Academic decision-support prototype — not for clinical diagnosis.",
        }

    @staticmethod
    def generate_difference_map(
        baseline_gray: np.ndarray,
        baseline_mask: np.ndarray,
        followup_mask: np.ndarray,
    ) -> np.ndarray:
        """Generates chromatic subtraction / spatial difference map:
        - Green (0, 230, 115): Tumor regression / shrinkage (in baseline but not followup)
        - Red (234, 67, 53): Tumor progression / growth (in followup but not baseline)
        - Yellow (251, 188, 4): Stable tumor area (in both baseline and followup)
        """
        b_mask = baseline_mask > 0.5
        f_mask = followup_mask > 0.5

        if baseline_gray.ndim == 2:
            base_rgb = cv2.cvtColor(baseline_gray, cv2.COLOR_GRAY2RGB)
        else:
            base_rgb = baseline_gray.copy()

        diff_vis = base_rgb.copy()

        # Stable region: yellow (251, 188, 4)
        stable = b_mask & f_mask
        diff_vis[stable] = [251, 188, 4]

        # Regressed region: green (0, 230, 115)
        regressed = b_mask & ~f_mask
        diff_vis[regressed] = [0, 230, 115]

        # Progressed region: red (234, 67, 53)
        progressed = ~b_mask & f_mask
        diff_vis[progressed] = [234, 67, 53]

        # Blend with base image
        result = cv2.addWeighted(base_rgb, 0.45, diff_vis, 0.55, 0)
        return result

    @classmethod
    def generate_longitudinal_delta_map(cls, baseline_mask: np.ndarray, followup_mask: np.ndarray, baseline_gray: np.ndarray = None):
        """Generates difference map as PIL Image."""
        from PIL import Image
        h, w = baseline_mask.shape[:2]
        if baseline_gray is None:
            baseline_gray = np.zeros((h, w), dtype=np.uint8)
        diff_rgb = cls.generate_difference_map(baseline_gray, baseline_mask, followup_mask)
        return Image.fromarray(diff_rgb)

