"""File Viewer UI Component"""

import json

import pandas as pd
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


_HELPER_COLUMNS = ["_to_delete", "_added"]


def _df_with_delete_col(df, added_mask=None):
    """Prepend helper columns used by editor state and row status previews."""
    result = df.drop(columns=_HELPER_COLUMNS, errors="ignore").copy()
    result.insert(0, "_to_delete", False)
    result.insert(1, "_added", False)
    if added_mask is not None:
        result["_added"] = list(added_mask)
    return result


def _df_without_helper_cols(df):
    """Return dataframe copy without internal UI helper columns."""
    cleaned = df.drop(columns=_HELPER_COLUMNS, errors="ignore").copy()
    # Ignore CSV index artifact columns that may appear in one file but not the other.
    keep_cols = [col for col in cleaned.columns if not str(col).startswith("Unnamed:")]
    return cleaned.loc[:, keep_cols]


def _normalize_for_compare(df):
    """Normalize dataframe for strict row-wise comparisons across summary/edit views."""
    normalized = _df_without_helper_cols(df).copy()
    normalized.columns = [str(col) for col in normalized.columns]
    normalized = normalized.reindex(sorted(normalized.columns), axis=1)
    return normalized.reset_index(drop=True)


def _normalize_cell(value):
    """Convert cell value into a stable compare token (NaN-safe, dtype-agnostic)."""
    if pd.isna(value):
        return "__GGIR_NULL__"
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _row_signatures(df):
    """Create stable per-row signatures used for exact row presence checks."""
    if df.empty:
        return pd.Series([], dtype="object")

    prepared = _normalize_for_compare(df).map(_normalize_cell)
    cols = list(prepared.columns)

    def _to_sig(row):
        payload = {col: row[col] for col in cols}
        return json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)

    return prepared.apply(_to_sig, axis=1)


def _missing_summary_mask(summary_df, edit_df):
    """Return boolean mask for summary rows that are missing from edit rows."""
    summary_norm = _normalize_for_compare(summary_df)
    edit_norm = _normalize_for_compare(edit_df)

    if summary_norm.empty:
        return pd.Series([], dtype="bool")

    if set(summary_norm.columns) != set(edit_norm.columns):
        return pd.Series([True] * len(summary_norm), index=summary_norm.index)

    ordered_cols = sorted(summary_norm.columns)
    summary_cmp = summary_norm.loc[:, ordered_cols].map(_normalize_cell)
    edit_cmp = edit_norm.loc[:, ordered_cols].map(_normalize_cell)

    # Multiset-aware diff: preserves duplicate counts when computing missing rows.
    summary_ranked = summary_cmp.copy()
    summary_ranked["_dup_rank"] = summary_cmp.groupby(ordered_cols, dropna=False).cumcount()
    edit_ranked = edit_cmp.copy()
    edit_ranked["_dup_rank"] = edit_cmp.groupby(ordered_cols, dropna=False).cumcount()

    merged = summary_ranked.merge(
        edit_ranked,
        on=ordered_cols + ["_dup_rank"],
        how="left",
        indicator=True,
    )
    return merged["_merge"].eq("left_only")


def _ensure_edit_state_loaded(csv_file, access_token, state_suffix):
    """Initialize edit dataframe state if absent so summary compare is available immediately."""
    key_original = f"original_df{state_suffix}"
    key_current = f"current_df{state_suffix}"
    if key_original in st.session_state and key_current in st.session_state:
        return

    if not csv_file:
        return

    df = download_csv(access_token, csv_file["id"])
    if df is None:
        return
    st.session_state[key_original] = df.copy()
    st.session_state[key_current] = _df_with_delete_col(df)


def _summary_to_edit_suffix(state_suffix):
    """Map read-only summary key suffix to edit-state suffix for the same phase."""
    if state_suffix.startswith("_qc_"):
        return f"_{state_suffix[4:]}"
    return state_suffix


