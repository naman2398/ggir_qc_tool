"""Tests for API file operations"""

import re
import pytest
from src.api import file_operations
from src.api.file_operations import build_folder_path, build_participant_phase_folder_path, build_versioned_filename


def test_build_folder_path_standard():
    path = build_folder_path("ActiwatchL", None, "PID123")
    assert path == "ActiwatchL/PID123/output_PID123/results/"


def test_build_folder_path_phased():
    path = build_folder_path("Actical", "Baseline", "PID456")
    assert path == "Actical/Baseline/PID456/output_PID456/results/"


def test_build_folder_path_with_special_chars():
    path = build_folder_path("FitBit", None, "SUBJ_001")
    assert path == "Fitbit/SUBJ_001/output_SUBJ_001/results/"


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


def test_build_folder_path_uses_sharepoint_alias_for_fdg():
    path = build_folder_path("FDG Actical", None, "PID111")
    assert path == "FDG-Actical/PID111/output_PID111/results/"


def test_build_folder_path_uses_sharepoint_alias_for_fitbit():
    path = build_folder_path("FitBit", None, "PID222")
    assert path == "Fitbit/PID222/output_PID222/results/"


def test_find_qc_csv_prefers_qc_root(monkeypatch):
    calls = []

    def fake_find_file(access_token, folder_path, filename, root_path=None):
        calls.append((folder_path, filename, root_path))
        if root_path == file_operations.settings.QC_ROOT_FOLDER_PATH:
            return {"id": "qc-id", "name": filename}
        return None

    monkeypatch.setattr(file_operations, "find_file", fake_find_file)

    result = file_operations.find_qc_csv("token", "FDG Actical/PID001/output_PID001/results/")

    assert result == {"id": "qc-id", "name": file_operations.settings.TARGET_FILES["csv_full"]}
    assert len(calls) == 1
    assert calls[0][2] == file_operations.settings.QC_ROOT_FOLDER_PATH


def test_find_qc_csv_falls_back_to_final_root(monkeypatch):
    calls = []

    def fake_find_file(access_token, folder_path, filename, root_path=None):
        calls.append(root_path)
        if root_path == file_operations.settings.QC_ROOT_FOLDER_PATH:
            return None
        if root_path == file_operations.settings.ROOT_FOLDER_PATH:
            return {"id": "final-id", "name": filename}
        return None

    monkeypatch.setattr(file_operations, "find_file", fake_find_file)

    result = file_operations.find_qc_csv("token", "FDG Actical/PID001/output_PID001/results/")

    assert result == {"id": "final-id", "name": file_operations.settings.TARGET_FILES["csv_full"]}
    assert calls == [
        file_operations.settings.QC_ROOT_FOLDER_PATH,
        file_operations.settings.ROOT_FOLDER_PATH,
    ]
