#!/usr/bin/env python3
"""
Setup Verification Script
=========================
Checks that the data sharing environment is properly configured:
  - rclone installed and configured
  - Google Drive accessible
  - Project folder structure exists
  - Raw data uploaded (or available locally)
  - Python dependencies installed
  - Pipeline scripts importable

Run from project root:
    python scripts/verify_setup.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check(label: str, ok: bool, details: str = "") -> bool:
    """Print a check result and return the status."""
    icon = "✓" if ok else "✗"
    color = "\033[32m" if ok else "\033[31m"  # green / red
    reset = "\033[0m"
    print(f"  {color}{icon}{reset} {label}", end="")
    if details:
        print(f"  ({details})", end="")
    print()
    return ok


def main():
    print("=" * 70)
    print("WAR SIGNAL THESIS — SETUP VERIFICATION")
    print("=" * 70)

    all_ok = True

    # ── 1. Python & Dependencies ──────────────────────────────────────────
    print("\n[1/6] Python environment")
    py_ok = sys.version_info >= (3, 11)
    all_ok &= check(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        py_ok,
        ">= 3.11 required",
    )
    if not py_ok:
        print("\n  → Install Python 3.11+ and create a virtual environment")

    # Check key packages
    for pkg in ["pandas", "pyarrow", "yaml", "tqdm"]:
        try:
            __import__(pkg)
            check(f"Package '{pkg}'", True)
        except ImportError:
            check(f"Package '{pkg}'", False, "not installed")
            all_ok = False

    # ── 2. rclone ─────────────────────────────────────────────────────────
    print("\n[2/6] rclone (Google Drive CLI)")
    rclone_ok = shutil.which("rclone") is not None
    all_ok &= check("rclone installed", rclone_ok)
    if rclone_ok:
        result = subprocess.run(["rclone", "--version"], capture_output=True, text=True, timeout=10)
        version_line = result.stdout.split("\n")[0] if result.returncode == 0 else "unknown"
        check(f"rclone version", True, version_line)

    # ── 3. Google Drive Connection ────────────────────────────────────────
    print("\n[3/6] Google Drive connection")
    if rclone_ok:
        try:
            result = subprocess.run(
                ["rclone", "lsf", "gdrive:WarSignalsThesis_Data"],
                capture_output=True, text=True, timeout=10
            )
            drive_ok = result.returncode == 0
            all_ok &= check("Google Drive accessible", drive_ok)
            if drive_ok:
                folders = result.stdout.strip().split("\n")
                check(
                    "Project folder exists",
                    "data/" in folders,
                    f"found: {folders}",
                )
        except subprocess.TimeoutExpired:
            check("Google Drive accessible", False, "timeout (10s)")
            all_ok = False
    else:
        check("Google Drive accessible", False, "rclone not installed")
        all_ok = False

    # ── 4. Data Files ────────────────────────────────────────────────────
    print("\n[4/6] Raw data availability")
    if rclone_ok:
        try:
            result = subprocess.run(
                ["rclone", "lsf", "gdrive:WarSignalsThesis_Data/data/raw_enriched"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                files = [f for f in result.stdout.strip().split("\n") if f]
                n_files = len(files)
                check(
                    f"Raw data in Drive ({n_files} files)",
                    n_files == 184,
                    f"expected 184" if n_files != 184 else "all present",
                )
                if n_files < 184:
                    print(f"    Note: upload may still be in progress")
            else:
                check("Raw data in Drive", False, "cannot list")
                all_ok = False
        except subprocess.TimeoutExpired:
            check("Raw data in Drive", False, "timeout (upload may be in progress)")

    # Check local copy
    local_raw = PROJECT_ROOT / "data" / "news_colab_sim" / "war_signals_phase3" / "raw_enriched"
    if local_raw.exists():
        local_files = list(local_raw.glob("*.parquet"))
        check(
            f"Local copy ({len(local_files)} files)",
            len(local_files) == 184,
        )
    else:
        check("Local copy", False, "not downloaded (OK if using Colab)")

    # ── 5. Code Structure ────────────────────────────────────────────────
    print("\n[5/6] Code structure")
    for path in [
        "src/data/gdelt.py",
        "scripts/phase3_post_process_enriched.py",
        "scripts/phase3_sensitivity_analysis.py",
        "notebooks/colab_03b_phase3_pipeline.ipynb",
        "config/source_groups.yaml",
        "config/country_groups.yaml",
        "config/gdelt_queries.yaml",
        "docs/data_sharing.md",
    ]:
        full = PROJECT_ROOT / path
        ok = full.exists()
        all_ok &= check(path, ok)

    # ── 6. Git Status ────────────────────────────────────────────────────
    print("\n[6/6] Git repository")
    git_dir = PROJECT_ROOT / ".git"
    check(".git exists", git_dir.exists())

    if git_dir.exists():
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                print(f"    Uncommitted changes:")
                for line in result.stdout.strip().split("\n")[:5]:
                    print(f"      {line}")
            else:
                check("Working tree clean", True)
        except Exception:
            check("Git status check", False, "error")

    # ── 5. Phase 5 model matrix ────────────────────────────────────────────
    print("\n[7/8] Phase 5 model matrix")
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.features.load_model_matrix import (
            load_model_matrix, validate_model_matrix_for_phase6,
        )
        mm = load_model_matrix()
        result = validate_model_matrix_for_phase6(mm)
        all_ok &= check(
            "model matrix loads",
            True,
            f"{result['n_rows']} rows × {result['n_features']} features",
        )
        for name, ok, detail in result["checks"]:
            all_ok &= check(f"  {name}", ok, detail)
    except Exception as e:
        all_ok &= check("Phase 5 model matrix", False, str(e)[:60])

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    if all_ok:
        print("✓ ALL CHECKS PASSED")
        print("\nYou're ready to run the pipeline!")
        print("  Local: python scripts/phase3_post_process_enriched.py")
        print("  Colab: open notebooks/colab_03b_phase3_pipeline.ipynb")
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nReview the failed checks above. See docs/data_sharing.md for setup help.")
    print("=" * 70)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
