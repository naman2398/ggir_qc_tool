"""File Viewer UI Component"""

import streamlit as st
from config import settings
from src.api.file_operations import download_csv, upload_csv


def _df_with_delete_col(df):
    """Prepend a _to_delete bool column (all False) to a dataframe."""
    result = df.copy()
    result.insert(0, "_to_delete", False)
    return result


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

    # Editable CSV
    st.subheader("✏️ Edit Data File")
    _render_csv_editor(
        csv_file=csv_file,
        folder_path=folder_path,
        access_token=access_token,
        username=username,
        state_suffix="",          # no suffix → uses original_df, current_df, etc.
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
            )


# =============================================================================
# Shared CSV editor (used by both single and multi-phase viewers)
# =============================================================================

def _render_csv_editor(csv_file, folder_path, access_token, username, state_suffix):
    """
    Render an editable CSV data_editor block.

    state_suffix: appended to all session_state keys so that multiple phases
    can each have independent editor state. Empty string for single-phase.
    """
    key_original = f"original_df{state_suffix}"
    key_current = f"current_df{state_suffix}"
    key_version = f"data_editor_version{state_suffix}"
    key_last_saved = f"last_saved_file{state_suffix}"

    if not csv_file:
        st.warning(f"⚠️ {settings.TARGET_FILES['csv']} not found")
        return

    st.markdown(f"**{settings.TARGET_FILES['csv']}**")

    last_saved = st.session_state.get(key_last_saved)
    if last_saved:
        st.success(f"✅ Saved as: **{last_saved}**")

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

    col_save, col_status = st.columns([1, 2])
    with col_save:
        save_button = st.button(
            "💾 Save Changes",
            type="primary",
            disabled=not data_changed,
            key=f"save_btn{state_suffix}",
        )
    with col_status:
        st.warning("⚠️ Unsaved changes") if data_changed else st.success("✅ All changes saved")

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
                    st.session_state[key_version] = version + 1
                    st.rerun()
                    st.markdown(f"[🔗 View file]({new_file['webUrl']})")
                else:
                    st.error("❌ Failed to save. Please try again.")


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
