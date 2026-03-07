"""Search Interface UI Component"""

import streamlit as st
from config import settings
from src.api.file_operations import (
    build_folder_path,
    find_file,
    find_all_phase_files,
    list_pdfs_in_subfolder,
)

_PHASED_KEYS_PREFIX = ("original_df_", "current_df_", "data_editor_version_", "last_saved_file_")


def _clear_file_state():
    """Clear all participant/file session state so a new search starts fresh."""
    # Fixed keys
    for key in [
        "participant_id", "device", "phase", "folder_path",
        "csv_file", "pdf_file_sleep", "pdf_file_data",
        "original_df", "current_df", "data_editor_version", "last_saved_file",
        "phase_files",
    ]:
        st.session_state.pop(key, None)

    # Per-phase namespaced keys (e.g. original_df_Baseline, data_editor_version_Overnight)
    phased_keys = [
        k for k in list(st.session_state.keys())
        if any(k.startswith(prefix) for prefix in _PHASED_KEYS_PREFIX)
    ]
    for k in phased_keys:
        st.session_state.pop(k, None)


def render_search_interface():
    """Render file search interface. Returns (success, search_performed)."""
    st.header("🔍 Find Participant Data")

    col1, col2 = st.columns([1, 1])

    with col1:
        device_options = ["Select Device Type..."] + settings.SUPPORTED_DEVICES
        selected_device = st.selectbox("Device Type", device_options, on_change=_clear_file_state)

    # Show default message if no device selected
    if selected_device == "Select Device Type...":
        st.info("👆 Please select a device type to begin searching for participant data.")
        return False, False

    # Phased devices (Actical, Philips Health Band) no longer need a phase dropdown —
    # the app fetches all phases automatically.
    is_phased_device = selected_device in settings.DEVICE_PHASE_MAPPING

    with col2:
        participant_id = st.text_input("Participant ID", placeholder="e.g., PID123")

    if is_phased_device:
        st.caption(
            f"ℹ️ All study phases for **{selected_device}** will be fetched automatically."
        )

    search_button = st.button("🔎 Search Files", type="primary")

    if search_button and participant_id:
        _clear_file_state()
        with st.spinner("Searching for files..."):
            access_token = st.session_state.get("access_token")
            if not access_token:
                st.error("❌ Not authenticated. Please login first.")
                return False, True

            # -------------------------------------------------------------------
            # Phased devices: search across all phases automatically
            # -------------------------------------------------------------------
            if is_phased_device:
                st.info(
                    f"📁 Searching all phases under: "
                    f"`{settings.ROOT_FOLDER_PATH}/{selected_device}/{participant_id}/`"
                )
                phase_files = find_all_phase_files(access_token, selected_device, participant_id)

                if not phase_files:
                    st.error(f"❌ No files found for **{selected_device} / {participant_id}** in any study phase.")
                    st.info("Please verify the device type and participant ID.")
                    return False, True

                phases_found = [pf["phase"] for pf in phase_files]
                st.success(f"✅ Found data in {len(phase_files)} phase(s): {', '.join(phases_found)}")

                st.session_state["participant_id"] = participant_id
                st.session_state["device"] = selected_device
                st.session_state["phase"] = None        # not used for phased devices
                st.session_state["phase_files"] = phase_files

            # -------------------------------------------------------------------
            # Non-phased devices: existing single-folder search (unchanged)
            # -------------------------------------------------------------------
            else:
                folder_path = build_folder_path(selected_device, None, participant_id)
                st.info(f"📁 Searching: `{folder_path}`")

                csv_file = find_file(access_token, folder_path, settings.TARGET_FILES["csv"])
                pdf_file_sleep = find_file(access_token, folder_path, settings.TARGET_FILES["pdf_sleep"])
                pdf_file_data = list_pdfs_in_subfolder(
                    access_token, folder_path, settings.TARGET_FILES["pdf_data"]
                )

                if not any([csv_file, pdf_file_sleep, pdf_file_data]):
                    st.error(f"❌ No files found for {selected_device}/{participant_id}")
                    st.info("Please verify the device type and participant ID.")
                    return False, True

                st.success("✅ Found participant folder!")

                st.session_state["participant_id"] = participant_id
                st.session_state["device"] = selected_device
                st.session_state["phase"] = None
                st.session_state["folder_path"] = folder_path
                st.session_state["csv_file"] = csv_file
                st.session_state["pdf_file_sleep"] = pdf_file_sleep
                st.session_state["pdf_file_data"] = pdf_file_data

            st.markdown("---")
            return True, True

    elif search_button:
        st.warning("⚠️ Please enter a Participant ID.")
        return False, True

    return False, False
