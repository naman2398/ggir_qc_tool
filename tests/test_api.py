"""Tests for API file operations"""

import re
import pytest
from src.api.file_operations import build_folder_path, build_participant_phase_folder_path, build_versioned_filename


def test_build_folder_path_standard():
    path = build_folder_path("ActiwatchL", None, "PID123")
    assert path == "ActiwatchL/PID123/output_PID123/results/"


def test_build_folder_path_phased():
    path = build_folder_path("Actical", "Baseline", "PID456")
    assert path == "Actical/Baseline/PID456/output_PID456/results/"


def test_build_folder_path_with_special_chars():
    path = build_folder_path("FitBit", None, "SUBJ_001")
    assert path == "FitBit/SUBJ_001/output_SUBJ_001/results/"


def test_build_versioned_filename_with_extension():
    filename = build_versioned_filename("part4_nightsummary_sleep_cleaned.csv", "john_doe")
    # Format: {base}_{username}_{YYYYMMDD_HHMMSS}.{ext}
    assert re.match(
        r"^part4_nightsummary_sleep_cleaned_john_doe_\d{8}_\d{6}\.csv$",
        filename
    )


def test_build_versioned_filename_without_extension_defaults_csv():
    filename = build_versioned_filename("part4_nightsummary_sleep_cleaned", "john_doe")
    assert re.match(
        r"^part4_nightsummary_sleep_cleaned_john_doe_\d{8}_\d{6}\.csv$",
        filename
    )


def test_build_participant_phase_folder_path():
    path = build_participant_phase_folder_path("Actical", "PID789", "Baseline")
    assert path == "Actical/PID789/output_PID789_Baseline/results/"
