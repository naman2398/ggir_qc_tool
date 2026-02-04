"""Search Interface UI Component"""

import streamlit as st
from config import settings
from src.api.file_operations import build_folder_path, find_file


def render_search_interface():
    """Render file search interface. Returns (success, search_performed)."""
    st.header("🔍 Find Participant Data")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        device_options = ["Select Device Type..."] + settings.SUPPORTED_DEVICES
        selected_device = st.selectbox("Device Type", device_options)
    
    # Show default message if no device selected
    if selected_device == "Select Device Type...":
        st.info("👆 Please select a device type to begin searching for participant data.")
        return False, False
    
    selected_phase = None
    if selected_device in settings.DEVICE_PHASE_MAPPING:
        with col1:
            phase_options = ["Select Study Phase..."] + settings.DEVICE_PHASE_MAPPING[selected_device]
            selected_phase = st.selectbox("Study Phase", phase_options)
            
            # Show message if phase not selected for devices that require it
            if selected_phase == "Select Study Phase...":
                st.info("👆 Please select a study phase for this device type.")
                return False, False
    
    with col2:
        participant_id = st.text_input("Participant ID", placeholder="e.g., PID123")
    
    search_button = st.button("🔎 Search Files", type="primary")
    
    if search_button and participant_id:
        with st.spinner("Searching for files..."):
            access_token = st.session_state.get("access_token")
            if not access_token:
                st.error("❌ Not authenticated. Please login first.")
                return False, True
            
            folder_path = build_folder_path(selected_device, selected_phase, participant_id)
            st.info(f"📁 Searching: `{folder_path}`")
            
            csv_file = find_file(access_token, folder_path, settings.TARGET_FILES["csv"])
            pdf_file_sleep = find_file(access_token, folder_path, settings.TARGET_FILES["pdf_sleep"])
            pdf_file_data = find_file(access_token, folder_path, settings.TARGET_FILES["pdf_data"])
            
            if not any([csv_file, pdf_file_sleep, pdf_file_data]):
                st.error(f"❌ No files found for {selected_device}/{participant_id}")
                st.info("Please verify the device type, phase, and participant ID.")
                return False, True
            
            st.success("✅ Found participant folder!")
            
            st.session_state["participant_id"] = participant_id
            st.session_state["device"] = selected_device
            st.session_state["phase"] = selected_phase
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
