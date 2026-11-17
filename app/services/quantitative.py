"""Quantitative 2D Morphometrics Engine.
Calculates 2D planar lesion measurements:
- area_mm2 = N_pixels * dx * dy (and area_cm2)
- d1_mm: Longest diameter from PCA major-axis extent of mask coordinates
- d2_mm: Longest diameter perpendicular to d1 along PCA minor-axis extent
- product_mm2: d1 * d2 (perpendicular product used in RANO criteria)

Pixel spacing is extracted from DICOM tags or user-supplied pixel_spacing_mm form field.
If not provided, measurements are reported in pixel units only with spacing_source="not provided".
"""
from typing import Optional, Tuple, Union
import numpy as np


class QuantitativeAnalyzer:

    def __init__(self, pixel_spacing: Optional[Union[float, Tuple[float, float]]] = None, spacing_source: Optional[str] = None):
        self.spacing_source = spacing_source
        if pixel_spacing is not None:
            if isinstance(pixel_spacing, (int, float)):
                self.dx = float(pixel_spacing)
                self.dy = float(pixel_spacing)
            else:
                self.dx = float(pixel_spacing[0])
                self.dy = float(pixel_spacing[1])
            self.has_spacing = True
            if not self.spacing_source:
                self.spacing_source = "user_provided"
        else:
            self.dx = None
            self.dy = None
            self.has_spacing = False
            self.spacing_source = "not provided"

    def compute_morphometrics(self, binary_mask: np.ndarray, original_gray: np.ndarray = None) -> dict:
        """Calculates 2D planar dimensions and perpendicular product from binary mask.
        binary_mask: 2D numpy array [H, W] with values in {0, 1} or booleans.
        """
        mask_bool = binary_mask > 0.5
        pixel_count = int(np.sum(mask_bool))

        if pixel_count == 0:
            return {
                "tumor_detected": False,
                "pixel_count": 0,
                "spacing_source": self.spacing_source,
                "pixel_spacing_mm": [self.dx, self.dy] if self.has_spacing else None,
                "area_mm2": 0.0 if self.has_spacing else None,
                "area_cm2": 0.0 if self.has_spacing else None,
                "d1_mm": 0.0 if self.has_spacing else None,
                "d2_mm": 0.0 if self.has_spacing else None,
                "product_mm2": 0.0 if self.has_spacing else None,
                "d1_px": 0.0,
                "d2_px": 0.0,
                "product_px2": 0.0,
                "centroid_px": (0, 0),
                "intensity_stats": {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0},
            }

        Y, X = np.where(mask_bool)
        centroid = (float(np.mean(X)), float(np.mean(Y)))

        # Intensity statistics on grayscale image if provided
        intensity_stats = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        if original_gray is not None:
            vals = original_gray[mask_bool]
            if len(vals) > 0:
                intensity_stats = {
                    "mean": float(np.mean(vals)),
                    "std": float(np.std(vals)),
                    "min": float(np.min(vals)),
                    "max": float(np.max(vals)),
                }

        # PCA for principal diameters (in pixels)
        pts_px = np.stack([X, Y], axis=1).astype(np.float64)
        pts_c_px = pts_px - pts_px.mean(axis=0)

        if len(pts_px) > 1:
            cov = np.cov(pts_c_px, rowvar=False)
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            v1 = eigvecs[:, order[0]]  # Major axis
            v2 = eigvecs[:, order[1]]  # Perpendicular minor axis

            p1_px = pts_c_px @ v1
            p2_px = pts_c_px @ v2
            d1_px = float(p1_px.max() - p1_px.min())
            d2_px = float(p2_px.max() - p2_px.min())
        else:
            d1_px = 1.0
            d2_px = 1.0

        product_px2 = float(d1_px * d2_px)

        # Calibrated metric calculations if spacing is available
        if self.has_spacing:
            pts_mm = np.stack([X * self.dx, Y * self.dy], axis=1).astype(np.float64)
            pts_c_mm = pts_mm - pts_mm.mean(axis=0)
            cov_mm = np.cov(pts_c_mm, rowvar=False)
            eigvals_mm, eigvecs_mm = np.linalg.eigh(cov_mm)
            order_mm = np.argsort(eigvals_mm)[::-1]
            v1_mm = eigvecs_mm[:, order_mm[0]]
            v2_mm = eigvecs_mm[:, order_mm[1]]

            p1_mm = pts_c_mm @ v1_mm
            p2_mm = pts_c_mm @ v2_mm
            d1_mm = float(p1_mm.max() - p1_mm.min())
            d2_mm = float(p2_mm.max() - p2_mm.min())
            area_mm2 = float(pixel_count * self.dx * self.dy)
            area_cm2 = float(area_mm2 / 100.0)
            product_mm2 = float(d1_mm * d2_mm)
        else:
            d1_mm = None
            d2_mm = None
            area_mm2 = None
            area_cm2 = None
            product_mm2 = None

        return {
            "tumor_detected": True,
            "pixel_count": pixel_count,
            "spacing_source": self.spacing_source,
            "pixel_spacing_mm": [self.dx, self.dy] if self.has_spacing else None,
            "area_mm2": area_mm2,
            "area_cm2": area_cm2,
            "d1_mm": d1_mm,
            "d2_mm": d2_mm,
            "product_mm2": product_mm2,
            "d1_px": d1_px,
            "d2_px": d2_px,
            "product_px2": product_px2,
            "centroid_px": centroid,
            "intensity_stats": intensity_stats,
        }
