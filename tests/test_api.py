"""Tests for API file operations"""

import pytest
from src.api.file_operations import build_folder_path


def test_build_folder_path_standard():
    path = build_folder_path("ActiwatchL", None, "PID123")
    assert path == "ActiwatchL/PID123/output_PID123/results/"


def test_build_folder_path_phased():
    path = build_folder_path("Actical", "Baseline", "PID456")
    assert path == "Actical/Baseline/PID456/output_PID456/results/"


def test_build_folder_path_with_special_chars():
    path = build_folder_path("FitBit", None, "SUBJ_001")
    assert path == "FitBit/SUBJ_001/output_SUBJ_001/results/"
