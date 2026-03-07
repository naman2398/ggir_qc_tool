#!/usr/bin/env python3
"""
SharePoint Folder Structure Migration Script
============================================
Migrates Actical and Philips Health Band output folders from:
    PHASE-FIRST:       {device}/{phase}/{pid}/output_{pid}/results/
to
    PARTICIPANT-FIRST: {device}/{pid}/output_{pid}_{phase}/results/

Each `output_{pid}` folder is moved into a new `{device}/{pid}/` parent
and renamed to `output_{pid}_{phase}`. Everything inside (results/, CSVs,
PDFs, etc.) is untouched — only the parent folder location+name changes.

Left behind (for manual cleanup):
    {device}/{phase}/{pid}/   ← now empty after the move

Usage
-----
    # Preview all planned moves (no SharePoint changes):
    python migrate_sharepoint_structure.py --dry-run

    # Execute migration for all phased devices and phases:
    python migrate_sharepoint_structure.py

    # Limit to a single device:
    python migrate_sharepoint_structure.py --device "Actical"

    # Limit to one or more participant IDs (comma-separated):
    python migrate_sharepoint_structure.py --pid 1001,1002

Environment variables required
-------------------------------
    AZURE_CLIENT_ID
    AZURE_CLIENT_SECRET
    AZURE_TENANT_ID
"""

import argparse
import logging
import os
import sys
from urllib.parse import quote

import msal
import requests

# ---------------------------------------------------------------------------
# Configuration (mirrors config/settings.py — no Streamlit import needed)
# ---------------------------------------------------------------------------

SHAREPOINT_HOSTNAME = "stonybrookmedicine.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/CUBIT"
DOCUMENT_LIBRARY = "CBT-I Documents"
ROOT_FOLDER_PATH = "Actigraphy Analysis (Multi-Study Data Sets)/GGIR_final_outputs"

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]

# Only phased devices are migrated
DEVICE_PHASE_MAPPING = {
    "Actical": ["Baseline", "Overnight", "Pre-Overnight", "Post-Overnight"],
    "Philips Health Band": ["Pre-Scan", "Post-Scan", "Pre-Overnight", "Post-Overnight"],
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    """Acquire a Graph API access token using client credentials from env vars."""
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")
    tenant_id = os.environ.get("AZURE_TENANT_ID")

    missing = [k for k, v in {
        "AZURE_CLIENT_ID": client_id,
        "AZURE_CLIENT_SECRET": client_secret,
        "AZURE_TENANT_ID": tenant_id,
    }.items() if not v]

    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    authority = AUTHORITY_URL.format(tenant_id=tenant_id)
    app = msal.ConfidentialClientApplication(
        client_id, client_credential=client_secret, authority=authority
    )
    result = app.acquire_token_for_client(scopes=SCOPES)

    if "access_token" not in result:
        log.error("Failed to acquire token: %s", result.get("error_description", result))
        sys.exit(1)

    log.info("Access token acquired successfully.")
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph API helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _encode(path: str) -> str:
    """URL-encode a SharePoint path, preserving forward slashes."""
    return quote(path, safe="/")


def get_drive_id(token: str) -> str:
    """Resolve the SharePoint document library to a Graph drive ID."""
    site_url = (
        f"{GRAPH_API_ENDPOINT}/sites/{SHAREPOINT_HOSTNAME}:{SHAREPOINT_SITE_PATH}"
    )
    resp = requests.get(site_url, headers=_headers(token))
    resp.raise_for_status()
    site_id = resp.json()["id"]

    drives_url = f"{GRAPH_API_ENDPOINT}/sites/{site_id}/drives"
    resp = requests.get(drives_url, headers=_headers(token))
    resp.raise_for_status()

    for drive in resp.json().get("value", []):
        if drive["name"] == DOCUMENT_LIBRARY:
            log.info("Drive ID resolved: %s ('%s')", drive["id"], DOCUMENT_LIBRARY)
            return drive["id"]

    raise RuntimeError(f"Document library '{DOCUMENT_LIBRARY}' not found.")


def get_item_by_path(token: str, drive_id: str, path: str) -> dict | None:
    """
    Return the Graph item dict for a path inside the document library root,
    or None if it does not exist (404) or access is denied.

    `path` is relative to the library root (e.g. "Actigraphy Analysis/…/foo").
    """
    encoded = _encode(path)
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}"
    resp = requests.get(url, headers=_headers(token))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def list_folder_children(token: str, drive_id: str, path: str) -> list[dict]:
    """
    Return all children (files + folders) of a folder at `path`.
    Handles `@odata.nextLink` pagination automatically.

    Returns an empty list if the folder does not exist.
    """
    encoded = _encode(path)
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}:/children"
    items = []

    while url:
        resp = requests.get(url, headers=_headers(token))
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        items.extend(data.get("value", []))
        url = data.get("@odata.nextLink")  # None when last page

    return items


