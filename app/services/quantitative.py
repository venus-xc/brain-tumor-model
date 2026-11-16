import math
import numpy as np
from scipy import ndimage
from app.config import DEFAULT_PIXEL_SPACING_MM, DEFAULT_SLICE_THICKNESS_MM

class QuantitativeAnalyzer:
    """
    Computes rigorous clinical morphometrics, geometry, and volumetric estimations
    from predicted tumor segmentation masks and MRI intensity data.
    """

    def __init__(self, pixel_spacing=DEFAULT_PIXEL_SPACING_MM, slice_thickness=DEFAULT_SLICE_THICKNESS_MM):
        self.dx, self.dy = pixel_spacing  # mm per pixel
        self.dz = slice_thickness         # mm slice thickness
        self.pixel_area_mm2 = self.dx * self.dy
        self.voxel_volume_mm3 = self.pixel_area_mm2 * self.dz

    def compute_morphometrics(self, binary_mask: np.ndarray, original_gray: np.ndarray = None) -> dict:
        """
        Calculates geometric and intensity metrics from 2D binary segmentation mask.
        binary_mask: 2D numpy array with values in {0, 1} or booleans.
        original_gray: 2D numpy array [0, 255] for intensity analysis.
        """
        mask_bool = binary_mask > 0.5
        pixel_count = int(np.sum(mask_bool))
        
        # If no tumor detected (e.g., Healthy brain scan)
        if pixel_count == 0:
            return {
                "tumor_detected": False,
                "pixel_count": 0,
                "surface_area_mm2": 0.0,
                "surface_area_cm2": 0.0,
                "estimated_volume_mm3": 0.0,
                "estimated_volume_cm3": 0.0,
                "equivalent_diameter_mm": 0.0,
                "major_axis_mm": 0.0,
                "minor_axis_mm": 0.0,
                "perimeter_mm": 0.0,
                "sphericity_index": 0.0,
                "centroid_px": (0, 0),
                "intensity_stats": {
                    "mean": 0.0,
                    "std": 0.0,
                    "min": 0.0,
                    "max": 0.0
                },
                "clinical_stage_estimate": "T0 (No measurable lesion detected)"
            }

        # 1. Surface Area
        area_mm2 = pixel_count * self.pixel_area_mm2
        area_cm2 = area_mm2 / 100.0
        
        # 2. Volumetric Estimation (Slice extrusion approximation / standard MRI slice modeling)
        # For single 2D representative slice, Volume ~ Area * slice_thickness * sphere_correction_factor (4/3 * sqrt(A/pi) / (2/3))
        # Standard clinical single-slice approximation uses Area * slice_thickness or spherical equivalent
        volume_mm3 = area_mm2 * self.dz
        volume_cm3 = volume_mm3 / 1000.0

        # 3. Equivalent Circular Diameter
        equivalent_diameter_mm = 2.0 * math.sqrt(area_mm2 / math.pi)

        # 4. Centroid
        labeled, num_features = ndimage.label(mask_bool)
        cy, cx = ndimage.center_of_mass(mask_bool)
        
        # 5. Moments & Major/Minor Axes
        y_indices, x_indices = np.where(mask_bool)
        x_centered = (x_indices - cx) * self.dx
        y_centered = (y_indices - cy) * self.dy
        
        # Covariance matrix of coordinates
        coords = np.stack([x_centered, y_centered], axis=0)
        cov = np.cov(coords)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.maximum(eigenvalues, 1e-6)
        
        # 4 * sqrt(eigenvalue) represents 2 standard deviations along principal axes (elliptical approximation)
        major_axis_mm = 4.0 * math.sqrt(max(eigenvalues))
        minor_axis_mm = 4.0 * math.sqrt(min(eigenvalues))

        # 6. Perimeter Calculation via morphological boundary
        eroded = ndimage.binary_erosion(mask_bool)
        boundary = mask_bool ^ eroded
        boundary_pixels = np.sum(boundary)
        perimeter_mm = float(boundary_pixels * ((self.dx + self.dy) / 2.0))

        # 7. Sphericity / Compactness Index (Isoperimetric quotient)
        # 1.0 for perfect circle, lower for irregular/infiltrative borders
        if perimeter_mm > 0:
            sphericity = (4.0 * math.pi * area_mm2) / (perimeter_mm ** 2)
            sphericity = min(1.0, max(0.0, sphericity))
        else:
            sphericity = 0.0

        # 8. Intensity Statistics inside tumor
        intensity_stats = {}
        if original_gray is not None:
            tumor_pixels = original_gray[mask_bool]
            if len(tumor_pixels) > 0:
                intensity_stats = {
                    "mean": float(np.mean(tumor_pixels)),
                    "std": float(np.std(tumor_pixels)),
                    "min": float(np.min(tumor_pixels)),
                    "max": float(np.max(tumor_pixels))
                }
            else:
                intensity_stats = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        # Clinical Size Categorization (similar to RECIST lesion grading)
        if area_cm2 < 1.0:
            stage_estimate = "Small Focal Lesion (< 1.0 cm²)"
        elif area_cm2 < 5.0:
            stage_estimate = "Moderate Sized Mass (1.0 - 5.0 cm²)"
        elif area_cm2 < 12.0:
            stage_estimate = "Large Solitary Mass (5.0 - 12.0 cm²)"
        else:
            stage_estimate = "Extensive Diffuse / Giant Mass (> 12.0 cm²)"

        return {
            "tumor_detected": True,
            "pixel_count": pixel_count,
            "surface_area_mm2": round(area_mm2, 2),
            "surface_area_cm2": round(area_cm2, 3),
            "estimated_volume_mm3": round(volume_mm3, 2),
            "estimated_volume_cm3": round(volume_cm3, 3),
            "equivalent_diameter_mm": round(equivalent_diameter_mm, 2),
            "major_axis_mm": round(major_axis_mm, 2),
            "minor_axis_mm": round(minor_axis_mm, 2),
            "perimeter_mm": round(perimeter_mm, 2),
            "sphericity_index": round(sphericity, 3),
            "centroid_px": (round(float(cx), 1), round(float(cy), 1)),
            "intensity_stats": intensity_stats,
            "clinical_stage_estimate": stage_estimate
        }
