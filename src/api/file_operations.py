"""
SharePoint File Operations via Microsoft Graph API
"""

import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime, timezone
from urllib.parse import quote
from config import settings


def _device_folder_name(device):
    """Return the SharePoint folder name for a display device label."""
    return settings.DEVICE_SHAREPOINT_FOLDER.get(device, device)


@st.cache_data(ttl=3600)
def get_drive_id(_access_token):
    """Get SharePoint document library drive ID (cached 1 hour)."""
    headers = {"Authorization": f"Bearer {_access_token}"}
    
    # Get site ID
    site_url = f"{settings.GRAPH_API_ENDPOINT}/sites/{settings.SHAREPOINT_HOSTNAME}:{settings.SHAREPOINT_SITE_PATH}"
    site_resp = requests.get(site_url, headers=headers)
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]
    
    # Get drives and find matching library
    drives_url = f"{settings.GRAPH_API_ENDPOINT}/sites/{site_id}/drives"
    drives_resp = requests.get(drives_url, headers=headers)
    drives_resp.raise_for_status()
    
    for drive in drives_resp.json()["value"]:
        if drive["name"] == settings.DOCUMENT_LIBRARY:
            return drive["id"]
    
    raise ValueError(f"Document library '{settings.DOCUMENT_LIBRARY}' not found")


def build_folder_path(device, phase, participant_id):
    """Build folder path from device, phase, and participant ID."""
    device_folder = _device_folder_name(device)
    if phase:
        return settings.PATH_TEMPLATE_PHASED.format(
            device=device_folder, phase=phase, pid=participant_id
        )
    return settings.PATH_TEMPLATE_STANDARD.format(device=device_folder, pid=participant_id)


def build_participant_phase_folder_path(device, participant_id, phase):
    """Build the post-migration participant-first path for a specific phase."""
    device_folder = _device_folder_name(device)
    return settings.PATH_TEMPLATE_PARTICIPANT_PHASED.format(
        device=device_folder, pid=participant_id, phase=phase
    )


def find_all_phase_files(access_token, device, participant_id):
    """
    For phased devices (Actical, Philips Health Band): find files across ALL phases
    for a given participant. Only phases that have at least one file are included.

    Returns a list of dicts, one per phase with data:
        [
            {
                "phase":          str,
                "folder_path":    str,   # relative path ending in results/
                "csv_file":       dict | None,
                "pdf_file_sleep": dict | None,
                "pdf_file_data":  list[dict],
                "qc_csv_file":    dict | None,  # results/QC/part4_nightsummary_sleep_full.csv
            },
            ...
        ]
    """
    phases = settings.DEVICE_PHASE_MAPPING.get(device, [])
    results = []
    for phase in phases:
        folder_path = build_participant_phase_folder_path(device, participant_id, phase)
        csv_file = find_file(access_token, folder_path, settings.TARGET_FILES["csv"])
        pdf_sleep = find_file(access_token, folder_path, settings.TARGET_FILES["pdf_sleep"])
        pdf_data = list_pdfs_in_subfolder(
            access_token, folder_path, settings.TARGET_FILES["pdf_data"]
        )
        qc_csv_file = find_file(
            access_token,
            folder_path + settings.TARGET_FILES["csv_full_subfolder"],
            settings.TARGET_FILES["csv_full"],
        )
        if any([csv_file, pdf_sleep, pdf_data, qc_csv_file]):
            results.append({
                "phase": phase,
                "folder_path": folder_path,
                "csv_file": csv_file,
                "pdf_file_sleep": pdf_sleep,
                "pdf_file_data": pdf_data,
                "qc_csv_file": qc_csv_file,
            })
    return results


def find_qc_csv(access_token, folder_path):
    """Find read-only QC full summary CSV, preferring GGIR_QC_outputs.

    Some studies store this artifact only in the QC root. We first try QC,
    then fall back to the final root to maintain backward compatibility.
    """
    qc_folder = folder_path + settings.TARGET_FILES["csv_full_subfolder"]

    qc_file = find_file(
        access_token,
        qc_folder,
        settings.TARGET_FILES["csv_full"],
        root_path=settings.QC_ROOT_FOLDER_PATH,
    )
    if qc_file:
        return qc_file

    return find_file(
        access_token,
        qc_folder,
        settings.TARGET_FILES["csv_full"],
        root_path=settings.ROOT_FOLDER_PATH,
    )


