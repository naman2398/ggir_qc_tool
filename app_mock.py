"""Mock App for Local UI Testing — real src/ui/ components, stubbed SharePoint API."""

import streamlit as st
import pandas as pd
from unittest.mock import patch

from config import settings
from src.auth.user_auth import extract_username_from_email
from src.ui.search_interface import render_search_interface
from src.ui.file_viewer import render_file_viewer

# ── Mock credentials ──────────────────────────────────────────────────────────
MOCK_TOKEN = "mock-access-token"
MOCK_USERS = ["test@example.com", "admin@example.com"]

# ── Mock SharePoint data ──────────────────────────────────────────────────────
MOCK_CSV_DATA = pd.DataFrame({
    "ID":            ["P001", "P002", "P003", "P004", "P005"],
    "filename":      ["file1.bin", "file2.bin", "file3.bin", "file4.bin", "file5.bin"],
    "device_serial": ["ABC123", "DEF456", "GHI789", "JKL012", "MNO345"],
    "start_time":    ["2025-01-01 08:00", "2025-01-02 09:00", "2025-01-03 10:00",
                      "2025-01-04 11:00", "2025-01-05 12:00"],
    "end_time":      ["2025-01-08 08:00", "2025-01-09 09:00", "2025-01-10 10:00",
                      "2025-01-11 11:00", "2025-01-12 12:00"],
    "QC_status":     ["Pass", "Fail", "Pending", "Pass", "Fail"],
    "notes":         ["Good data", "Missing days", "Review needed", "Complete", "Signal lost"],
})

MOCK_CSV_FILE = {
    "id": "mock-csv-id",
    "name": settings.TARGET_FILES["csv"],
    "webUrl": "https://example.com/data.csv",
    "downloadUrl": "",
}
MOCK_PDF_SLEEP = {
    "id": "mock-pdf-sleep",
    "name": settings.TARGET_FILES["pdf_sleep"],
    "webUrl": "https://example.com/sleep.pdf",
    "downloadUrl": "",
}
MOCK_SUMMARY_PDFS = [
    {"id": "mock-pdf-1", "name": "summary_report_part1.pdf",
     "webUrl": "https://example.com/summary1.pdf", "downloadUrl": ""},
    {"id": "mock-pdf-2", "name": "summary_report_part2.pdf",
     "webUrl": "https://example.com/summary2.pdf", "downloadUrl": ""},
]


# ── Stub functions (replace real SharePoint calls) ────────────────────────────
def _stub_find_file(_token, _folder, filename):
    if filename == settings.TARGET_FILES["csv"]:
        return MOCK_CSV_FILE
    if filename == settings.TARGET_FILES["pdf_sleep"]:
        return MOCK_PDF_SLEEP
    return None


def _stub_list_pdfs(_token, _folder, _subfolder):
    return MOCK_SUMMARY_PDFS


def _stub_download_csv(_token, _file_id):
    return MOCK_CSV_DATA.copy()


def _stub_upload_csv(_token, _folder, base_filename, dataframe, username="unknown_user"):
    from src.api.file_operations import build_versioned_filename
    name = build_versioned_filename(base_filename, username)
    st.toast(f"💾 Mock save: {name}")
    return {"id": "mock-saved-id", "name": name, "webUrl": "https://example.com/saved.csv"}


# ── Mock sidebar (mirrors exact session state keys of real sidebar) ────────────
def mock_render_sidebar():
    """Same session state contract as src/ui/sidebar.py — no Azure/MSAL calls."""
    if st.session_state.get("authorized") and st.session_state.get("access_token"):
        with st.sidebar:
            st.header("🔐 Login")
            st.success(f"✅ {st.session_state.get('user_email', '')}")
            st.caption(f"👤 Username: **{st.session_state.get('username', '')}**")
            if st.button("Logout"):
                for key in ["authorized", "access_token", "user_email", "username",
                            "participant_id", "device", "phase", "folder_path",
                            "csv_file", "pdf_file_sleep", "pdf_file_data",
                            "data_editor_version", "last_saved_file",
                            "original_df", "current_df"]:
                    st.session_state.pop(key, None)
                st.rerun()
        return True

    with st.sidebar:
        st.header("🔐 Login")
        email_input = st.text_input("Email", placeholder="name@stonybrook.edu")
        password_input = st.text_input("Password", type="password",
                                       placeholder="Enter access password")
        login_button = st.button("Login", type="primary")

        if login_button:
            if email_input in MOCK_USERS and password_input:
                st.session_state["authorized"] = True
                st.session_state["access_token"] = MOCK_TOKEN
                st.session_state["user_email"] = email_input.strip().lower()
                st.session_state["username"] = extract_username_from_email(email_input)
                st.rerun()
            elif not email_input or "@" not in email_input:
                st.error("Please enter a valid email address.")
            else:
                st.error("❌ Not authorized. Use: test@example.com or admin@example.com")
                st.session_state["authorized"] = False
                st.stop()
        else:
            st.info("Please enter your email and access password.")
            st.stop()

    return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="GGIR QC Tool", page_icon="📊", layout="wide")
    st.title("GGIR QC Tool")
    st.caption("🧪 **Mock mode** — real UI components, stubbed SharePoint. "
               "Login: `test@example.com` / any password.")
    st.markdown("---")

    if not mock_render_sidebar():
        st.stop()

    # Patch the four SharePoint calls used by the real UI components
    with patch("src.ui.search_interface.find_file",           side_effect=_stub_find_file), \
         patch("src.ui.search_interface.list_pdfs_in_subfolder", side_effect=_stub_list_pdfs), \
         patch("src.ui.file_viewer.download_csv",             side_effect=_stub_download_csv), \
         patch("src.ui.file_viewer.upload_csv",               side_effect=_stub_upload_csv):

        files_found, _ = render_search_interface()

        if files_found or st.session_state.get("participant_id"):
            render_file_viewer()


if __name__ == "__main__":
    main()

