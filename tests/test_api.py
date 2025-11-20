"""
Tests for API file operations
"""

import pytest
from src.api import build_folder_path
from config.settings import config


def test_build_folder_path_standard():
    """Test folder path building without phase."""
    path = build_folder_path("ActiwatchL", None, "PID123")
    expected = "ActiwatchL/PID123/output_PID123/results/"
    assert path == expected


def test_build_folder_path_phased():
    """Test folder path building with phase."""
    path = build_folder_path("Actical", "Baseline", "PID456")
    expected = "Actical/Baseline/PID456/output_PID456/results/"
    assert path == expected


def test_build_folder_path_with_special_chars():
    """Test folder path building with special participant IDs."""
    path = build_folder_path("FitBit", None, "SUBJ_001")
    expected = "FitBit/SUBJ_001/output_SUBJ_001/results/"
    assert path == expected