def check_participant_folder_exists(access_token, device, pid):
    """Check whether a participant folder exists under both SharePoint roots.

    Returns a dict:
        {
            "in_final": bool,   # folder found under GGIR_final_outputs/{device}/{pid}
            "in_qc":    bool,   # folder found under GGIR_QC_outputs/{device}/{pid}
        }
    """
    try:
        drive_id = get_drive_id(access_token)
        headers = {"Authorization": f"Bearer {access_token}"}

        def _folder_exists(root: str) -> bool:
            device_folder = _device_folder_name(device)
            path = f"{root}/{device_folder}/{pid}"
            encoded = quote(path, safe="/")
            url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded}"
            resp = requests.get(url, headers=headers)
            return resp.status_code == 200

        return {
            "in_final": _folder_exists(settings.ROOT_FOLDER_PATH),
            "in_qc": _folder_exists(settings.QC_ROOT_FOLDER_PATH),
        }
    except Exception as e:
        st.error(f"Error checking participant folder: {e}")
        return {"in_final": False, "in_qc": False}


def find_file(access_token, folder_path, filename, root_path=None):
    """Find a file in SharePoint folder. Returns file info dict or None."""
    try:
        drive_id = get_drive_id(access_token)
        if root_path is None:
            root_path = settings.ROOT_FOLDER_PATH

        full_path = f"{root_path}/{folder_path}{filename}"
        encoded_path = quote(full_path, safe="/")
        
        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "id": data["id"],
                "name": data["name"],
                "webUrl": data.get("webUrl", ""),
                "downloadUrl": data.get("@microsoft.graph.downloadUrl", "")
            }
        return None
    except Exception as e:
        st.error(f"Error finding file: {e}")
        return None


def list_pdfs_in_subfolder(access_token, folder_path, subfolder):
    """List all PDFs in a subfolder under the participant results folder."""
    try:
        drive_id = get_drive_id(access_token)
        full_path = f"{settings.ROOT_FOLDER_PATH}/{folder_path}{subfolder}".rstrip("/")
        encoded_path = quote(full_path, safe="/")

        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/children"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            return []

        pdf_files = []
        for file_data in resp.json().get("value", []):
            name = file_data.get("name", "")
            if name.lower().endswith(".pdf"):
                pdf_files.append({
                    "id": file_data["id"],
                    "name": name,
                    "webUrl": file_data.get("webUrl", ""),
                    "downloadUrl": file_data.get("@microsoft.graph.downloadUrl", ""),
                })

        return sorted(pdf_files, key=lambda item: item["name"].lower())
    except Exception as e:
        st.error(f"Error listing summary PDFs: {e}")
        return []


def download_csv(access_token, file_id):
    """Download CSV file and return as DataFrame."""
    try:
        drive_id = get_drive_id(access_token)
        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{file_id}/content"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        return pd.read_csv(io.StringIO(resp.content.decode("utf-8")))
    except Exception as e:
        st.error(f"Error downloading CSV: {e}")
        return None


