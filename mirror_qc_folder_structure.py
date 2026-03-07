#!/usr/bin/env python3
"""
Mirror QC Folder Structure Script
==================================
Creates an empty parallel folder hierarchy under GGIR_QC_outputs that mirrors
the post-migration participant-first layout in GGIR_final_outputs.

For each device → participant → output folder found in GGIR_final_outputs,
the script creates the corresponding empty folder in GGIR_QC_outputs:

    Source (read-only):
        GGIR_final_outputs/{device}/{pid}/output_{pid}_{phase}/

    Destination (created):
        GGIR_QC_outputs/{device}/{pid}/output_{pid}_{phase}/

Nothing inside the output folders is touched — no files are copied or moved.
The GGIR_QC_outputs root folder must already exist in SharePoint.

This destination structure is where the Streamlit app will write edited/saved
files going forward, keeping QC outputs separate from the original GGIR data.

Usage
-----
    # Preview all folders that would be created (no SharePoint changes):
    python mirror_qc_folder_structure.py --dry-run

    # Execute for all devices:
    python mirror_qc_folder_structure.py

    # Limit to a single device:
    python mirror_qc_folder_structure.py --device "Actical"

    # Limit to specific participant IDs:
    python mirror_qc_folder_structure.py --pid 1001,1002

    # Verbose debug logging:
    python mirror_qc_folder_structure.py --dry-run --verbose

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
# Configuration
# ---------------------------------------------------------------------------

SHAREPOINT_HOSTNAME = "stonybrookmedicine.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/CUBIT"
DOCUMENT_LIBRARY = "CBT-I Documents"

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]

# Base paths (both live under the same parent directory in SharePoint)
PARENT_PATH = "Actigraphy Analysis (Multi-Study Data Sets)"
SOURCE_ROOT = f"{PARENT_PATH}/GGIR_final_outputs"
DEST_ROOT = f"{PARENT_PATH}/GGIR_QC_outputs"

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
    return quote(path, safe="/")


def get_drive_id(token: str) -> str:
    """Resolve the SharePoint document library to a Graph drive ID."""
    site_url = f"{GRAPH_API_ENDPOINT}/sites/{SHAREPOINT_HOSTNAME}:{SHAREPOINT_SITE_PATH}"
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
    """Return the Graph item dict for a path, or None if not found."""
    encoded = _encode(path)
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}"
    resp = requests.get(url, headers=_headers(token))
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def list_folder_children(token: str, drive_id: str, path: str) -> list[dict]:
    """
    Return all direct children of a folder at `path`.
    Handles pagination via @odata.nextLink automatically.
    Returns empty list if folder does not exist.
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
        url = data.get("@odata.nextLink")

    return items


def create_folder(token: str, drive_id: str, parent_id: str, folder_name: str) -> dict:
    """Create a child folder inside parent_id. Returns the new item."""
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{parent_id}/children"
    payload = {"name": folder_name, "folder": {}}
    resp = requests.post(url, headers=_headers(token), json=payload)
    resp.raise_for_status()
    return resp.json()


def get_or_create_folder(token: str, drive_id: str, path: str) -> dict:
    """
    Ensure a folder at `path` exists, creating any missing intermediate levels.
    Returns the item dict of the leaf folder.
    """
    item = get_item_by_path(token, drive_id, path)
    if item:
        return item

    segments = path.rstrip("/").split("/")

    # Find the deepest existing ancestor
    existing_depth = len(segments) - 1
    while existing_depth > 0:
        ancestor_path = "/".join(segments[:existing_depth])
        ancestor = get_item_by_path(token, drive_id, ancestor_path)
        if ancestor:
            break
        existing_depth -= 1
    else:
        raise RuntimeError(f"Cannot find any ancestor of '{path}' in SharePoint.")

    current_item = ancestor
    for segment in segments[existing_depth:]:
        log.debug("  Creating subfolder '%s'", segment)
        current_item = create_folder(token, drive_id, current_item["id"], segment)

    return current_item


# ---------------------------------------------------------------------------
# Mirroring logic
# ---------------------------------------------------------------------------

