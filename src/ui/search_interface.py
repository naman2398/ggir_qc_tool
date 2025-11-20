"""
Search Interface UI Component

Device selection and participant search functionality.
"""

import streamlit as st
from config.settings import config
from src.auth import get_access_token
from src.api import build_folder_path, find_file_in_folder


def render_search_interface():
    """
    Render the file search interface.
    
    Returns:
        tuple: (success, search_performed) - success indicates if files were found
    """
    st.header("🔍 Find Participant Files")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        selected_device = st.selectbox(
            "Device Type",
            config.SUPPORTED_DEVICES
        )
    
    # Conditional phase selection
    selected_phase = None
    if selected_device in config.DEVICE_PHASE_MAPPING:
        with col1:
            selected_phase = st.selectbox(
                "Study Phase",
                config.DEVICE_PHASE_MAPPING[selected_device]
            )
    
    with col2:
        participant_id = st.text_input(
            "Participant ID",
            placeholder="e.g., PID123"
        )
    
    search_button = st.button("🔎 Search Files", type="primary")
    
    if search_button and participant_id:
        with st.spinner("Searching for files..."):
            # Get access token
            access_token = get_access_token()
            
            if not access_token:
                st.error("❌ Failed to authenticate with Microsoft Graph API.")
                return False, True
            
            # Build folder path
            folder_path = build_folder_path(selected_device, selected_phase, participant_id)
            
            # Display the path being searched
            st.info(f"📁 Searching: `{folder_path}`")
            
            # Find the three target files
            csv_file = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['csv']
            )
            pdf_file_sleep = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['pdf_sleep']
            )
            pdf_file_data = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['pdf_data']
            )
            
            # Check if folder exists (at least one file found)
            if not any([csv_file, pdf_file_sleep, pdf_file_data]):
                st.error(f"❌ No files found for {selected_device}/{participant_id}")
                st.info("Please verify the device type, phase (if applicable), and participant ID are correct.")
                return False, True
            
            st.success(f"✅ Found participant folder!")
            
            # Store in session state
            st.session_state['participant_id'] = participant_id
            st.session_state['device'] = selected_device
            st.session_state['phase'] = selected_phase
            st.session_state['folder_path'] = folder_path
            st.session_state['csv_file'] = csv_file
            st.session_state['pdf_file_sleep'] = pdf_file_sleep
            st.session_state['pdf_file_data'] = pdf_file_data
            
            st.markdown("---")
            return True, True
    
    elif search_button:
        st.warning("⚠️ Please enter a Participant ID.")
        return False, True
    
    return False, False
