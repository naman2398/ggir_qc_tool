"""Tests for file viewer compare helpers."""

import pandas as pd

from src.ui.file_viewer import _missing_summary_mask, _summary_to_edit_suffix


def test_summary_to_edit_suffix_for_qc_phase():
    assert _summary_to_edit_suffix("_qc_Baseline") == "_Baseline"
    assert _summary_to_edit_suffix("") == ""


def test_missing_summary_mask_ignores_helper_columns():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": "x"},
            {"A": 2, "B": "y"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"_to_delete": False, "_added": True, "A": 1, "B": "x"},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, True]


def test_missing_summary_mask_treats_nan_as_equal():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": float("nan")},
            {"A": 2, "B": "ok"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"A": 1, "B": float("nan")},
            {"A": 2, "B": "ok"},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, False]


def test_missing_summary_mask_marks_all_missing_on_column_mismatch():
    summary_df = pd.DataFrame([{"A": 1, "B": "x"}])
    edit_df = pd.DataFrame([{"A": 1, "C": "x"}])

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [True]


def test_missing_summary_mask_ignores_column_order():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": "x"},
            {"A": 2, "B": "y"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"B": "x", "A": 1},
            {"B": "y", "A": 2},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, False]


def test_missing_summary_mask_ignores_unnamed_index_artifact_column():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": "x"},
            {"A": 2, "B": "y"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"Unnamed: 0": 0, "A": 1, "B": "x"},
            {"Unnamed: 0": 1, "A": 2, "B": "y"},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, False]
