#!/usr/bin/env bash
# End-to-end training and evaluation script.
# Trains classical models, CNN, SE-CNN, EfficientNet-B0 (clean & official splits),
# and segmentation models (U-Net, Attention U-Net), then generates all figures and metrics.json.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON="${PYTHON:-.venv/bin/python}"
if [ ! -f "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "=========================================="
echo "Starting End-to-End Evaluation Pipeline"
echo "Using Python: $PYTHON"
echo "=========================================="

# Ensure data is acquired and preprocessed
if [ ! -f "data/processed/clean_192.npz" ]; then
    echo "Processing classification dataset..."
    $PYTHON scripts/prepare_classification.py data/raw/sartaj data/processed results
fi

if [ ! -f "data/processed/seg_256.npz" ]; then
    echo "Processing segmentation dataset..."
    $PYTHON scripts/prepare_segmentation.py data/raw/figshare data/processed results
fi

# Ensure data/ symlinks exist for legacy script compatibility
mkdir -p data
cd data
ln -sf processed/clean_192.npz clean_192.npz
ln -sf processed/cache_192.npz cache_192.npz
ln -sf processed/paths.json paths.json
ln -sf ../results/clean_split.json clean_split.json
ln -sf ../results/leakage.json dup_audit.json
cd "$ROOT_DIR"

# 1. Classical ML Baselines
echo "--- 1. Training Classical ML Baselines ---"
$PYTHON scripts/train_classical.py

# 2. Deep Classifiers
echo "--- 2. Training EfficientNet-B0 (Clean Split) ---"
$PYTHON scripts/train_classifier.py --model effb0 --size 160 --epochs 12 --lr 1e-3 --split clean

echo "--- 3. Training SE-CNN (Clean Split) ---"
$PYTHON scripts/train_classifier.py --model secnn --size 128 --epochs 15 --lr 2e-3 --split clean

echo "--- 4. Training Custom CNN (Clean Split) ---"
$PYTHON scripts/train_classifier.py --model cnn --size 128 --epochs 15 --lr 2e-3 --split clean

echo "--- 5. Training EfficientNet-B0 on Official Split (Leakage Audit) ---"
$PYTHON scripts/train_classifier.py --model effb0 --size 160 --epochs 6 --lr 1e-3 --split official

# 3. Segmentation Models
echo "--- 6. Training U-Net Segmentation ---"
$PYTHON scripts/train_segmentation.py --arch unet --epochs 40

echo "--- 7. Training Attention U-Net Segmentation ---"
$PYTHON scripts/train_segmentation.py --arch attunet --epochs 40

# 4. Figures, Grad-CAM, Result consolidation
echo "--- 8. Generating Figures & Consolidated Metrics ---"
$PYTHON exp/figures.py
$PYTHON exp/gradcam.py
$PYTHON exp/result_figs.py
$PYTHON exp/equations.py || true
$PYTHON scripts/generate_segmentation_figure.py

echo "=========================================="
echo "End-to-End Evaluation Pipeline Completed"
echo "Metrics written to results/metrics.json and results/segmentation.json"
echo "=========================================="
