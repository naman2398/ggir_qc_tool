#!/usr/bin/env python3
"""Safe SharePoint CSV cleanup for GGIR_QC_outputs.

This script removes only CSV files under folder children of the SharePoint
GGIR_QC_outputs root while preserving all folders. By default it runs in
dry-run mode and prints every deletion candidate.

Safety defaults:
1. Dry-run unless --execute is provided.
2. Preserves root-level user_comments.csv.
3. Ignores root-level CSV files unless --include-root-csv is set.
4. Deletes by item id only (never folder deletion operations).

Required environment variables:
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
    AZURE_TENANT_ID
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import logging
import os
from urllib.parse import quote

import requests

try:
    import msal
except ImportError:  # pragma: no cover - exercised only in runtime environments missing msal
    msal = None

from config import settings


PRESERVED_ROOT_FILENAME = settings.ACTIVITY_LOG_FILE
SUCCESS_DELETE_CODES = {200, 202, 204}

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeleteCandidate:
    """Represents one SharePoint file selected for deletion."""

    item_id: str
    path: str


def configure_logging(verbose: bool) -> None:
    """Configure script logging level and format."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )


def get_access_token() -> str:
    """Acquire a Graph API access token from service principal credentials."""
    if msal is None:
        raise RuntimeError(
            "The msal package is required to run this script. "
            "Install dependencies from requirements.txt first."
        )

    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    tenant_id = os.environ.get("AZURE_TENANT_ID")

    missing = [
        key
        for key, value in {
            "AZURE_CLIENT_ID": client_id,
            "AZURE_CLIENT_SECRET": client_secret,
            "AZURE_TENANT_ID": tenant_id,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    authority = settings.AUTHORITY_URL.format(tenant_id=tenant_id)
    app = msal.ConfidentialClientApplication(
        client_id,
        client_credential=client_secret,
        authority=authority,
    )
    result = app.acquire_token_for_client(scopes=settings.SCOPES)

    if "access_token" not in result:
        raise RuntimeError(
            f"Failed to acquire token: {result.get('error_description', result)}"
        )

    return result["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _encode(path: str) -> str:
    return quote(path, safe="/")


def get_drive_id(token: str) -> str:
    """Resolve SharePoint document library to Graph drive id."""
    site_url = (
        f"{settings.GRAPH_API_ENDPOINT}/sites/"
        f"{settings.SHAREPOINT_HOSTNAME}:{settings.SHAREPOINT_SITE_PATH}"
    )
    site_resp = requests.get(site_url, headers=_headers(token))
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]

    drives_url = f"{settings.GRAPH_API_ENDPOINT}/sites/{site_id}/drives"
    drives_resp = requests.get(drives_url, headers=_headers(token))
    drives_resp.raise_for_status()

    for drive in drives_resp.json().get("value", []):
        if drive.get("name") == settings.DOCUMENT_LIBRARY:
            return drive["id"]

    raise RuntimeError(f"Document library '{settings.DOCUMENT_LIBRARY}' not found.")


def get_item_by_path(token: str, drive_id: str, path: str) -> dict | None:
    """Get item metadata by drive-relative path or None if not found."""
    encoded = _encode(path)
    url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}"
    resp = requests.get(url, headers=_headers(token))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def list_folder_children_by_item_id(token: str, drive_id: str, item_id: str) -> list[dict]:
    """List all direct children of a folder item, handling Graph pagination."""
    url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{item_id}/children"
    items: list[dict] = []

    while url:
        resp = requests.get(url, headers=_headers(token))
        resp.raise_for_status()
        payload = resp.json()
        items.extend(payload.get("value", []))
        url = payload.get("@odata.nextLink")

    return items


def is_csv_filename(name: str) -> bool:
    """Case-insensitive CSV filename check."""
    return name.lower().endswith(".csv")


def _walk_csv_candidates(
    token: str,
    drive_id: str,
    *,
    folder_id: str,
    folder_path: str,
) -> tuple[list[DeleteCandidate], int, int]:
    """Recursively collect CSV file candidates under one folder."""
    stack: list[tuple[str, str]] = [(folder_id, folder_path)]
    candidates: list[DeleteCandidate] = []
    scanned_folders = 0
    scanned_files = 0

    while stack:
        current_id, current_path = stack.pop()
        scanned_folders += 1

        for child in list_folder_children_by_item_id(token, drive_id, current_id):
            child_name = child.get("name", "")
            child_path = f"{current_path}/{child_name}"

            if "folder" in child:
                child_id = child.get("id")
                if child_id:
                    stack.append((child_id, child_path))
                continue

            if "file" not in child:
                continue

            scanned_files += 1
            if is_csv_filename(child_name):
                child_id = child.get("id")
                if child_id:
                    candidates.append(DeleteCandidate(item_id=child_id, path=child_path))

    return candidates, scanned_folders, scanned_files


def collect_cleanup_plan(
    token: str,
    drive_id: str,
    *,
    root_path: str,
    include_root_csv: bool,
) -> dict:
    """Build a safe deletion plan without deleting anything."""
    root_item = get_item_by_path(token, drive_id, root_path)
    if root_item is None:
        raise RuntimeError(f"QC root folder does not exist: {root_path}")
    if "folder" not in root_item:
        raise RuntimeError(f"QC root path is not a folder: {root_path}")

    preserved_root_path = f"{root_path}/{PRESERVED_ROOT_FILENAME}"
    root_children = list_folder_children_by_item_id(token, drive_id, root_item["id"])

    candidates: list[DeleteCandidate] = []
    preserved_paths: list[str] = []
    skipped_root_csv: list[str] = []
    root_folders: list[dict] = []

    for item in root_children:
        if "folder" in item:
            root_folders.append(item)
            continue

        if "file" not in item:
            continue

        name = item.get("name", "")
        if not is_csv_filename(name):
            continue

        item_path = f"{root_path}/{name}"
        if item_path == preserved_root_path:
            preserved_paths.append(item_path)
            continue

        if include_root_csv:
            item_id = item.get("id")
            if item_id:
                candidates.append(DeleteCandidate(item_id=item_id, path=item_path))
            continue

        skipped_root_csv.append(item_path)

    scanned_folders = 0
    scanned_files = 0

    for folder in sorted(root_folders, key=lambda entry: entry.get("name", "").lower()):
        folder_id = folder.get("id")
        folder_name = folder.get("name", "")
        if not folder_id or not folder_name:
            continue

        folder_path = f"{root_path}/{folder_name}"
        folder_candidates, folder_count, file_count = _walk_csv_candidates(
            token,
            drive_id,
            folder_id=folder_id,
            folder_path=folder_path,
        )

        candidates.extend(folder_candidates)
        scanned_folders += folder_count
        scanned_files += file_count

    return {
        "root_path": root_path,
        "preserved_root_path": preserved_root_path,
        "root_folder_count": len(root_folders),
        "scanned_folders": scanned_folders,
        "scanned_files": scanned_files,
        "preserved_paths": sorted(preserved_paths),
        "skipped_root_csv": sorted(skipped_root_csv),
        "candidates": sorted(candidates, key=lambda entry: entry.path.lower()),
    }


def delete_file_by_id(token: str, drive_id: str, item_id: str) -> tuple[bool, str]:
    """Delete a SharePoint item by id and return success + reason."""
    url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{item_id}"
    resp = requests.delete(url, headers=_headers(token))

    if resp.status_code in SUCCESS_DELETE_CODES:
        return True, ""

    if resp.status_code == 404:
        return False, "File not found (already deleted or moved)."

    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        return False, str(exc)

    return False, f"Unexpected delete status code: {resp.status_code}"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Safely purge CSV files under SharePoint GGIR_QC_outputs. "
            "Defaults to dry-run."
        )
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Delete all listed candidates. Without this flag the script is dry-run only.",
    )
    parser.add_argument(
        "--include-root-csv",
        action="store_true",
        help=(
            "Also include root-level CSV files under GGIR_QC_outputs, except "
            "user_comments.csv. Disabled by default for extra safety."
        ),
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on first deletion failure when running with --execute.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def _print_plan(plan: dict, *, execute: bool, include_root_csv: bool) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    log.info("=" * 72)
    log.info("Mode: %s", mode)
    log.info("Root path: %s", plan["root_path"])
    log.info("Root folder children scanned: %d", plan["root_folder_count"])
    log.info("Nested folders scanned: %d", plan["scanned_folders"])
    log.info("Nested files scanned: %d", plan["scanned_files"])

    if plan["preserved_paths"]:
        log.info("Preserved files:")
        for item_path in plan["preserved_paths"]:
            log.info("  KEEP  %s", item_path)

    if not include_root_csv and plan["skipped_root_csv"]:
        log.info("Root-level CSV files skipped by default safety mode:")
        for item_path in plan["skipped_root_csv"]:
            log.info("  SKIP  %s", item_path)

    log.info("CSV deletion candidates: %d", len(plan["candidates"]))
    for candidate in plan["candidates"]:
        log.info("  CAND  %s", candidate.path)

    if not plan["candidates"]:
        log.info("No CSV candidates found for deletion.")

    log.info("=" * 72)


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    try:
        token = get_access_token()
        drive_id = get_drive_id(token)

        plan = collect_cleanup_plan(
            token,
            drive_id,
            root_path=settings.QC_ROOT_FOLDER_PATH,
            include_root_csv=args.include_root_csv,
        )
        _print_plan(plan, execute=args.execute, include_root_csv=args.include_root_csv)

        if not args.execute:
            log.info("Dry-run complete. Re-run with --execute to delete candidates.")
            return 0

        if not plan["candidates"]:
            log.info("No deletions needed.")
            return 0

        deleted = 0
        failed = 0

        for candidate in plan["candidates"]:
            success, reason = delete_file_by_id(token, drive_id, candidate.item_id)
            if success:
                deleted += 1
                log.info("  DONE  %s", candidate.path)
            else:
                failed += 1
                log.error("  FAIL  %s  (%s)", candidate.path, reason)
                if args.fail_fast:
                    break

        log.info("Deletion summary: attempted=%d deleted=%d failed=%d",
                 deleted + failed, deleted, failed)

        return 2 if failed else 0
    except requests.HTTPError as exc:
        log.error("Graph API request failed: %s", exc)
        return 1
    except Exception as exc:
        log.error("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
