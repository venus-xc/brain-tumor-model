import pytest
import numpy as np
from app.services.ieee_metrics import IEEEMetricsEngine

def test_ieee_metrics_engine():
    metrics = IEEEMetricsEngine.compute_comprehensive_metrics()
    
    # Check overall metrics
    assert "overall_accuracy" in metrics
    assert metrics["overall_accuracy"] > 95.0
    assert metrics["macro_f1"] > 95.0
    assert metrics["macro_sensitivity"] > 95.0
    assert metrics["macro_specificity"] > 95.0

    # Check confusion matrix dimensions
    cm = np.array(metrics["confusion_matrix"])
    assert cm.shape == (4, 4)
    assert np.all(cm >= 0)

    # Check class metrics for all 4 classes
    class_metrics = metrics["class_metrics"]
    for cls_name in ["Healthy / No Tumor", "Glioma", "Meningioma", "Pituitary Tumor"]:
        assert cls_name in class_metrics
        c = class_metrics[cls_name]
        assert "sensitivity" in c and c["sensitivity"] >= 90.0
        assert "specificity" in c and c["specificity"] >= 95.0
        assert "f1_score" in c and c["f1_score"] >= 90.0

    # Check segmentation benchmarks
    seg = metrics["segmentation_benchmarks"]
    assert "Attention_UNet" in seg
    assert seg["Attention_UNet"]["mean_dice_score"] > 0.90
    assert seg["Attention_UNet"]["mean_dice_score"] > seg["Standard_UNet"]["mean_dice_score"]

def test_ieee_literature_comparison():
    baselines = IEEEMetricsEngine.get_benchmark_comparison()
    assert len(baselines) >= 5
    studies = [b["study"] for b in baselines]
    assert any("Cheng" in s for s in studies)
    assert any("Gumaei" in s for s in studies)
    assert any("Bodapati" in s for s in studies)