def create_folder(token: str, drive_id: str, parent_id: str, folder_name: str) -> dict:
    """Create a folder inside an existing parent folder (by item ID). Returns the new item."""
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{parent_id}/children"
    payload = {"name": folder_name, "folder": {}}
    resp = requests.post(url, headers=_headers(token), json=payload)
    resp.raise_for_status()
    return resp.json()


def get_or_create_folder(token: str, drive_id: str, path: str) -> dict:
    """
    Ensure a folder at `path` exists (relative to library root).
    Creates any missing intermediate folders one level at a time.
    Returns the item dict for the final leaf folder.
    """
    item = get_item_by_path(token, drive_id, path)
    if item:
        return item

    # Walk up to find the deepest existing ancestor, then create downward
    segments = path.rstrip("/").split("/")
    # Find deepest existing ancestor
    existing_depth = len(segments) - 1
    while existing_depth > 0:
        ancestor_path = "/".join(segments[:existing_depth])
        ancestor = get_item_by_path(token, drive_id, ancestor_path)
        if ancestor:
            break
        existing_depth -= 1
    else:
        # Even root doesn't exist? Shouldn't happen in practice.
        raise RuntimeError(f"Cannot find any ancestor of '{path}' in SharePoint.")

    # Create folders from existing_depth + 1 downward
    current_item = ancestor
    for segment in segments[existing_depth:]:
        log.debug("Creating folder '%s' under '%s'", segment, current_item.get("name"))
        current_item = create_folder(token, drive_id, current_item["id"], segment)

    return current_item


def move_item(
    token: str, drive_id: str, item_id: str, new_parent_id: str, new_name: str
) -> dict:
    """
    Move a Drive item to a new parent folder and optionally rename it,
    using a single PATCH request (atomic in Graph API).
    Returns the updated item dict.
    """
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{item_id}"
    payload = {
        "parentReference": {"id": new_parent_id},
        "name": new_name,
    }
    resp = requests.patch(url, headers=_headers(token), json=payload)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------

def build_source_output_path(device: str, phase: str, pid: str) -> str:
    """Full path (from library root) to the output folder in the OLD phase-first layout."""
    return f"{ROOT_FOLDER_PATH}/{device}/{phase}/{pid}/output_{pid}"


def build_dest_parent_path(device: str, pid: str) -> str:
    """Full path to the participant's new top-level folder in the NEW participant-first layout."""
    return f"{ROOT_FOLDER_PATH}/{device}/{pid}"


def build_dest_output_name(pid: str, phase: str) -> str:
    """New name for the relocated output folder, e.g. 'output_1001_Baseline'."""
    return f"output_{pid}_{phase}"


