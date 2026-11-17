#!/usr/bin/env bash
# Data acquisition script for Brain Tumor Classification & Segmentation
# Datasets:
# 1. Classification: SARTAJ dataset (Bhuvaji et al., Kaggle 2020, doi:10.34740/KAGGLE/DSV/1183165)
# 2. Segmentation: Figshare brain tumor dataset (Cheng et al., doi:10.6084/m9.figshare.1512427.v5, CC BY 4.0)
# 3. Model weights: EfficientNet-B0 pretrained ImageNet weights
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p data/raw/sartaj data/raw/figshare data/processed weights results figs

# 1. Sartaj classification dataset (Bhuvaji et al., Kaggle 2020, doi:10.34740/KAGGLE/DSV/1183165)
if [ ! -d "data/raw/sartaj/Training" ]; then
    echo "Cloning Sartaj classification dataset..."
    rm -rf data/raw/sartaj
    git clone --depth 1 https://github.com/SartajBhuvaji/Brain-Tumor-Classification-DataSet data/raw/sartaj
else
    echo "Sartaj dataset already present."
fi

# 2. Figshare segmentation dataset (Cheng et al., doi:10.6084/m9.figshare.1512427.v5)
MAT_COUNT=$(find data/raw/figshare -maxdepth 1 -name "*.mat" 2>/dev/null | wc -l | tr -d ' ')
if [ "$MAT_COUNT" -lt 3064 ]; then
    echo "Acquiring Figshare brain tumor segmentation dataset..."
    if [ ! -f "data/raw/figshare/brainTumorDataPublic_1-766.zip" ]; then
        curl -L -o data/raw/figshare/brainTumorDataPublic_1-766.zip https://ndownloader.figshare.com/files/3381290
    fi
    if [ ! -f "data/raw/figshare/brainTumorDataPublic_767-1532.zip" ]; then
        curl -L -o data/raw/figshare/brainTumorDataPublic_767-1532.zip https://ndownloader.figshare.com/files/3381296
    fi
    if [ ! -f "data/raw/figshare/brainTumorDataPublic_1533-2298.zip" ]; then
        curl -L -o data/raw/figshare/brainTumorDataPublic_1533-2298.zip https://ndownloader.figshare.com/files/3381293
    fi
    if [ ! -f "data/raw/figshare/brainTumorDataPublic_2299-3064.zip" ]; then
        curl -L -o data/raw/figshare/brainTumorDataPublic_2299-3064.zip https://ndownloader.figshare.com/files/3381302
    fi
    if [ ! -f "data/raw/figshare/cvind.mat" ]; then
        curl -L -o data/raw/figshare/cvind.mat https://ndownloader.figshare.com/files/7005344
    fi

    echo "Unzipping Figshare files..."
    for z in data/raw/figshare/brainTumorDataPublic_*.zip; do
        if [ -f "$z" ]; then
            echo "Unzipping $z..."
            unzip -q -o "$z" -d data/raw/figshare/
        fi
    done
fi

TOTAL_MAT=$(find data/raw/figshare -maxdepth 1 -name "*.mat" | wc -l | tr -d ' ')
echo "Figshare .mat files verified: $TOTAL_MAT"

# 3. EfficientNet-B0 pretrained weights
if [ ! -f "weights/effb0.pth" ]; then
    echo "Downloading EfficientNet-B0 ImageNet weights..."
    curl -L -o weights/effb0.pth https://github.com/rwightman/pytorch-image-models/releases/download/v0.1-weights/efficientnet_b0_ra-3dd342df.pth
else
    echo "weights/effb0.pth already exists."
fi

echo "Data acquisition complete."
