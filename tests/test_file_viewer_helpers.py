"""Tests for file viewer compare and state helpers."""

import pandas as pd

from src.ui.file_viewer import (
    _align_rows_to_columns,
    _build_previous_state,
    _df_without_helper_cols,
    _missing_summary_mask,
    _summary_to_edit_suffix,
)


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


def test_missing_summary_mask_handles_mixed_dtypes_without_merge_error():
    summary_df = pd.DataFrame(
        [
            {"error_dur": 12.5, "flag": "ok"},
            {"error_dur": 3.0, "flag": "warn"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"error_dur": "12.5", "flag": "ok"},
            {"error_dur": 3.0, "flag": "warn"},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, False]


def test_missing_summary_mask_uses_edit_columns_as_canonical_subset():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": "x", "extra": "foo"},
            {"A": 2, "B": "y", "extra": "bar"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"A": 1, "B": "x"},
            {"A": 2, "B": "y"},
        ]
    )

    mask = _missing_summary_mask(summary_df, edit_df)
    assert mask.tolist() == [False, False]


def test_align_rows_to_columns_keeps_target_schema_and_order():
    rows_df = pd.DataFrame(
        [
            {"B": "x", "A": 1, "extra": "drop-me"},
        ]
    )

    aligned = _align_rows_to_columns(rows_df, ["A", "B"])

    assert list(aligned.columns) == ["A", "B"]
    assert aligned.to_dict("records") == [{"A": 1, "B": "x"}]


def test_missing_summary_mask_after_copy_alignment_does_not_false_highlight_existing_rows():
    summary_df = pd.DataFrame(
        [
            {"A": 1, "B": "x", "C": "keep-only-in-summary"},
            {"A": 2, "B": "y", "C": "keep-only-in-summary"},
            {"A": 3, "B": "z", "C": "keep-only-in-summary"},
        ]
    )
    edit_df = pd.DataFrame(
        [
            {"_to_delete": False, "_added": False, "A": 1, "B": "x"},
            {"_to_delete": False, "_added": False, "A": 2, "B": "y"},
        ]
    )

    initial_mask = _missing_summary_mask(summary_df, edit_df)
    assert initial_mask.tolist() == [False, False, True]

    rows_to_copy = summary_df[initial_mask].reset_index(drop=True)
    edit_clean = _df_without_helper_cols(edit_df)
    rows_to_copy_aligned = _align_rows_to_columns(rows_to_copy, edit_clean.columns)
    updated_edit = pd.concat([edit_clean, rows_to_copy_aligned], ignore_index=True)

    after_copy_mask = _missing_summary_mask(summary_df, updated_edit)
    assert after_copy_mask.tolist() == [False, False, False]


def test_build_previous_state_uses_current_editor_df_for_undo_snapshot():
    original_df = pd.DataFrame([{"A": 1, "B": "x"}])
    editor_df = pd.DataFrame(
        [
            {"_to_delete": True, "_added": False, "A": 1, "B": "x"},
            {"_to_delete": False, "_added": True, "A": 2, "B": "y"},
        ]
    )

    snapshot = _build_previous_state(
        original_df=original_df,
        editor_df=editor_df,
        last_saved="v1.csv",
        last_saved_url="https://example.com/v1.csv",
    )

    assert snapshot["original_df"].equals(original_df)
    assert snapshot["current_df"].equals(editor_df)
    assert snapshot["last_saved"] == "v1.csv"
    assert snapshot["last_saved_url"] == "https://example.com/v1.csv"