def migrate_participant(
    token: str,
    drive_id: str,
    device: str,
    phase: str,
    pid: str,
    *,
    dry_run: bool,
    counters: dict,
) -> None:
    """Move one participant's output folder for a given device+phase."""
    source_path = build_source_output_path(device, phase, pid)
    dest_parent_path = build_dest_parent_path(device, pid)
    dest_output_name = build_dest_output_name(pid, phase)
    dest_output_path = f"{dest_parent_path}/{dest_output_name}"

    label = f"[{device} / {phase} / {pid}]"

    # --- Verify source exists ---
    source_item = get_item_by_path(token, drive_id, source_path)
    if source_item is None:
        log.warning("%s SKIP — source not found: %s", label, source_path)
        counters["skipped"] += 1
        return

    # Only move folders, not files at this path
    if "folder" not in source_item:
        log.warning("%s SKIP — source is not a folder: %s", label, source_path)
        counters["skipped"] += 1
        return

    # --- Check destination does not already exist ---
    dest_item = get_item_by_path(token, drive_id, dest_output_path)
    if dest_item is not None:
        log.warning(
            "%s SKIP — destination already exists: %s", label, dest_output_path
        )
        counters["skipped"] += 1
        return

    # --- Plan output ---
    log.info(
        "%s  %s\n          → %s",
        "DRY-RUN" if dry_run else "MOVING ",
        source_path,
        dest_output_path,
    )

    if dry_run:
        counters["planned"] += 1
        return

    # --- Execute ---
    try:
        dest_parent_item = get_or_create_folder(token, drive_id, dest_parent_path)
        move_item(
            token,
            drive_id,
            source_item["id"],
            dest_parent_item["id"],
            dest_output_name,
        )
        log.info("%s DONE", label)
        counters["moved"] += 1
    except requests.HTTPError as exc:
        log.error("%s FAILED — %s", label, exc)
        counters["failed"] += 1


def run_migration(
    token: str,
    drive_id: str,
    *,
    dry_run: bool,
    device_filter: str | None,
    pid_filter: set[str] | None,
) -> None:
    """Enumerate all phased devices/phases/participants and migrate each one."""
    counters = {"planned": 0, "moved": 0, "skipped": 0, "failed": 0}

    devices_to_migrate = {
        dev: phases
        for dev, phases in DEVICE_PHASE_MAPPING.items()
        if device_filter is None or dev == device_filter
    }

    if not devices_to_migrate:
        log.error("No matching device found. Available: %s", list(DEVICE_PHASE_MAPPING))
        sys.exit(1)

    for device, phases in devices_to_migrate.items():
        log.info("=" * 60)
        log.info("Device: %s", device)

        for phase in phases:
            phase_path = f"{ROOT_FOLDER_PATH}/{device}/{phase}"
            log.info("  Phase: %s  →  scanning %s", phase, phase_path)

            participants = list_folder_children(token, drive_id, phase_path)
            if not participants:
                log.info("    (no participant folders found — skipping phase)")
                continue

            # Filter to folder items only (ignore stray files)
            pid_folders = [
                item for item in participants
                if "folder" in item
            ]
            log.info("    Found %d participant folder(s).", len(pid_folders))

            for item in pid_folders:
                pid = item["name"]

                if pid_filter and pid not in pid_filter:
                    log.debug("    Skipping %s (not in --pid filter)", pid)
                    continue

                migrate_participant(
                    token,
                    drive_id,
                    device,
                    phase,
                    pid,
                    dry_run=dry_run,
                    counters=counters,
                )

    # --- Summary ---
    log.info("=" * 60)
    if dry_run:
        log.info("DRY-RUN complete. %d move(s) planned.", counters["planned"])
        log.info("Re-run without --dry-run to execute.")
    else:
        log.info(
            "Migration complete.  Moved: %d  |  Skipped: %d  |  Failed: %d",
            counters["moved"],
            counters["skipped"],
            counters["failed"],
        )
        if counters["failed"]:
            log.warning(
                "%d failure(s) occurred. Check logs above for details.",
                counters["failed"],
            )
            sys.exit(2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without making any changes to SharePoint.",
    )
    parser.add_argument(
        "--device",
        metavar="DEVICE_NAME",
        help=(
            "Restrict migration to a single device. "
            f"Options: {list(DEVICE_PHASE_MAPPING)}. Default: all phased devices."
        ),
    )
    parser.add_argument(
        "--pid",
        metavar="PID[,PID,...]",
        help="Comma-separated list of participant IDs to migrate. Default: all found.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        log.info("*** DRY-RUN MODE — no SharePoint changes will be made ***")

    pid_filter: set[str] | None = None
    if args.pid:
        pid_filter = {p.strip() for p in args.pid.split(",") if p.strip()}
        log.info("PID filter active: %s", pid_filter)

    token = get_access_token()
    drive_id = get_drive_id(token)

    run_migration(
        token,
        drive_id,
        dry_run=args.dry_run,
        device_filter=args.device,
        pid_filter=pid_filter,
    )


if __name__ == "__main__":
    main()
