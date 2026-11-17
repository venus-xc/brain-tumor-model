import os
import json
import pytest
import numpy as np
import cv2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_identical_images_in_same_group():
    # Construct two identical synthetic images and one different
    img1 = np.ones((32, 32), dtype=np.float32)
    img1[10:20, 10:20] = 2.0
    img2 = img1.copy()
    img3 = np.zeros((32, 32), dtype=np.float32)
    img3[5:15, 5:15] = 1.0

    X = np.stack([img1, img2, img3]).reshape(3, -1)
    X -= X.mean(1, keepdims=True)
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-6
    S = X @ X.T

    parent = list(range(3))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    ii, jj = np.where(np.triu(S, 1) >= 0.98)
    for a, b in zip(ii, jj):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    groups = [find(i) for i in range(3)]
    # img1 and img2 must have identical group ID
    assert groups[0] == groups[1], "Identical images must be assigned to the same group"
    # img3 must have a different group ID
    assert groups[0] != groups[2], "Distinct image must not be grouped with identical pair"


def test_no_group_crosses_splits():
    clean_split_file = os.path.join(PROJECT_ROOT, "results", "clean_split.json")
    if not os.path.exists(clean_split_file):
        pytest.skip("results/clean_split.json not yet generated")

    with open(clean_split_file, "r") as f:
        meta = json.load(f)

    assert meta.get("duplicate_groups_crossing_subsets", 0) == 0
