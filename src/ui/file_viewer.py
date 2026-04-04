"""File Viewer UI Component"""

import streamlit as st
from config import settings
from src.api.file_operations import (
    delete_file_by_id,
    download_csv,
    log_to_sharepoint,
    remove_last_activity_log_for_scope,
    upload_csv,
)
from src.ui.activity_logging import (
    DECISION_LOGGED,
    DECISION_SKIPPED,
    activity_rows_key,
    comment_key,
    decision_key,
    last_entry_key,
    modified_key,
    pending_phase_labels,
    saved_files_key,
)


def _df_with_delete_col(df):
    """Prepend a _to_delete bool column (all False) to a dataframe."""
    result = df.copy()
    result.insert(0, "_to_delete", False)
    return result


def _render_readonly_csv(qc_csv_file, access_token, state_suffix):
    """Render a read-only view of the full QC summary CSV."""
    key_qc_df = f"qc_df{state_suffix}"

    if not qc_csv_file:
        st.info(f"ℹ️ {settings.TARGET_FILES['csv_full']} not found at results/QC/")
        return

    col_title, col_link = st.columns([3, 1])
    with col_title:
        st.markdown(f"**{settings.TARGET_FILES['csv_full']}**")
    with col_link:
        if qc_csv_file.get("webUrl"):
            st.markdown(f"[🔗 Open in SharePoint]({qc_csv_file['webUrl']})")

    if key_qc_df not in st.session_state:
        df = download_csv(access_token, qc_csv_file["id"])
        if df is None:
            st.error("❌ Failed to load full summary file.")
            return
        st.session_state[key_qc_df] = df

    df = st.session_state[key_qc_df]
    st.caption(f"📊 {len(df)} rows × {len(df.columns)} columns")
    st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# Single-phase viewer (non-phased devices: ActiwatchL, FitBit, FDG Actical)
# =============================================================================

def _render_single_phase_viewer(
    participant_id, device, phase, folder_path,
    csv_file, pdf_file_sleep, pdf_file_data,
    access_token, username,
):
    """Render file viewer for a single-phase (non-phased) device."""
    st.header("📂 Participant Files")

    path_display = f"{device}" + (f" / {phase}" if phase else "") + f" / {participant_id}"
    st.info(f"📁 **Path**: {path_display}")

    # PDF links
    st.subheader("📄 Reports (Read-Only)")
    col1, col2 = st.columns(2)

    with col1:
        if pdf_file_sleep:
            st.markdown(f"**{settings.TARGET_FILES['pdf_sleep']}**")
            st.markdown(f"[🔗 Open PDF]({pdf_file_sleep['webUrl']})")
        else:
            st.warning(f"⚠️ {settings.TARGET_FILES['pdf_sleep']} not found")

    with col2:
        if pdf_file_data:
            st.markdown(f"**{settings.TARGET_FILES['pdf_data']}**")
            for pdf in pdf_file_data:
                st.markdown(f"- [🔗 {pdf['name']}]({pdf['webUrl']})")
        else:
            st.warning(f"⚠️ No PDFs found under {settings.TARGET_FILES['pdf_data']}")

    st.markdown("---")

    # Read-only QC full CSV
    st.subheader("📋 Full Summary Data (Read-Only)")
    _render_readonly_csv(
        qc_csv_file=st.session_state.get("qc_csv_file"),
        access_token=access_token,
        state_suffix="",
    )

    st.markdown("---")

    # Editable CSV
    st.subheader("✏️ Edit Data File")
    _render_csv_editor(
        csv_file=csv_file,
        folder_path=folder_path,
        access_token=access_token,
        username=username,
        state_suffix="",          # no suffix → uses original_df, current_df, etc.
        phase_label=phase or "NoPhase",
    )


# =============================================================================
# Multi-phase viewer (Actical, Philips Health Band)
# =============================================================================