def _render_readonly_csv(qc_csv_file, access_token, state_suffix, phase_label):
    """Render a read-only view of the full QC summary CSV."""
    key_qc_df = f"qc_df{state_suffix}"
    edit_state_suffix = _summary_to_edit_suffix(state_suffix)
    key_current = f"current_df{edit_state_suffix}"
    key_version = f"data_editor_version{edit_state_suffix}"
    key_editor_status = f"editor_status{edit_state_suffix}"
    key_force_dirty = f"force_dirty{edit_state_suffix}"

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
    current_df = st.session_state.get(key_current)

    if current_df is not None:
        missing_mask = _missing_summary_mask(df, current_df)
    else:
        missing_mask = pd.Series([False] * len(df), index=df.index)

    missing_df = df[missing_mask].reset_index(drop=True)
    st.caption(
        f"📊 {len(df)} rows × {len(df.columns)} columns | "
        f"Missing from edit: {len(missing_df)}"
    )

    def _highlight_missing(row):
        if bool(missing_mask.loc[row.name]):
            return ["background-color: #fff9c4"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(_highlight_missing, axis=1),
        use_container_width=True,
        hide_index=True,
    )

    if current_df is None:
        st.info("Load edit data to enable missing-row copy actions.")
        return

    if missing_df.empty:
        st.success("All summary records are already present in Edit Data Files.")
        return

    st.caption("Select missing rows to copy into Edit Data Files")
    selector_df = missing_df.copy()
    selector_df.insert(0, "_copy", False)
    selected_rows = st.data_editor(
        selector_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        column_config={
            "_copy": st.column_config.CheckboxColumn(
                "Copy",
                help="Select rows to copy into Edit Data Files.",
                default=False,
            ),
        },
        disabled=list(selector_df.columns[1:]),
        key=f"missing_copy_editor{edit_state_suffix}",
    )
    selected_count = int(selected_rows["_copy"].sum())
    st.caption(f"Selected: {selected_count} of {len(missing_df)} missing row(s)")

    copy_clicked = st.button(
        "Copy selected to Edit Data Files",
        key=f"copy_missing_rows{edit_state_suffix}",
        disabled=selected_count == 0,
    )

    if copy_clicked:
        selected_df = selected_rows[selected_rows["_copy"]].drop(columns=["_copy"]).reset_index(drop=True)
        latest_current_df = st.session_state.get(key_current)
        latest_missing_mask = _missing_summary_mask(df, latest_current_df)
        latest_missing_df = df[latest_missing_mask].reset_index(drop=True)
        latest_missing_signatures = set(_row_signatures(latest_missing_df).tolist())

        selected_signatures = _row_signatures(selected_df)
        rows_to_copy = selected_df[selected_signatures.isin(latest_missing_signatures)].reset_index(drop=True)

        if rows_to_copy.empty:
            st.session_state[key_editor_status] = {
                "level": "warning",
                "text": "Selected rows are already present in Edit Data Files.",
            }
            st.rerun()

        latest_edit_clean = _df_without_helper_cols(latest_current_df)
        updated_edit = pd.concat([latest_edit_clean, rows_to_copy], ignore_index=True)
        if "_added" in latest_current_df.columns:
            existing_added = latest_current_df["_added"].astype(bool).tolist()
        else:
            existing_added = [False] * len(latest_edit_clean)
        st.session_state[key_current] = _df_with_delete_col(
            updated_edit,
            added_mask=existing_added + [True] * len(rows_to_copy),
        )
        st.session_state[key_version] = st.session_state.get(key_version, 0) + 1
        st.session_state[key_force_dirty] = True

        participant_id = st.session_state.get("participant_id")
        monitor = st.session_state.get("device")
        if participant_id and monitor:
            st.session_state[modified_key(participant_id, monitor, phase_label)] = True

        st.session_state[key_editor_status] = {
            "level": "success",
            "text": f"Copied {len(rows_to_copy)} row(s) into Edit Data Files.",
        }
        st.rerun()


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
    _ensure_edit_state_loaded(csv_file=csv_file, access_token=access_token, state_suffix="")
    _render_readonly_csv(
        qc_csv_file=st.session_state.get("qc_csv_file"),
        access_token=access_token,
        state_suffix="",
        phase_label=phase or "NoPhase",
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
                _ensure_edit_state_loaded(
                    csv_file=pf.get("csv_file"),
                    access_token=access_token,
                    state_suffix=f"_{pf['phase']}",
                )
                _render_readonly_csv(
                    qc_csv_file=pf["qc_csv_file"],
                    access_token=access_token,
                    state_suffix=f"_qc_{pf['phase']}",
                    phase_label=pf["phase"],
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
    key_editor_status = f"editor_status{state_suffix}"
    key_save_state_history = f"save_state_history{state_suffix}"
    key_force_dirty = f"force_dirty{state_suffix}"
    participant_id = st.session_state.get("participant_id")
    monitor = st.session_state.get("device")
    tracked_saves_key = saved_files_key(participant_id, monitor, phase_label)
    st.session_state.setdefault(tracked_saves_key, [])
    st.session_state.setdefault(key_save_state_history, [])
    st.session_state.setdefault(key_force_dirty, False)

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

    if "_added" not in st.session_state[key_current].columns:
        st.session_state[key_current].insert(1, "_added", False)

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
            ),
            "_added": st.column_config.CheckboxColumn(
                "➕ Added",
                help="Rows copied from Full Summary Data and not yet saved.",
                default=False,
            ),
        },
        disabled=["_added"],
        key=f"data_editor{state_suffix}_{version}",
    )

    rows_to_delete = int(edited_df["_to_delete"].sum())
    rows_added = int(edited_df["_added"].sum())
    data_changed = st.session_state.get(key_force_dirty, False) or not edited_df.equals(st.session_state[key_current])
    editor_status = st.session_state.pop(key_editor_status, None)

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

    if rows_added > 0:
        st.info(
            f"➕ **{rows_added} row(s) copied from Full Summary Data** — "
            "shown in green below. Save with data modifications to persist them."
        )

        def _highlight_added(row):
            if row["_added"] and not row["_to_delete"]:
                return ["background-color: #dff6dd; color: #0b6e4f"] * len(row)
            if row["_added"] and row["_to_delete"]:
                return ["background-color: #ffe8cc; color: #8a4b08"] * len(row)
            return [""] * len(row)

        st.dataframe(
            edited_df.style.apply(_highlight_added, axis=1),
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
        if editor_status:
            level = editor_status.get("level")
            text = editor_status.get("text", "")
            if level == "success":
                st.success(text)
            elif level == "warning":
                st.warning(text)
            elif level == "error":
                st.error(text)
            else:
                st.info(text)
        else:
            st.warning("⚠️ Unsaved changes") if data_changed else st.success("✅ All changes saved")

    if undo_button:
        tracked_saves = st.session_state.get(tracked_saves_key, [])
        if not tracked_saves:
            st.session_state[key_editor_status] = {
                "level": "warning",
                "text": "No saved files from this session to undo.",
            }
            st.rerun()
        else:
            latest_file = tracked_saves[-1]
            delete_result = delete_file_by_id(access_token, latest_file.get("id"))
            if delete_result.get("success"):
                updated_history = tracked_saves[:-1]
                st.session_state[tracked_saves_key] = updated_history

                save_state_history = st.session_state.get(key_save_state_history, [])
                if save_state_history:
                    previous_state = save_state_history[-1]
                    st.session_state[key_save_state_history] = save_state_history[:-1]
                    st.session_state[key_original] = previous_state["original_df"].copy()
                    restored_current = previous_state["current_df"].copy()
                    if "_added" not in restored_current.columns:
                        restored_current.insert(1, "_added", False)
                    st.session_state[key_current] = restored_current
                    if previous_state.get("last_saved"):
                        st.session_state[key_last_saved] = previous_state["last_saved"]
                    else:
                        st.session_state.pop(key_last_saved, None)
                    if previous_state.get("last_saved_url"):
                        st.session_state[key_last_saved_url] = previous_state["last_saved_url"]
                    else:
                        st.session_state.pop(key_last_saved_url, None)

                if updated_history:
                    st.session_state[key_last_saved] = updated_history[-1].get("name")
                    st.session_state[key_last_saved_url] = updated_history[-1].get("webUrl", "")
                elif not save_state_history:
                    st.session_state.pop(key_last_saved, None)
                    st.session_state.pop(key_last_saved_url, None)

                st.session_state[key_version] = st.session_state.get(key_version, 0) + 1
                st.session_state[key_force_dirty] = False
                st.session_state[key_editor_status] = {
                    "level": "success",
                    "text": "✅ Saved changes undone.",
                }
                st.rerun()
            else:
                st.session_state[key_editor_status] = {
                    "level": "error",
                    "text": f"Undo failed: {delete_result.get('error', 'Unknown error')}",
                }
                st.rerun()

    if save_button and data_changed:
        save_df = (
            edited_df[~edited_df["_to_delete"]]
            .drop(columns=["_to_delete", "_added"])
            .reset_index(drop=True)
        )
        if save_df.empty:
            st.error("❌ Cannot save: all rows are marked for deletion.")
        else:
            with st.spinner("Saving new version..."):
                previous_state = {
                    "original_df": st.session_state[key_original].copy(),
                    "current_df": st.session_state[key_current].copy(),
                    "last_saved": st.session_state.get(key_last_saved),
                    "last_saved_url": st.session_state.get(key_last_saved_url),
                }
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
                    st.session_state[key_save_state_history] = (
                        st.session_state.get(key_save_state_history, []) + [previous_state]
                    )
                    st.session_state[key_version] = version + 1
                    st.session_state[key_force_dirty] = False
                    st.session_state[key_editor_status] = {
                        "level": "success",
                        "text": "✅ Save done with data modifications",
                    }
                    st.rerun()
                else:
                    st.session_state[key_editor_status] = {
                        "level": "error",
                        "text": "Failed to save. Please try again.",
                    }
                    st.rerun()

    if save_without_changes_button:
        unchanged_df = st.session_state[key_original].copy()
        with st.spinner("Saving unchanged copy..."):
            previous_state = {
                "original_df": st.session_state[key_original].copy(),
                "current_df": st.session_state[key_current].copy(),
                "last_saved": st.session_state.get(key_last_saved),
                "last_saved_url": st.session_state.get(key_last_saved_url),
            }
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
                st.session_state[key_save_state_history] = (
                    st.session_state.get(key_save_state_history, []) + [previous_state]
                )
                st.session_state[key_editor_status] = {
                    "level": "success",
                    "text": "Save done without data modifications",
                }
                st.rerun()
            else:
                st.session_state[key_editor_status] = {
                    "level": "error",
                    "text": "Failed to save unchanged copy. Please try again.",
                }
                st.rerun()

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
