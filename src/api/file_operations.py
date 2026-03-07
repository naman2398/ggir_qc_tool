"""
SharePoint File Operations via Microsoft Graph API
"""

import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime
from urllib.parse import quote
from config import settings


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
    if phase:
        return settings.PATH_TEMPLATE_PHASED.format(device=device, phase=phase, pid=participant_id)
    return settings.PATH_TEMPLATE_STANDARD.format(device=device, pid=participant_id)


def build_participant_phase_folder_path(device, participant_id, phase):
    """Build the post-migration participant-first path for a specific phase."""
    return settings.PATH_TEMPLATE_PARTICIPANT_PHASED.format(
        device=device, pid=participant_id, phase=phase
    )


def find_all_phase_files(access_token, device, participant_id):
    """
    For phased devices (Actical, Philips Health Band): find files across ALL phases
    for a given participant. Only phases that have at least one file are included.

    Returns a list of dicts, one per phase with data:
        [
            {
                "phase":         str,
                "folder_path":   str,   # relative path ending in results/
                "csv_file":      dict | None,
                "pdf_file_sleep": dict | None,
                "pdf_file_data": list[dict],
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
        if any([csv_file, pdf_sleep, pdf_data]):
            results.append({
                "phase": phase,
                "folder_path": folder_path,
                "csv_file": csv_file,
                "pdf_file_sleep": pdf_sleep,
                "pdf_file_data": pdf_data,
            })
    return results


def find_file(access_token, folder_path, filename):
    """Find a file in SharePoint folder. Returns file info dict or None."""
    try:
        drive_id = get_drive_id(access_token)
        full_path = f"{settings.ROOT_FOLDER_PATH}/{folder_path}{filename}"
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


def upload_csv(access_token, folder_path, base_filename, dataframe, username="unknown_user"):
    """Upload DataFrame as versioned CSV file."""
    try:
        drive_id = get_drive_id(access_token)
        new_filename = build_versioned_filename(base_filename, username)
        
        full_path = f"{settings.ROOT_FOLDER_PATH}/{folder_path}{new_filename}"
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