def mirror_structure(
    token: str,
    drive_id: str,
    *,
    dry_run: bool,
    device_filter: str | None,
    pid_filter: set[str] | None,
) -> None:
    """
    Walk GGIR_final_outputs three levels deep (device → pid → output_*)
    and create matching empty folders in GGIR_QC_outputs.
    """
    counters = {"created": 0, "skipped": 0, "planned": 0, "failed": 0}

    # --- Level 1: devices ---
    log.info("Scanning source root: %s", SOURCE_ROOT)
    device_items = list_folder_children(token, drive_id, SOURCE_ROOT)
    device_folders = [d for d in device_items if "folder" in d]

    if not device_folders:
        log.error("No device folders found under %s — aborting.", SOURCE_ROOT)
        sys.exit(1)

    log.info("Found %d device folder(s): %s",
             len(device_folders), [d["name"] for d in device_folders])

    for device_item in device_folders:
        device = device_item["name"]

        if device_filter and device != device_filter:
            log.debug("Skipping device '%s' (not in --device filter)", device)
            continue

        log.info("=" * 60)
        log.info("Device: %s", device)

        # --- Level 2: participants ---
        device_source_path = f"{SOURCE_ROOT}/{device}"
        pid_items = list_folder_children(token, drive_id, device_source_path)
        pid_folders = [p for p in pid_items if "folder" in p]

        if not pid_folders:
            log.info("  (no participant folders found — skipping)")
            continue

        log.info("  Found %d participant folder(s).", len(pid_folders))

        for pid_item in pid_folders:
            pid = pid_item["name"]

            if pid_filter and pid not in pid_filter:
                log.debug("  Skipping pid '%s' (not in --pid filter)", pid)
                continue

            # --- Level 3: output_* folders ---
            pid_source_path = f"{SOURCE_ROOT}/{device}/{pid}"
            output_items = list_folder_children(token, drive_id, pid_source_path)
            output_folders = [o for o in output_items if "folder" in o]

            if not output_folders:
                log.warning("  [%s / %s] No output folders found — skipping.", device, pid)
                continue

            for output_item in output_folders:
                output_name = output_item["name"]
                dest_path = f"{DEST_ROOT}/{device}/{pid}/{output_name}"
                label = f"[{device} / {pid} / {output_name}]"

                # Check destination existence
                existing = get_item_by_path(token, drive_id, dest_path)
                if existing:
                    log.info("  %s SKIP — already exists", label)
                    counters["skipped"] += 1
                    continue

                log.info(
                    "  %s  → %s",
                    "DRY-RUN" if dry_run else "CREATING",
                    dest_path,
                )

                if dry_run:
                    counters["planned"] += 1
                    continue

                try:
                    get_or_create_folder(token, drive_id, dest_path)
                    log.info("  %s DONE", label)
                    counters["created"] += 1
                except requests.HTTPError as exc:
                    log.error("  %s FAILED — %s", label, exc)
                    counters["failed"] += 1

    # --- Summary ---
    log.info("=" * 60)
    if dry_run:
        log.info("DRY-RUN complete. %d folder(s) would be created, %d already exist.",
                 counters["planned"], counters["skipped"])
        log.info("Re-run without --dry-run to execute.")
    else:
        log.info(
            "Mirror complete.  Created: %d  |  Skipped (exists): %d  |  Failed: %d",
            counters["created"],
            counters["skipped"],
            counters["failed"],
        )
        if counters["failed"]:
            log.warning("%d failure(s) — check logs above.", counters["failed"])
            sys.exit(2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print folders that would be created without making any SharePoint changes.",
    )
    parser.add_argument(
        "--device",
        metavar="DEVICE_NAME",
        help=(
            "Restrict mirroring to a single device folder name as it appears in SharePoint "
            "(e.g. 'Actical', 'Philips Health Band'). Default: all devices."
        ),
    )
    parser.add_argument(
        "--pid",
        metavar="PID[,PID,...]",
        help="Comma-separated participant IDs to mirror. Default: all found.",
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

    mirror_structure(
        token,
        drive_id,
        dry_run=args.dry_run,
        device_filter=args.device,
        pid_filter=pid_filter,
    )


if __name__ == "__main__":
    main()