def _render_multi_phase_viewer(phase_files, access_token, username, participant_id, device):
    """Render file viewer for a phased device, showing all phases together."""
    st.header("📂 Participant Files")
    st.info(f"📁 **Path**: {device} / {participant_id}  —  {len(phase_files)} phase(s) found")

    # ------------------------------------------------------------------
    # PDFs: one labelled section per phase
    # ------------------------------------------------------------------
    st.subheader("📄 Reports (Read-Only)")

    for pf in phase_files:
        phase = pf["phase"]
        pdf_sleep = pf["pdf_file_sleep"]
        pdf_data = pf["pdf_file_data"]

        if not pdf_sleep and not pdf_data:
            continue

        with st.expander(f"📑 {phase}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                if pdf_sleep:
                    st.markdown(f"**{settings.TARGET_FILES['pdf_sleep']}**")
                    st.markdown(f"[🔗 Open — {phase}]({pdf_sleep['webUrl']})")
                else:
                    st.warning(f"⚠️ {settings.TARGET_FILES['pdf_sleep']} not found")
            with col2:
                if pdf_data:
                    st.markdown(f"**{settings.TARGET_FILES['pdf_data']}**")
                    for pdf in pdf_data:
                        st.markdown(f"- [🔗 {pdf['name']} — {phase}]({pdf['webUrl']})")
                else:
                    st.warning(f"⚠️ No PDFs found under {settings.TARGET_FILES['pdf_data']}")

    st.markdown("---")

    # ------------------------------------------------------------------
    # Read-only QC full CSVs: one tab per phase
    # ------------------------------------------------------------------
    st.subheader("📋 Full Summary Data (Read-Only)")

    qc_phases = [pf for pf in phase_files if pf.get("qc_csv_file")]
    if not qc_phases:
        st.info(f"ℹ️ {settings.TARGET_FILES['csv_full']} not found in any phase.")
    else:
        qc_tab_labels = [pf["phase"] for pf in qc_phases]
        qc_tabs = st.tabs(qc_tab_labels)
        for tab, pf in zip(qc_tabs, qc_phases):
            with tab:
                _render_readonly_csv(
                    qc_csv_file=pf["qc_csv_file"],
                    access_token=access_token,
                    state_suffix=f"_qc_{pf['phase']}",
                )

    st.markdown("---")

    # ------------------------------------------------------------------
    # CSVs: one tab per phase
    # ------------------------------------------------------------------
    st.subheader("✏️ Edit Data Files")

    csv_phases = [pf for pf in phase_files if pf["csv_file"]]
    if not csv_phases:
        st.warning(f"⚠️ {settings.TARGET_FILES['csv']} not found in any phase.")
        return

    tab_labels = [pf["phase"] for pf in csv_phases]
    tabs = st.tabs(tab_labels)

    for tab, pf in zip(tabs, csv_phases):
        with tab:
            _render_csv_editor(
                csv_file=pf["csv_file"],
                folder_path=pf["folder_path"],
                access_token=access_token,
                username=username,
                state_suffix=f"_{pf['phase']}",   # e.g. _Baseline, _Overnight
                phase_label=pf["phase"],
            )


# =============================================================================
# Shared CSV editor (used by both single and multi-phase viewers)
# =============================================================================

def _render_activity_log_panel(access_token, phase_label, panel_key_suffix):
    """Render per-phase activity logging controls and persist explicit decision."""
    participant_id = st.session_state.get("participant_id")
    monitor = st.session_state.get("device")
    user_email = st.session_state.get("user_email")

    if not participant_id or not monitor or not user_email:
        st.warning("⚠️ Missing participant or user context. Activity logging is unavailable.")
        return

    d_key = decision_key(participant_id, monitor, phase_label)
    c_key = comment_key(participant_id, monitor, phase_label)
    m_key = modified_key(participant_id, monitor, phase_label)
    l_key = last_entry_key(participant_id, monitor, phase_label)
    rows_key = activity_rows_key(participant_id, monitor, phase_label)
    reset_key = f"log_reset::{panel_key_suffix}"
    status_key = f"log_status::{panel_key_suffix}"

    # Apply pending widget resets before rendering widgets for this run.
    if st.session_state.pop(reset_key, False):
        st.session_state[c_key] = ""
        st.session_state[m_key] = False

    st.session_state.setdefault(c_key, "")
    st.session_state.setdefault(m_key, False)

    st.subheader("📝 Log Activity")
    st.caption(f"Phase: {phase_label}")

    status = st.session_state.pop(status_key, None)
    if status:
        level = status.get("level")
        text = status.get("text", "")
        if level == "success":
            st.success(text)
        elif level == "warning":
            st.warning(text)
        elif level == "info":
            st.info(text)
        elif level == "error":
            st.error(text)

    st.text_area(
        "Comments",
        key=c_key,
        height=100,
        placeholder="Describe your QC findings or changes...",
    )
    st.checkbox("Data Modified", key=m_key)

    st.session_state.setdefault(rows_key, [])

    col_log, col_skip, col_clear = st.columns(3)
    with col_log:
        log_clicked = st.button(
            "Log Activity",
            type="primary",
            key=f"log_activity_{panel_key_suffix}",
        )
    with col_skip:
        skip_clicked = st.button(
            "Skip Log",
            key=f"skip_log_{panel_key_suffix}",
            help="Choose this when you explicitly do not want to create a log row.",
        )
    with col_clear:
        clear_clicked = st.button("Clear logged activity", key=f"clear_log_{panel_key_suffix}")

    if clear_clicked:
        logged_rows = st.session_state.get(rows_key, [])
        if not logged_rows:
            st.session_state[status_key] = {
                "level": "warning",
                "text": "No session log entry to clear for this phase.",
            }
            st.rerun()

        latest_row = logged_rows[-1]
        result = remove_last_activity_log_for_scope(
            access_token=access_token,
            participant_id=participant_id,
            monitor=monitor,
            phase_label=phase_label,
            timestamp=latest_row.get("timestamp_QC'ed"),
        )
        if result.get("success"):
            st.session_state[rows_key] = logged_rows[:-1]
            st.session_state.pop(l_key, None)
            st.session_state[status_key] = {"level": "success", "text": "✅ Logged activity cleared."}
        else:
            st.session_state[status_key] = {
                "level": "error",
                "text": f"❌ Clear failed: {result.get('error', 'Unknown error')}",
            }
        st.rerun()

    if skip_clicked:
        st.session_state[d_key] = DECISION_SKIPPED
        st.session_state[reset_key] = True
        st.session_state.pop(l_key, None)
        st.session_state[status_key] = {
            "level": "warning",
            "text": f"Logging skipped for {phase_label}. You can still submit a log before leaving.",
        }
        st.rerun()

    if log_clicked:
        comments = st.session_state.get(c_key, "").strip()
        qc_outcome = "Data Modified" if st.session_state.get(m_key, False) else "Data Not Modified"
        payload = {
            "User_email": user_email,
            "Monitor": monitor,
            "Participant_ID": participant_id,
            "Study_Phase": phase_label,
            "QC_Outcome": qc_outcome,
            "Comments": comments,
        }

        with st.spinner("Submitting activity log..."):
            result = log_to_sharepoint(access_token, payload)

        if result.get("success"):
            st.session_state[d_key] = DECISION_LOGGED
            latest_entry = {
                **payload,
                "timestamp_QC'ed": result.get("timestamp"),
            }
            st.session_state[l_key] = latest_entry
            st.session_state[rows_key] = st.session_state.get(rows_key, []) + [latest_entry]
            st.session_state[reset_key] = True
            st.session_state[status_key] = {"level": "success", "text": "✅ Activity logged successfully."}
            st.rerun()
        else:
            st.error(f"❌ Log failed: {result.get('error', 'Unknown error')}")

    last_entry = st.session_state.get(l_key)
    if last_entry:
        st.caption(
            "Last submission this session: "
            f"{last_entry.get('timestamp_QC\'ed', '')} | "
            f"{last_entry.get('QC_Outcome', '')}"
        )


def _render_csv_editor(csv_file, folder_path, access_token, username, state_suffix, phase_label):
    """
    Render an editable CSV data_editor block.

    state_suffix: appended to all session_state keys so that multiple phases
    can each have independent editor state. Empty string for single-phase.
    """
    key_original = f"original_df{state_suffix}"
    key_current = f"current_df{state_suffix}"
    key_version = f"data_editor_version{state_suffix}"
    key_last_saved = f"last_saved_file{state_suffix}"
    key_last_saved_url = f"last_saved_url{state_suffix}"
    participant_id = st.session_state.get("participant_id")
    monitor = st.session_state.get("device")
    tracked_saves_key = saved_files_key(participant_id, monitor, phase_label)
    st.session_state.setdefault(tracked_saves_key, [])

    if not csv_file:
        st.warning(f"⚠️ {settings.TARGET_FILES['csv']} not found")
        return

    # Original file link
    col_title, col_link = st.columns([3, 1])
    with col_title:
        st.markdown(f"**{settings.TARGET_FILES['csv']}**")
    with col_link:
        if csv_file.get("webUrl"):
            st.markdown(f"[🔗 Open original in SharePoint]({csv_file['webUrl']})")

    last_saved = st.session_state.get(key_last_saved)
    last_saved_url = st.session_state.get(key_last_saved_url)
    if last_saved:
        scol1, scol2 = st.columns([3, 1])
        with scol1:
            st.success(f"✅ Last saved as: **{last_saved}**")
        with scol2:
            if last_saved_url:
                st.markdown(f"[🔗 Open saved file in SharePoint]({last_saved_url})")

    if key_original not in st.session_state:
        df = download_csv(access_token, csv_file["id"])
        if df is not None:
            st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
            st.session_state[key_original] = df.copy()
            st.session_state[key_current] = _df_with_delete_col(df)
        else:
            st.error("❌ Failed to load CSV file.")
            return

    version = st.session_state.get(key_version, 0)
    edited_df = st.data_editor(
        st.session_state[key_current],
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "_to_delete": st.column_config.CheckboxColumn(
                "🗑️ Delete",
                help="Check to mark this row for deletion. Marked rows are removed when you save.",
                default=False,
            )
        },
        key=f"data_editor{state_suffix}_{version}",
    )

    rows_to_delete = int(edited_df["_to_delete"].sum())
    data_changed = not edited_df.equals(st.session_state[key_current])

    # Red-highlighted preview of rows marked for deletion
    if rows_to_delete > 0:
        st.warning(
            f"🗑️ **{rows_to_delete} row(s) marked for deletion** — "
            "shown in red below. They will be removed when you save."
        )

        def _highlight_deleted(row):
            if row["_to_delete"]:
                return ["background-color: #ffcccc; color: #8b0000; text-decoration: line-through"] * len(row)
            return [""] * len(row)

        st.dataframe(
            edited_df.style.apply(_highlight_deleted, axis=1),
            use_container_width=True,
            hide_index=True,
        )

    col_save_modified, col_save_unchanged, col_undo, col_status = st.columns([1.3, 1.6, 1.1, 2.2])
    with col_save_modified:
        save_button = st.button(
            "Save with data modifications",
            type="primary",
            disabled=not data_changed,
            key=f"save_btn{state_suffix}",
        )
    with col_save_unchanged:
        save_without_changes_button = st.button(
            "Save without data modifications",
            key=f"save_without_btn{state_suffix}",
        )
    with col_undo:
        tracked_saves = st.session_state.get(tracked_saves_key, [])
        undo_button = st.button(
            "Undo saved changes",
            disabled=len(tracked_saves) == 0,
            key=f"undo_save_btn{state_suffix}",
        )
    with col_status:
        st.warning("⚠️ Unsaved changes") if data_changed else st.success("✅ All changes saved")

    if undo_button:
        tracked_saves = st.session_state.get(tracked_saves_key, [])
        if not tracked_saves:
            st.warning("⚠️ No saved files from this session to undo.")
        else:
            latest_file = tracked_saves[-1]
            delete_result = delete_file_by_id(access_token, latest_file.get("id"))
            if delete_result.get("success"):
                updated_history = tracked_saves[:-1]
                st.session_state[tracked_saves_key] = updated_history
                if updated_history:
                    st.session_state[key_last_saved] = updated_history[-1].get("name")
                    st.session_state[key_last_saved_url] = updated_history[-1].get("webUrl", "")
                else:
                    st.session_state.pop(key_last_saved, None)
                    st.session_state.pop(key_last_saved_url, None)
                st.success("✅ Last saved file was removed from SharePoint.")
                st.rerun()
            else:
                st.error(f"❌ Undo failed: {delete_result.get('error', 'Unknown error')}")

    if save_button and data_changed:
        save_df = (
            edited_df[~edited_df["_to_delete"]]
            .drop(columns=["_to_delete"])
            .reset_index(drop=True)
        )
        if save_df.empty:
            st.error("❌ Cannot save: all rows are marked for deletion.")
        else:
            with st.spinner("Saving new version..."):
                new_file = upload_csv(
                    access_token, folder_path,
                    settings.TARGET_FILES["csv"], save_df, username,
                )
                if new_file:
                    st.session_state[key_original] = save_df.copy()
                    st.session_state[key_current] = _df_with_delete_col(save_df)
                    st.session_state[key_last_saved] = new_file["name"]
                    st.session_state[key_last_saved_url] = new_file.get("webUrl", "")
                    st.session_state[tracked_saves_key] = st.session_state.get(tracked_saves_key, []) + [new_file]
                    st.session_state[key_version] = version + 1
                    st.rerun()
                else:
                    st.error("❌ Failed to save. Please try again.")

    if save_without_changes_button:
        unchanged_df = st.session_state[key_original].copy()
        with st.spinner("Saving unchanged copy..."):
            new_file = upload_csv(
                access_token,
                folder_path,
                settings.TARGET_FILES["csv"],
                unchanged_df,
                username,
                filename_tag="unchanged",
            )
            if new_file:
                st.session_state[key_last_saved] = new_file["name"]
                st.session_state[key_last_saved_url] = new_file.get("webUrl", "")
                st.session_state[tracked_saves_key] = st.session_state.get(tracked_saves_key, []) + [new_file]
                st.success("✅ Unchanged copy saved to SharePoint.")
                st.rerun()
            else:
                st.error("❌ Failed to save unchanged copy. Please try again.")

    st.markdown("---")
    _render_activity_log_panel(
        access_token=access_token,
        phase_label=phase_label,
        panel_key_suffix=(phase_label or "NoPhase").replace(" ", "_").replace("/", "_"),
    )