def build_versioned_filename(base_filename, username):
    """Build filename as {base}_{username}_{YYYYMMDD_HHMMSS}.{ext}."""
    name_part, ext = base_filename.rsplit(".", 1) if "." in base_filename else (base_filename, "csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name_part}_{username}_{timestamp}.{ext}"


def get_next_version(access_token, folder_path, base_filename, username):
    """Get next version number by checking existing files."""
    try:
        drive_id = get_drive_id(access_token)
        full_path = f"{settings.ROOT_FOLDER_PATH}/{folder_path}".rstrip("/")
        encoded_path = quote(full_path, safe="/")
        
        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/children"
        resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        
        name_part = base_filename.rsplit(".", 1)[0] if "." in base_filename else base_filename
        prefix = f"{name_part}_{username}_v"
        max_version = 0
        
        for file in resp.json().get("value", []):
            fname = file["name"]
            if fname.startswith(prefix):
                try:
                    version_str = fname[len(prefix):].split(".")[0]
                    max_version = max(max_version, int(version_str))
                except (ValueError, IndexError):
                    continue
        
        return max_version + 1
    except Exception:
        return 1


def upload_csv(access_token, folder_path, base_filename, dataframe, username="unknown_user", root_path=None):
    """Upload DataFrame as versioned CSV file.
    
    root_path: SharePoint root to save under. Defaults to QC_ROOT_FOLDER_PATH so that
               edits are always written to GGIR_QC_outputs, not the source GGIR_final_outputs.
    """
    if root_path is None:
        root_path = settings.QC_ROOT_FOLDER_PATH
    try:
        drive_id = get_drive_id(access_token)
        new_filename = build_versioned_filename(base_filename, username)
        
        full_path = f"{root_path}/{folder_path}{new_filename}"
        encoded_path = quote(full_path, safe="/")
        
        csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/content"
        
        resp = requests.put(url, headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "text/csv"
        }, data=csv_bytes)
        resp.raise_for_status()
        
        data = resp.json()
        return {"id": data["id"], "name": data["name"], "webUrl": data.get("webUrl", "")}
    except Exception as e:
        st.error(f"Error uploading file: {e}")
        return None


def _validate_activity_payload(log_row):
    """Validate required activity-log values before writing to Excel."""
    missing = []
    for key in settings.ACTIVITY_LOG_HEADERS[:-1]:  # timestamp is generated server-side
        value = log_row.get(key)
        if value is None or str(value).strip() == "":
            missing.append(key)
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    return True, ""


def log_to_sharepoint(access_token, log_row, root_path=None):
    """Append one activity row into the configured SharePoint CSV file.

    Args:
        access_token: Microsoft Graph access token.
        log_row: Dict containing activity values for ACTIVITY_LOG_HEADERS except timestamp.
        root_path: Optional SharePoint root path, defaults to QC root.

    Returns:
        dict with keys: success (bool), error (str), timestamp (str).
    """
    if root_path is None:
        root_path = settings.QC_ROOT_FOLDER_PATH

    is_valid, validation_error = _validate_activity_payload(log_row)
    if not is_valid:
        return {"success": False, "error": validation_error}

    timestamp = datetime.now(timezone.utc).isoformat()
    row_values = {**log_row, "timestamp_QC'ed": timestamp}

    try:
        drive_id = get_drive_id(access_token)
        headers = {"Authorization": f"Bearer {access_token}"}

        csv_path = f"{root_path}/{settings.ACTIVITY_LOG_FILE}"
        encoded_path = quote(csv_path, safe="/")
        content_url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/content"

        # Download current CSV if it exists.
        get_resp = requests.get(content_url, headers=headers)
        expected_headers = settings.ACTIVITY_LOG_HEADERS
        if get_resp.status_code == 404:
            current_df = pd.DataFrame(columns=expected_headers)
        else:
            get_resp.raise_for_status()
            content = get_resp.content.decode("utf-8-sig")
            if content.strip():
                current_df = pd.read_csv(io.StringIO(content))
            else:
                current_df = pd.DataFrame(columns=expected_headers)

        if list(current_df.columns) != expected_headers:
            return {
                "success": False,
                "error": (
                    "Header mismatch in activity log CSV. "
                    f"Expected {expected_headers} but found {list(current_df.columns)}"
                ),
            }

        updated_df = pd.concat(
            [current_df, pd.DataFrame([row_values], columns=expected_headers)],
            ignore_index=True,
        )
        csv_bytes = updated_df.to_csv(index=False).encode("utf-8")

        put_resp = requests.put(
            content_url,
            headers={
                **headers,
                "Content-Type": "text/csv",
            },
            data=csv_bytes,
        )
        if put_resp.status_code in {409, 423}:
            return {
                "success": False,
                "error": "Activity log file is locked or has a write conflict. Please retry.",
            }
        put_resp.raise_for_status()

        return {"success": True, "timestamp": timestamp}
    except Exception as e:
        return {"success": False, "error": f"Failed to log activity: {e}"}