import io
import base64
import numpy as np
from PIL import Image, ImageOps, ImageEnhance
import torch
import torchvision.transforms as transforms
from app.config import IMAGE_SIZE, NORM_MEAN, NORM_STD

class MedicalImagePreprocessor:
    """
    Standardized MRI image preprocessing pipeline supporting:
    - Format harmonization (RGB / Grayscale / DICOM extract)
    - Contrast Limited Adaptive Enhancement / Intensity rescaling
    - Brain parenchyma localization & background cropping
    - PyTorch tensor conversion & normalization
    """

    def __init__(self, target_size=IMAGE_SIZE):
        self.target_size = target_size
        self.transform = transforms.Compose([
            transforms.Resize(self.target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=NORM_MEAN, std=NORM_STD)
        ])
        self.raw_transform = transforms.Compose([
            transforms.Resize(self.target_size),
            transforms.ToTensor()
        ])

    def load_image(self, file_source):
        """Loads image from bytes, file path, or PIL Image."""
        if isinstance(file_source, (str, bytes)):
            if isinstance(file_source, bytes):
                img = Image.open(io.BytesIO(file_source)).convert("RGB")
            else:
                img = Image.open(file_source).convert("RGB")
        elif isinstance(file_source, Image.Image):
            img = file_source.convert("RGB")
        elif isinstance(file_source, np.ndarray):
            if file_source.dtype != np.uint8:
                file_source = ((file_source - file_source.min()) / (file_source.max() - file_source.min() + 1e-8) * 255).astype(np.uint8)
            img = Image.fromarray(file_source).convert("RGB")
        else:
            raise ValueError(f"Unsupported image source type: {type(file_source)}")
        return img

    def enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Applies adaptive contrast adjustment and auto-leveling."""
        # Auto-contrast to maximize dynamic range of brain parenchyma
        autocontrasted = ImageOps.autocontrast(image, cutoff=1)
        enhancer = ImageEnhance.Contrast(autocontrasted)
        return enhancer.enhance(1.25)

    def crop_brain_parenchyma(self, image: Image.Image, threshold: int = 15) -> Image.Image:
        """Crops black border around the skull/brain tissue."""
        gray = image.convert("L")
        np_gray = np.array(gray)
        mask = np_gray > threshold
        if not np.any(mask):
            return image
        
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        
        # Add safety margin
        pad = 8
        h, w = np_gray.shape
        rmin = max(0, rmin - pad)
        rmax = min(h, rmax + pad)
        cmin = max(0, cmin - pad)
        cmax = min(w, cmax + pad)
        
        cropped = image.crop((cmin, rmin, cmax, rmax))
        return cropped

    def preprocess_for_inference(self, file_source, crop=False, enhance=True):
        """Full pipeline returning PIL image, PyTorch normalized tensor, and raw tensor."""
        img = self.load_image(file_source)
        if crop:
            img = self.crop_brain_parenchyma(img)
        if enhance:
            img = self.enhance_contrast(img)
        
        resized_img = img.resize(self.target_size, Image.Resampling.BILINEAR)
        normalized_tensor = self.transform(resized_img).unsqueeze(0)  # Shape: (1, 3, H, W)
        raw_tensor = self.raw_transform(resized_img).unsqueeze(0)
        
        return {
            "pil_image": resized_img,
            "normalized_tensor": normalized_tensor,
            "raw_tensor": raw_tensor,
            "np_array": np.array(resized_img)
        }

    @staticmethod
    def pil_to_base64(image: Image.Image, format: str = "PNG") -> str:
        """Converts PIL image to base64 data URI."""
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/{format.lower()};base64,{img_str}"

    @staticmethod
    def base64_to_pil(base64_str: str) -> Image.Image:
        """Converts base64 data string to PIL Image."""
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_data = base64.b64decode(base64_str)
        return Image.open(io.BytesIO(img_data)).convert("RGB")
