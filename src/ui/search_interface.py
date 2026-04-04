"""Search Interface UI Component"""

import pathlib

import streamlit as st
import yaml

from config import settings
from src.api.file_operations import (
    build_folder_path,
    check_participant_folder_exists,
    find_all_phase_files,
    find_file,
    find_qc_csv,
    list_pdfs_in_subfolder,
)
from src.ui.activity_logging import all_activity_state_keys, has_pending_log_decisions, pending_phase_labels

_PARTICIPANTS_FILE = pathlib.Path(settings.PARTICIPANTS_FILE)
_SELECT_PLACEHOLDER = "Select participant..."
_CUSTOM_ID_OPTION = "➕ Enter custom ID..."


def _load_participants() -> dict[str, list[str]]:
    """Load config/participants.yaml. Returns {} if file not found."""
    if not _PARTICIPANTS_FILE.exists():
        return {}
    with _PARTICIPANTS_FILE.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data


def _save_participant(device: str, pid: str) -> None:
    """Append pid to the device list in participants.yaml (no-op if already present)."""
    data = _load_participants()
    device_list = data.get(device, [])
    if str(pid) not in [str(p) for p in device_list]:
        device_list.append(str(pid))
        data[device] = sorted(set(str(p) for p in device_list))
    # Ensure all supported devices are present
    for d in settings.SUPPORTED_DEVICES:
        data.setdefault(d, [])
    _PARTICIPANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _PARTICIPANTS_FILE.open("w", encoding="utf-8") as fh:
        fh.write(
            "# Participant registry — one list per device.\n"
            "# Populated by refresh_participants.py.\n"
            "# Edit freely — re-running the script merges without removing manual entries.\n"
        )
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=True)


_PHASED_KEYS_PREFIX = ("original_df_", "current_df_", "data_editor_version_", "last_saved_file_", "last_saved_url_", "qc_df_")


def _clear_file_state():
    """Clear all participant/file session state so a new search starts fresh."""
    # Fixed keys
    for key in [
        "participant_id", "device", "phase", "folder_path",
        "csv_file", "pdf_file_sleep", "pdf_file_data",
        "original_df", "current_df", "data_editor_version", "last_saved_file",
        "last_saved_url", "qc_csv_file", "phase_files",
    ]:
        st.session_state.pop(key, None)

    # Per-phase namespaced keys (e.g. original_df_Baseline, data_editor_version_Overnight)
    phased_keys = [
        k for k in list(st.session_state.keys())
        if isinstance(k, str) and any(k.startswith(prefix) for prefix in _PHASED_KEYS_PREFIX)
    ]
    for k in phased_keys:
        st.session_state.pop(k, None)

    for k in all_activity_state_keys(st.session_state):
        st.session_state.pop(k, None)


def _clear_file_state_if_allowed():
    """Prevent context clearing while required log/skip decisions are pending."""
    if has_pending_log_decisions(st.session_state):
        phases = ", ".join(pending_phase_labels(st.session_state))
        st.session_state["log_guard_message"] = (
            "Choose Log Activity or Skip Log before leaving this participant. "
            f"Pending phase(s): {phases}"
        )
        return
    _clear_file_state()