# =============================================================================
# Entry point
# =============================================================================

def render_file_viewer():
    """Render the file viewer and editor interface."""
    if not st.session_state.get("participant_id"):
        return

    st.session_state.setdefault("data_editor_version", 0)

    participant_id = st.session_state["participant_id"]
    device = st.session_state["device"]
    access_token = st.session_state.get("access_token")
    username = st.session_state.get("username", "unknown_user")

    pending_phases = pending_phase_labels(st.session_state)
    if pending_phases:
        st.warning(
            "⚠️ Before leaving this participant, choose Log Activity or Skip Log for: "
            + ", ".join(pending_phases)
        )
    else:
        st.success("✅ Activity logging decision completed for all visible phases.")

    # ------------------------------------------------------------------
    # Multi-phase path: Actical / Philips Health Band
    # ------------------------------------------------------------------
    if "phase_files" in st.session_state:
        _render_multi_phase_viewer(
            phase_files=st.session_state["phase_files"],
            access_token=access_token,
            username=username,
            participant_id=participant_id,
            device=device,
        )
        return

    # ------------------------------------------------------------------
    # Single-phase path: all other devices (unchanged behaviour)
    # ------------------------------------------------------------------
    _render_single_phase_viewer(
        participant_id=participant_id,
        device=device,
        phase=st.session_state.get("phase"),
        folder_path=st.session_state["folder_path"],
        csv_file=st.session_state.get("csv_file"),
        pdf_file_sleep=st.session_state.get("pdf_file_sleep"),
        pdf_file_data=st.session_state.get("pdf_file_data", []),
        access_token=access_token,
        username=username,
    )
