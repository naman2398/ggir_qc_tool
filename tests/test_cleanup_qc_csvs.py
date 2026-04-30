"""Tests for SharePoint QC CSV cleanup script safety behavior."""

import cleanup_qc_csvs as cleanup


ROOT_PATH = "Actigraphy Analysis (Multi-Study Data Sets)/GGIR_QC_outputs"


def test_collect_cleanup_plan_skips_root_csv_by_default(monkeypatch):
    tree = {
        "root": [
            {"id": "folder-device", "name": "Actical", "folder": {}},
            {"id": "file-keep", "name": "user_comments.csv", "file": {}},
            {"id": "file-root-csv", "name": "stray_root.csv", "file": {}},
            {"id": "file-root-txt", "name": "notes.txt", "file": {}},
        ],
        "folder-device": [
            {"id": "folder-pid", "name": "1001", "folder": {}},
        ],
        "folder-pid": [
            {"id": "file-nested-csv", "name": "part4.csv", "file": {}},
            {"id": "file-nested-pdf", "name": "visual.pdf", "file": {}},
        ],
    }

    monkeypatch.setattr(
        cleanup,
        "get_item_by_path",
        lambda token, drive_id, path: {"id": "root", "name": "GGIR_QC_outputs", "folder": {}},
    )
    monkeypatch.setattr(
        cleanup,
        "list_folder_children_by_item_id",
        lambda token, drive_id, item_id: tree[item_id],
    )

    plan = cleanup.collect_cleanup_plan(
        "token",
        "drive",
        root_path=ROOT_PATH,
        include_root_csv=False,
    )

    assert [candidate.path for candidate in plan["candidates"]] == [
        f"{ROOT_PATH}/Actical/1001/part4.csv"
    ]
    assert plan["preserved_paths"] == [f"{ROOT_PATH}/user_comments.csv"]
    assert plan["skipped_root_csv"] == [f"{ROOT_PATH}/stray_root.csv"]


def test_collect_cleanup_plan_can_include_root_csv(monkeypatch):
    tree = {
        "root": [
            {"id": "folder-device", "name": "Actical", "folder": {}},
            {"id": "file-keep", "name": "user_comments.csv", "file": {}},
            {"id": "file-root-csv", "name": "stray_root.csv", "file": {}},
        ],
        "folder-device": [
            {"id": "file-nested-csv", "name": "nested.csv", "file": {}},
        ],
    }

    monkeypatch.setattr(
        cleanup,
        "get_item_by_path",
        lambda token, drive_id, path: {"id": "root", "name": "GGIR_QC_outputs", "folder": {}},
    )
    monkeypatch.setattr(
        cleanup,
        "list_folder_children_by_item_id",
        lambda token, drive_id, item_id: tree[item_id],
    )

    plan = cleanup.collect_cleanup_plan(
        "token",
        "drive",
        root_path=ROOT_PATH,
        include_root_csv=True,
    )

    assert {candidate.path for candidate in plan["candidates"]} == {
        f"{ROOT_PATH}/Actical/nested.csv",
        f"{ROOT_PATH}/stray_root.csv",
    }
    assert plan["preserved_paths"] == [f"{ROOT_PATH}/user_comments.csv"]
    assert plan["skipped_root_csv"] == []


def test_delete_file_by_id_handles_success_and_404(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, status_code):
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise cleanup.requests.HTTPError(f"HTTP {self.status_code}")

    responses = [FakeResponse(204), FakeResponse(404)]

    def fake_delete(url, headers):
        calls.append((url, headers))
        return responses.pop(0)

    monkeypatch.setattr(cleanup.requests, "delete", fake_delete)

    ok, reason_ok = cleanup.delete_file_by_id("token", "drive-id", "item-1")
    not_found, reason_missing = cleanup.delete_file_by_id("token", "drive-id", "item-2")

    assert ok is True
    assert reason_ok == ""
    assert not_found is False
    assert "not found" in reason_missing.lower()
    assert len(calls) == 2


def test_is_csv_filename_is_case_insensitive():
    assert cleanup.is_csv_filename("a.csv") is True
    assert cleanup.is_csv_filename("A.CSV") is True
    assert cleanup.is_csv_filename("a.csv.backup") is False
