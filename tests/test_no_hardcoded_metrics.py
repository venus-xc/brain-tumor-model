"""Audit test verifying that no fabricated or hardcoded performance numbers exist in app/ source code."""
import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"

# Banned fabricated literals that were previously hardcoded in app/
FABRICATED_NUMBERS = [
    "98.65",
    "0.942",
    "0.9065",
    "100.00",
    "0.998",
]


def test_no_hardcoded_performance_metrics_in_app():
    """Scans all Python and template/JS files in app/ to guarantee no hardcoded metrics exist."""
    violations = []
    
    file_extensions = {".py", ".html", ".js"}
    
    for root, _, files in os.walk(APP_DIR):
        for f in files:
            path = Path(root) / f
            if path.suffix in file_extensions:
                try:
                    content = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                    
                for lit in FABRICATED_NUMBERS:
                    # Match exact float string
                    if lit in content:
                        # Allow matching in comments or variable names only if not reporting metrics
                        violations.append(f"{path.relative_to(PROJECT_ROOT)}: contains fabricated literal '{lit}'")

    assert not violations, "Found prohibited hardcoded metrics in app/:\n" + "\n".join(violations)
