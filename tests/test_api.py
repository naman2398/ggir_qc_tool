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


def test_find_csv_by_prefix_excludes_full_prefix_and_picks_latest(monkeypatch):
    def fake_list_files(access_token, folder_path, root_path=None):
        return [
            {"id": "1", "name": "part5_daysummary_full_20240101.csv"},
            {"id": "2", "name": "part5_daysummary_full_20240102.csv"},
            {"id": "3", "name": "part5_daysummary_20240101.csv"},
            {"id": "4", "name": "part5_daysummary_20240103.csv"},
            {"id": "5", "name": "part5_daysummary_20240102.csv"},
        ]

    monkeypatch.setattr(file_operations, "list_files_in_folder", fake_list_files)

    result = file_operations.find_csv_by_prefix(
        "token",
        "Device/PID/output_PID/results/",
        file_operations.settings.TARGET_FILES["day_csv_prefix"],
        exclude_prefixes=[file_operations.settings.TARGET_FILES["day_csv_full_prefix"]],
    )

    assert result["name"] == "part5_daysummary_20240103.csv"


def test_find_qc_csv_by_prefix_prefers_qc_root(monkeypatch):
    calls = []

    def fake_find_csv_by_prefix(access_token, folder_path, prefix, root_path=None, exclude_prefixes=None):
        calls.append(root_path)
        if root_path == file_operations.settings.QC_ROOT_FOLDER_PATH:
            return {"id": "qc-id", "name": "part5_daysummary_full_20240102.csv"}
        return None

    monkeypatch.setattr(file_operations, "find_csv_by_prefix", fake_find_csv_by_prefix)

    result = file_operations.find_qc_csv_by_prefix(
        "token",
        "Device/PID/output_PID/results/",
        file_operations.settings.TARGET_FILES["day_csv_full_prefix"],
        subfolder=file_operations.settings.TARGET_FILES["day_csv_full_subfolder"],
    )

    assert result["id"] == "qc-id"
    assert calls == [file_operations.settings.QC_ROOT_FOLDER_PATH]


def test_find_all_phase_files_includes_day_summary(monkeypatch):
    monkeypatch.setattr(
        file_operations.settings,
        "DEVICE_PHASE_MAPPING",
        {"Actical": ["Baseline"]},
    )

    monkeypatch.setattr(
        file_operations,
        "build_participant_phase_folder_path",
        lambda device, participant_id, phase: "Actical/PID/output_PID_Baseline/results/",
    )

    def fake_find_file(access_token, folder_path, filename, root_path=None):
        if filename == file_operations.settings.TARGET_FILES["csv"]:
            return {"id": "night-id", "name": filename}
        if filename == file_operations.settings.TARGET_FILES["pdf_sleep"]:
            return {"id": "pdf-id", "name": filename}
        return None

    monkeypatch.setattr(file_operations, "find_file", fake_find_file)
    monkeypatch.setattr(
        file_operations,
        "find_qc_csv",
        lambda access_token, folder_path: {"id": "qc-id", "name": "part4_nightsummary_sleep_full.csv"},
    )
    monkeypatch.setattr(file_operations, "list_pdfs_in_subfolder", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        file_operations,
        "find_csv_by_prefix",
        lambda access_token, folder_path, prefix, root_path=None, exclude_prefixes=None: {
            "id": "day-id",
            "name": "part5_daysummary_20240101.csv",
        }
        if prefix == file_operations.settings.TARGET_FILES["day_csv_prefix"]
        else None,
    )
    monkeypatch.setattr(
        file_operations,
        "find_qc_csv_by_prefix",
        lambda access_token, folder_path, prefix, exclude_prefixes=None, subfolder=None: {
            "id": "day-full-id",
            "name": "part5_daysummary_full_20240101.csv",
        },
    )

    results = file_operations.find_all_phase_files("token", "Actical", "PID")

    assert len(results) == 1
    phase_entry = results[0]
    assert phase_entry["day_csv_file"]["name"] == "part5_daysummary_20240101.csv"
    assert phase_entry["day_qc_csv_file"]["name"] == "part5_daysummary_full_20240101.csv"
