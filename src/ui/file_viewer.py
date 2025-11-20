"""
File Viewer UI Component

Display and edit participant files.
"""

import streamlit as st
from datetime import datetime
from config.settings import config
from src.auth import get_access_token
from src.api import download_csv_content, upload_versioned_csv


def render_file_viewer():
    """
    Render the file viewer and editor interface.
    """
    if not st.session_state.get('participant_id'):
        return
    
    participant_id = st.session_state['participant_id']
    device = st.session_state['device']
    phase = st.session_state.get('phase')
    folder_path = st.session_state['folder_path']
    csv_file = st.session_state.get('csv_file')
    pdf_file_sleep = st.session_state.get('pdf_file_sleep')
    pdf_file_data = st.session_state.get('pdf_file_data')
    
    st.header("📂 Participant Files")
    
    # Display path
    path_display = f"{device}"
    if phase:
        path_display += f" / {phase}"
    path_display += f" / {participant_id}"
    st.info(f"📁 **Path**: {path_display}")
    
    # Display PDF links
    st.subheader("📄 Reports (Read-Only)")
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        if pdf_file_sleep:
            st.markdown(f"**{config.TARGET_FILES['pdf_sleep']}**")
            st.markdown(f"[🔗 Open PDF]({pdf_file_sleep['webUrl']})")
        else:
            st.warning(f"⚠️ {config.TARGET_FILES['pdf_sleep']} not found")
    
    with col_pdf2:
        if pdf_file_data:
            st.markdown(f"**{config.TARGET_FILES['pdf_data']}**")
            st.markdown(f"[🔗 Open PDF]({pdf_file_data['webUrl']})")
        else:
            st.warning(f"⚠️ {config.TARGET_FILES['pdf_data']} not found")
    
    st.markdown("---")
    
    # Display editable CSV
    st.subheader("✏️ Edit Data File")
    
    if csv_file:
        st.markdown(f"**{config.TARGET_FILES['csv']}**")
        
        # Initialize session state for data editing
        if 'original_df' not in st.session_state:
            access_token = get_access_token()
            df = download_csv_content(access_token, csv_file['id'])
            
            if df is not None:
                st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
                st.session_state['original_df'] = df.copy()
                st.session_state['current_df'] = df.copy()
            else:
                st.error("❌ Failed to load CSV file.")
                st.stop()
        
        # Editable data editor
        edited_df = st.data_editor(
            st.session_state['current_df'],
            use_container_width=True,
            num_rows="dynamic",
            key="data_editor"
        )
        
        # Check if data was modified
        data_changed = not edited_df.equals(st.session_state['current_df'])
        
        # Save button and status
        col_save, col_status = st.columns([1, 2])
        
        with col_save:
            save_button = st.button(
                "💾 Save Changes",
                type="primary",
                disabled=not data_changed
            )
        
        with col_status:
            if data_changed:
                st.warning("⚠️ Unsaved changes")
            else:
                st.success("✅ All changes saved")
        
        # Handle save action
        if save_button and data_changed:
            with st.spinner("Saving new version..."):
                access_token = get_access_token()
                
                # Upload versioned file
                new_file = upload_versioned_csv(
                    access_token,
                    folder_path,
                    config.TARGET_FILES['csv'],
                    edited_df
                )
                
                if new_file:
                    # Update current state
                    st.session_state['current_df'] = edited_df.copy()
                    
                    st.success(f"✅ Successfully saved as: **{new_file['name']}**")
                    st.markdown(f"[🔗 View file]({new_file['webUrl']})")
                    
                    # Log the save action
                    with st.expander("📋 Save Details"):
                        st.markdown(f"""
                        - **User**: {st.session_state.get('user_email', 'Unknown')}
                        - **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        - **Participant ID**: {participant_id}
                        - **Device**: {device}
                        - **Phase**: {phase if phase else 'N/A'}
                        - **File**: {new_file['name']}
                        """)
                else:
                    st.error("❌ Failed to save the file. Please try again.")
    else:
        st.warning(f"⚠️ {config.TARGET_FILES['csv']} not found in the participant folder.")
