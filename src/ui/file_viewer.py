"""File Viewer UI Component"""

import streamlit as st
from config import settings
from src.api.file_operations import download_csv, upload_csv


def _df_with_delete_col(df):
    """Prepend a _to_delete bool column (all False) to a dataframe."""
    result = df.copy()
    result.insert(0, "_to_delete", False)
    return result


def render_file_viewer():
    """Render the file viewer and editor interface."""
    if not st.session_state.get("participant_id"):
        return

    st.session_state.setdefault("data_editor_version", 0)
    
    participant_id = st.session_state["participant_id"]
    device = st.session_state["device"]
    phase = st.session_state.get("phase")
    folder_path = st.session_state["folder_path"]
    csv_file = st.session_state.get("csv_file")
    pdf_file_sleep = st.session_state.get("pdf_file_sleep")
    pdf_file_data = st.session_state.get("pdf_file_data", [])
    access_token = st.session_state.get("access_token")
    username = st.session_state.get("username", "unknown_user")
    
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
    
    if csv_file:
        st.markdown(f"**{settings.TARGET_FILES['csv']}**")
        
        last_saved = st.session_state.get("last_saved_file")
        if last_saved:
            st.success(f"✅ Saved as: **{last_saved}**")

        if "original_df" not in st.session_state:
            df = download_csv(access_token, csv_file["id"])
            if df is not None:
                st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
                st.session_state["original_df"] = df.copy()
                st.session_state["current_df"] = _df_with_delete_col(df)
            else:
                st.error("❌ Failed to load CSV file.")
                return

        edited_df = st.data_editor(
            st.session_state["current_df"],
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "_to_delete": st.column_config.CheckboxColumn(
                    "🗑️ Delete",
                    help="Check to mark this row for deletion. Marked rows are removed when you save.",
                    default=False,
                )
            },
            key=f"data_editor_{st.session_state['data_editor_version']}",
        )

        rows_to_delete = int(edited_df["_to_delete"].sum())
        data_changed = not edited_df.equals(st.session_state["current_df"])

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
            save_button = st.button("💾 Save Changes", type="primary", disabled=not data_changed)
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
                        st.session_state["original_df"] = save_df.copy()
                        st.session_state["current_df"] = _df_with_delete_col(save_df)
                        st.session_state["last_saved_file"] = new_file["name"]
                        st.session_state["data_editor_version"] = st.session_state.get("data_editor_version", 0) + 1
                        st.rerun()
                        st.markdown(f"[🔗 View file]({new_file['webUrl']})")
                    else:
                        st.error("❌ Failed to save. Please try again.")
    else:
        st.warning(f"⚠️ {settings.TARGET_FILES['csv']} not found")
