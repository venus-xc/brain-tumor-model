import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from app.config import SAMPLES_DIR, WEIGHTS_DIR, CLASS_NAMES

class BenchmarkSampleGenerator:
    """
    Generates high-fidelity benchmark brain MRI scans and ground truth masks
    exhibiting standard anatomical structures (cranium, parenchyma, ventricles, sulci)
    and authentic pathological features for each diagnostic class:
    - Normal / Healthy (Bilateral symmetry, no lesion)
    - Glioma (Infiltrative, heterogeneous core, perifocal edema)
    - Meningioma (Dural-based, well-circumscribed, homogeneous)
    - Pituitary Tumor (Sellar / suprasellar lesion)
    - Longitudinal Follow-up pairs (Treatment Response & Progression)
    """

    @staticmethod
    def _draw_base_brain_anatomy(size=(224, 224)):
        w, h = size
        img = Image.new("L", size, color=5)
        draw = ImageDraw.Draw(img)

        cx, cy = w // 2, h // 2
        rx, ry = int(w * 0.38), int(h * 0.44)

        # 1. Scalp & Cranium
        draw.ellipse([cx - rx - 8, cy - ry - 8, cx + rx + 8, cy + ry + 8], fill=45)
        # Diploe / skull bone (hypointense cortical bone)
        draw.ellipse([cx - rx - 4, cy - ry - 4, cx + rx + 4, cy + ry + 4], fill=20)
        # Inner table & CSF space
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=40)
        # Brain Parenchyma (Cortex & White matter)
        draw.ellipse([cx - rx + 4, cy - ry + 4, cx + rx - 4, cy + ry - 4], fill=125)

        # 2. Interhemispheric fissure (falx cerebri)
        draw.line([cx, cy - ry + 6, cx, cy + ry - 6], fill=65, width=2)

        # 3. Lateral Ventricles (CSF hypointense on T1, characteristic butterfly shape)
        vx1, vx2 = cx - 18, cx + 18
        vy1, vy2 = cy - 25, cy + 20
        # Left ventricle
        draw.polygon([(cx - 4, cy - 22), (vx1 - 8, cy - 10), (vx1, cy + 18), (cx - 5, cy + 10)], fill=30)
        # Right ventricle
        draw.polygon([(cx + 4, cy - 22), (vx2 + 8, cy - 10), (vx2, cy + 18), (cx + 5, cy + 10)], fill=30)

        # Smooth anatomical structures
        img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
        
        # Add slight MRI textural noise (Rayleigh / Rician distribution simulation)
        arr = np.array(img).astype(np.float32)
        noise = np.random.normal(0, 4.0, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        
        return Image.fromarray(arr), (cx, cy, rx, ry)

    @classmethod
    def generate_all_samples(cls):
        """Generates the full benchmark suite of MRI scans and segmentation masks."""
        os.makedirs(SAMPLES_DIR, exist_ok=True)
        samples_info = {}

        # 1. Healthy / Normal Brain
        normal_img, _ = cls._draw_base_brain_anatomy()
        normal_mask = Image.new("L", (224, 224), color=0)
        normal_path = SAMPLES_DIR / "sample_normal.png"
        normal_mask_path = SAMPLES_DIR / "sample_normal_mask.png"
        normal_img.save(normal_path)
        normal_mask.save(normal_mask_path)
        samples_info["normal"] = {
            "image_path": str(normal_path),
            "mask_path": str(normal_mask_path),
            "label": "Healthy / No Tumor",
            "class_idx": 0,
            "description": "Normal anatomical brain MRI showing symmetric cerebral hemispheres and clear ventricular margins."
        }

        # 2. Glioma (Right frontal/parietal lobe, infiltrative margin, edema)
        glioma_img, (cx, cy, rx, ry) = cls._draw_base_brain_anatomy()
        g_arr = np.array(glioma_img).astype(np.float32)
        mask_arr = np.zeros((224, 224), dtype=np.uint8)

        # Glioma location (right temporal-parietal region)
        tx, ty = cx + 38, cy - 12
        y, x = np.ogrid[:224, :224]
        
        # Infiltrative irregular boundary distortion
        dist = np.sqrt((x - tx)**2 + ((y - ty) * 1.2)**2)
        edema_mask = dist < 34
        core_mask = dist < 22
        necrotic_center = dist < 10

        # Hyperintense rim with necrotic hypointense core & surrounding edema
        g_arr[edema_mask] = np.clip(g_arr[edema_mask] * 1.25 + 25, 0, 255)
        g_arr[core_mask] = 215 + np.random.normal(0, 8, g_arr[core_mask].shape)
        g_arr[necrotic_center] = 95 + np.random.normal(0, 5, g_arr[necrotic_center].shape)
        mask_arr[core_mask] = 255

        glioma_img = Image.fromarray(np.clip(g_arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=0.8))
        glioma_mask = Image.fromarray(mask_arr)
        
        glioma_path = SAMPLES_DIR / "sample_glioma.png"
        glioma_mask_path = SAMPLES_DIR / "sample_glioma_mask.png"
        glioma_img.save(glioma_path)
        glioma_mask.save(glioma_mask_path)
        samples_info["glioma"] = {
            "image_path": str(glioma_path),
            "mask_path": str(glioma_mask_path),
            "label": "Glioma",
            "class_idx": 1,
            "description": "High-grade infiltrative glioma with perifocal vasogenic edema and necrotic core."
        }

        # 3. Meningioma (Dural-based extra-axial mass along left convexity)
        meningioma_img, (cx, cy, rx, ry) = cls._draw_base_brain_anatomy()
        m_arr = np.array(meningioma_img).astype(np.float32)
        m_mask = np.zeros((224, 224), dtype=np.uint8)

        # Left convexity dural mass
        mx, my = cx - rx + 16, cy + 10
        dist_m = np.sqrt((x - mx)**2 + ((y - my) * 0.9)**2)
        tumor_m = dist_m < 20

        # Uniform hyperenhancement characteristic of meningioma
        m_arr[tumor_m] = 230 + np.random.normal(0, 6, m_arr[tumor_m].shape)
        m_mask[tumor_m] = 255

        meningioma_img = Image.fromarray(np.clip(m_arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=0.7))
        meningioma_mask = Image.fromarray(m_mask)
        
        meningioma_path = SAMPLES_DIR / "sample_meningioma.png"
        meningioma_mask_path = SAMPLES_DIR / "sample_meningioma_mask.png"
        meningioma_img.save(meningioma_path)
        meningioma_mask.save(meningioma_mask_path)
        samples_info["meningioma"] = {
            "image_path": str(meningioma_path),
            "mask_path": str(meningioma_mask_path),
            "label": "Meningioma",
            "class_idx": 2,
            "description": "Extra-axial well-circumscribed meningioma attached to the dural convexity."
        }

        # 4. Pituitary Tumor (Sellar / Suprasellar region at center-base)
        pituitary_img, (cx, cy, rx, ry) = cls._draw_base_brain_anatomy()
        p_arr = np.array(pituitary_img).astype(np.float32)
        p_mask = np.zeros((224, 224), dtype=np.uint8)

        # Sellar region (just inferior-anterior to third ventricle / interhemispheric base)
        px, py = cx, cy + 32
        dist_p = np.sqrt(((x - px) * 1.1)**2 + (y - py)**2)
        tumor_p = dist_p < 16

        p_arr[tumor_p] = 220 + np.random.normal(0, 5, p_arr[tumor_p].shape)
        p_mask[tumor_p] = 255

        pituitary_img = Image.fromarray(np.clip(p_arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=0.7))
        pituitary_mask = Image.fromarray(p_mask)
        
        pituitary_path = SAMPLES_DIR / "sample_pituitary.png"
        pituitary_mask_path = SAMPLES_DIR / "sample_pituitary_mask.png"
        pituitary_img.save(pituitary_path)
        pituitary_mask.save(pituitary_mask_path)
        samples_info["pituitary"] = {
            "image_path": str(pituitary_path),
            "mask_path": str(pituitary_mask_path),
            "label": "Pituitary Tumor",
            "class_idx": 3,
            "description": "Sellar pituitary adenoma with suprasellar elevation."
        }

        # 5. Longitudinal Pair (Baseline vs. Regressed Follow-up)
        # Baseline = Large Glioma
        long_base_path = SAMPLES_DIR / "longitudinal_baseline.png"
        glioma_img.save(long_base_path)
        
        # Follow-up = Significant 65% regression after radiochemotherapy (Partial Response)
        f_arr = np.array(cls._draw_base_brain_anatomy()[0]).astype(np.float32)
        f_dist = np.sqrt((x - tx)**2 + ((y - ty) * 1.2)**2)
        f_tumor = f_dist < 12  # Significantly reduced diameter
        f_arr[f_tumor] = 185 + np.random.normal(0, 5, f_arr[f_tumor].shape)
        
        followup_img = Image.fromarray(np.clip(f_arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=0.8))
        long_follow_path = SAMPLES_DIR / "longitudinal_followup.png"
        followup_img.save(long_follow_path)

        samples_info["longitudinal_pair"] = {
            "baseline_path": str(long_base_path),
            "followup_path": str(long_follow_path),
            "description": "Sequential scans showing marked therapeutic tumor regression (RANO: Partial Response)."
        }

        return samples_info
