#!/usr/bin/env python3
"""Training & evaluation dispatcher for Brain Tumor Classification & Segmentation.
Invokes verified modular training scripts in scripts/:
- scripts/train_classical.py (HOG + SVM / RF / k-NN / LR)
- scripts/train_classifier.py (BrainCNN, SE-CNN, EfficientNet-B0)
- scripts/train_segmentation.py (U-Net, Attention U-Net)
- scripts/evaluate_all.sh (End-to-end execution)
"""
import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate brain tumor models on real MRI data")
    parser.add_argument("--mode", choices=["all", "classical", "classifier", "segmentation"], default="all")
    parser.add_argument("--model", choices=["cnn", "secnn", "effb0"], default="effb0")
    parser.add_argument("--arch", choices=["unet", "attunet"], default="attunet")
    parser.add_argument("--split", choices=["clean", "official"], default="clean")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()

    python_bin = sys.executable

    if args.mode == "all":
        cmd = ["bash", os.path.join(SCRIPTS_DIR, "evaluate_all.sh")]
        print(f"Running end-to-end evaluation: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    elif args.mode == "classical":
        cmd = [python_bin, os.path.join(SCRIPTS_DIR, "train_classical.py")]
        subprocess.run(cmd, check=True)
    elif args.mode == "classifier":
        cmd = [python_bin, os.path.join(SCRIPTS_DIR, "train_classifier.py"), "--model", args.model, "--split", args.split]
        if args.epochs:
            cmd.extend(["--epochs", str(args.epochs)])
        subprocess.run(cmd, check=True)
    elif args.mode == "segmentation":
        cmd = [python_bin, os.path.join(SCRIPTS_DIR, "train_segmentation.py"), "--arch", args.arch]
        if args.epochs:
            cmd.extend(["--epochs", str(args.epochs)])
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