def render_search_interface():
    """Render file search interface. Returns (success, search_performed)."""
    st.header("🔍 Find Participant Data")

    if st.session_state.get("log_guard_message"):
        st.error(st.session_state["log_guard_message"])
        st.session_state.pop("log_guard_message", None)

    # ---------- YAML missing warning ----------
    if not _PARTICIPANTS_FILE.exists():
        st.warning(
            "⚠️ Participant registry not found (`config/participants.yaml`). "
            "Run `python refresh_participants.py` to generate it, or use "
            "**➕ Enter custom ID...** below to search by typing a participant ID."
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        device_options = ["Select Device Type..."] + settings.SUPPORTED_DEVICES
        selected_device = st.selectbox("Device Type", device_options, on_change=_clear_file_state_if_allowed)

    if selected_device == "Select Device Type...":
        st.info("👆 Please select a device type to begin searching for participant data.")
        return False, False

    is_phased_device = selected_device in settings.DEVICE_PHASE_MAPPING

    # ---------- Participant id selectbox ----------
    participants = _load_participants().get(selected_device, [])
    if not participants:
        st.warning(
            f"⚠️ No participants found for **{selected_device}** in `config/participants.yaml`. "
            "Use **➕ Add new participant to list** below, or run "
            f"`python refresh_participants.py --device \"{selected_device}\"` "
            "after setting Azure environment variables."
        )
    pid_options = [_SELECT_PLACEHOLDER] + sorted(str(p) for p in participants) + [_CUSTOM_ID_OPTION]

    with col2:
        selected_pid = st.selectbox(
            "Participant ID",
            pid_options,
            key=f"pid_select_{selected_device}",
            on_change=_clear_file_state_if_allowed,
        )

    # Free-text fallback when custom option chosen
    custom_pid = ""
    if selected_pid == _CUSTOM_ID_OPTION:
        custom_pid = st.text_input("Custom Participant ID", placeholder="e.g., PID123")

    # Resolve the actual participant ID to use
    if selected_pid == _SELECT_PLACEHOLDER:
        participant_id = ""
    elif selected_pid == _CUSTOM_ID_OPTION:
        participant_id = custom_pid.strip()
    else:
        participant_id = selected_pid

    if is_phased_device:
        st.caption(
            f"ℹ️ All study phases for **{selected_device}** will be fetched automatically."
        )

    search_button = st.button("🔎 Search Files", type="primary")

    # ---------- Add participant expander ----------
    with st.expander("➕ Add new participant to list"):
        st.caption(
            "The participant folder must exist in **both** "
            "`GGIR_final_outputs` and `GGIR_QC_outputs` under the selected device."
        )
        add_pid_input = st.text_input(
            "Participant ID to add",
            placeholder="e.g., PID999",
            key="add_pid_input",
        )
        if st.button("Add to list", key="add_pid_button"):
            if not add_pid_input.strip():
                st.warning("⚠️ Please enter a participant ID.")
            else:
                add_pid = add_pid_input.strip()
                access_token = st.session_state.get("access_token")
                if not access_token:
                    st.error("❌ Not authenticated. Please login first.")
                else:
                    existing = _load_participants().get(selected_device, [])
                    if str(add_pid) in [str(p) for p in existing]:
                        st.info(f"ℹ️ **{add_pid}** is already in the list for {selected_device}.")
                    else:
                        with st.spinner("Checking SharePoint folders…"):
                            presence = check_participant_folder_exists(
                                access_token, selected_device, add_pid
                            )
                        if not presence["in_final"] or not presence["in_qc"]:
                            missing = []
                            if not presence["in_final"]:
                                missing.append("GGIR_final_outputs")
                            if not presence["in_qc"]:
                                missing.append("GGIR_QC_outputs")
                            st.error(
                                f"❌ No data folder found for **{add_pid}** under "
                                f"**{selected_device}** in: {', '.join(missing)}. "
                                "Ensure the folder exists in both roots before adding."
                            )
                        else:
                            _save_participant(selected_device, add_pid)
                            st.success(
                                f"✅ **{add_pid}** added to the {selected_device} participant list. "
                                "It will appear in the dropdown immediately."
                            )
                            st.rerun()

    # ---------- Search ----------
    if search_button and participant_id:
        if has_pending_log_decisions(st.session_state):
            phases = ", ".join(pending_phase_labels(st.session_state))
            st.error(
                "❌ Cannot switch context yet. Choose Log Activity or Skip Log first for: "
                f"{phases}"
            )
            return False, True

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
                qc_csv_file = find_qc_csv(access_token, folder_path)

                if not any([csv_file, pdf_file_sleep, pdf_file_data, qc_csv_file]):
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
                st.session_state["qc_csv_file"] = qc_csv_file

            st.markdown("---")
            return True, True

    elif search_button and selected_pid == _SELECT_PLACEHOLDER:
        st.warning("⚠️ Please select or enter a Participant ID.")
        return False, True

    elif search_button and selected_pid == _CUSTOM_ID_OPTION and not custom_pid.strip():
        st.warning("⚠️ Please enter a custom Participant ID in the text box.")
        return False, True

    return False, False
