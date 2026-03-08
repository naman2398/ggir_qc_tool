#!/usr/bin/env python3
"""
Refresh Participant Registry
=============================
Scans both SharePoint roots (GGIR_final_outputs and GGIR_QC_outputs) for
participant folders and rebuilds ``config/participants.yaml``.

Only participant IDs found under a device folder in **both** roots are written
to the YAML.  PIDs that appear in only one root are printed as warnings so the
developer can ensure the mirror folder is created before the participant is
added to the registry.

By default the script **merges** — it adds newly-discovered PIDs but never
removes manually-added entries.  Use ``--fresh`` to overwrite the YAML
completely with what was found on SharePoint.

Usage
-----
    # Preview without writing anything:
    python refresh_participants.py --dry-run

    # Refresh all devices:
    python refresh_participants.py

    # Refresh one device only:
    python refresh_participants.py --device "Actical"

    # Overwrite YAML completely (remove stale manual entries):
    python refresh_participants.py --fresh

    # Verbose debug logging:
    python refresh_participants.py --dry-run --verbose

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
from pathlib import Path
from urllib.parse import quote

import msal
import requests
import yaml

# ---------------------------------------------------------------------------
# Configuration (mirrors config/settings.py — kept self-contained so the
# script can run without the Streamlit app environment)
# ---------------------------------------------------------------------------

SHAREPOINT_HOSTNAME = "stonybrookmedicine.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/CUBIT"
DOCUMENT_LIBRARY = "CBT-I Documents"

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]

PARENT_PATH = "Actigraphy Analysis (Multi-Study Data Sets)"
FINAL_ROOT = f"{PARENT_PATH}/GGIR_final_outputs"
QC_ROOT = f"{PARENT_PATH}/GGIR_QC_outputs"

SUPPORTED_DEVICES = [
    "Actical",
    "ActiwatchL",
    "Philips Health Band",
    "FitBit",
    "FDG Actical",
    "CentrePointLeap",
]

PARTICIPANTS_FILE = Path(__file__).parent / "config" / "participants.yaml"

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
    """Acquire a Graph API access token from env-var client credentials."""
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

    log.info("Access token acquired.")
    return result["access_token"]


# ---------------------------------------------------------------------------
# Graph API helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _encode(path: str) -> str:
    return quote(path, safe="/")


def get_drive_id(token: str) -> str:
    """Resolve the document library drive ID."""
    headers = _headers(token)
    site_url = (
        f"{GRAPH_API_ENDPOINT}/sites/"
        f"{SHAREPOINT_HOSTNAME}:{SHAREPOINT_SITE_PATH}"
    )
    site_id = requests.get(site_url, headers=headers).json()["id"]

    drives_url = f"{GRAPH_API_ENDPOINT}/sites/{site_id}/drives"
    for drive in requests.get(drives_url, headers=headers).json()["value"]:
        if drive["name"] == DOCUMENT_LIBRARY:
            return drive["id"]

    log.error("Document library '%s' not found.", DOCUMENT_LIBRARY)
    sys.exit(1)


def list_child_folders(token: str, drive_id: str, folder_path: str) -> set[str]:
    """Return the names of all direct child *folders* under folder_path."""
    encoded = _encode(folder_path)
    url = f"{GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}:/children"
    resp = requests.get(url, headers=_headers(token))

    if resp.status_code == 404:
        log.warning("Folder not found on SharePoint: %s", folder_path)
        return set()

    resp.raise_for_status()
    return {
        item["name"]
        for item in resp.json().get("value", [])
        if "folder" in item
    }


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml() -> dict[str, list[str]]:
    """Load existing participants.yaml, or return an empty per-device dict."""
    if not PARTICIPANTS_FILE.exists():
        return {device: [] for device in SUPPORTED_DEVICES}
    with PARTICIPANTS_FILE.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    # Ensure every supported device has a list (handles newly added devices)
    for device in SUPPORTED_DEVICES:
        data.setdefault(device, [])
    return data


def save_yaml(data: dict[str, list[str]], dry_run: bool) -> None:
    """Write participants.yaml, sorted alphabetically per device."""
    # Sort lists
    for device in data:
        data[device] = sorted(set(str(p) for p in data[device]))

    header = (
        "# Participant registry — one list per device.\n"
        "# Populated by refresh_participants.py.\n"
        "# Edit freely — re-running the script merges without removing manual entries.\n"
        "# Use  python refresh_participants.py --fresh  to overwrite completely.\n"
    )

    yaml_text = header + yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
    )

    if dry_run:
        log.info("[DRY-RUN] Would write %s:\n%s", PARTICIPANTS_FILE, yaml_text)
    else:
        PARTICIPANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PARTICIPANTS_FILE.write_text(yaml_text, encoding="utf-8")
        log.info("Wrote %s", PARTICIPANTS_FILE)


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def refresh(
    token: str,
    drive_id: str,
    devices: list[str],
    dry_run: bool,
    fresh: bool,
) -> None:
    existing = {} if fresh else load_yaml()

    # Per-device results for the summary table
    summary: list[tuple[str, int, int, int, int]] = []

    for device in devices:
        final_pids = list_child_folders(token, drive_id, f"{FINAL_ROOT}/{device}")
        qc_pids = list_child_folders(token, drive_id, f"{QC_ROOT}/{device}")

        both = final_pids & qc_pids
        only_final = final_pids - qc_pids
        only_qc = qc_pids - final_pids

        if only_final:
            log.warning(
                "[%s] %d PID(s) in GGIR_final_outputs only (no QC mirror) — skipped: %s",
                device, len(only_final), ", ".join(sorted(only_final)),
            )
        if only_qc:
            log.warning(
                "[%s] %d PID(s) in GGIR_QC_outputs only (no final data) — skipped: %s",
                device, len(only_qc), ", ".join(sorted(only_qc)),
            )

        existing_pids = set(str(p) for p in existing.get(device, []))
        new_pids = both - existing_pids

        if new_pids:
            log.info("[%s] Adding %d new PID(s): %s", device, len(new_pids), ", ".join(sorted(new_pids)))

        merged = existing_pids | both
        existing[device] = sorted(merged)

        summary.append((device, len(both), len(new_pids), len(only_final), len(only_qc)))

    save_yaml(existing, dry_run)

    # Print summary table
    col_w = max(len(d) for d, *_ in summary) + 2
    print("\n" + "=" * (col_w + 44))
    print(f"{'Device':<{col_w}} {'Both':>6} {'New':>6} {'Only-Final':>12} {'Only-QC':>9}")
    print("-" * (col_w + 44))
    for device, n_both, n_new, n_only_final, n_only_qc in summary:
        print(
            f"{device:<{col_w}} {n_both:>6} {n_new:>6} {n_only_final:>12} {n_only_qc:>9}"
        )
    print("=" * (col_w + 44))
    if dry_run:
        print("\n[DRY-RUN] No changes written.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh config/participants.yaml from SharePoint."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print planned changes without writing the YAML file.",
    )
    parser.add_argument(
        "--device", metavar="DEVICE",
        help="Restrict refresh to a single device (exact name).",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Overwrite YAML completely instead of merging with existing entries.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    devices = SUPPORTED_DEVICES
    if args.device:
        if args.device not in SUPPORTED_DEVICES:
            log.error(
                "Unknown device '%s'. Choose from: %s",
                args.device,
                ", ".join(SUPPORTED_DEVICES),
            )
            sys.exit(1)
        devices = [args.device]

    token = get_access_token()
    drive_id = get_drive_id(token)
    refresh(token, drive_id, devices, dry_run=args.dry_run, fresh=args.fresh)


if __name__ == "__main__":
    main()
