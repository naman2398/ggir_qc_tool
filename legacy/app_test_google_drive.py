"""
Mock version of the Secure Participant File Finder & Editor for UI testing.
This version simulates Google Drive responses without making actual API calls.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time

# ============================================================================
# CONFIGURATION
# ============================================================================

# Hardcoded list of accelerometer types
ACCELEROMETER_TYPES = [
    "ActiGraph",
    "Actiwatch",
    "Actical",
    "Fitbit",
    "Philips Health Band"
]

# Hardcoded filenames to search for
CSV_FILENAME = "part4_nightsummary_sleep_cleaned.csv"
PDF_FILENAME_1 = "visualisation_sleep.pdf"
PDF_FILENAME_2 = "visualisation_data.pdf"

# Mock authorized users for UI testing
MOCK_AUTHORIZED_USERS = [
    "user@stonybrook.edu",
    "admin@stonybrook.edu",
    "researcher@stonybrook.edu"
]

# ============================================================================
# MOCK FUNCTIONS FOR UI TESTING
# ============================================================================

def mock_check_authorization(email):
    """Mock authorization check."""
    return email.lower() in [u.lower() for u in MOCK_AUTHORIZED_USERS]


def mock_find_files(accelerometer, participant_id):
    """Mock file finding - simulates successful file discovery with real Google Drive links."""
    return {
        'csv': {
            'id': '1aIEB84p1YY4sCe5RqH--pu6PoU8uUG5v',
            'name': CSV_FILENAME,
            'webViewLink': 'https://drive.google.com/file/d/1aIEB84p1YY4sCe5RqH--pu6PoU8uUG5v/view?usp=drive_link'
        },
        'pdf1': {
            'id': '1f65DKTu-NDwGDvHtmllBlqt5l56QKyVo',
            'name': PDF_FILENAME_1,
            'webViewLink': 'https://drive.google.com/file/d/1f65DKTu-NDwGDvHtmllBlqt5l56QKyVo/view?usp=drive_link'
        },
        'pdf2': {
            'id': '1K0fuEPyu9MXbzQ9byRO71-fEwjzehc5y',
            'name': PDF_FILENAME_2,
            'webViewLink': 'https://drive.google.com/file/d/1K0fuEPyu9MXbzQ9byRO71-fEwjzehc5y/view?usp=sharing'
        }
    }


def mock_load_csv():
    """Load CSV data from actual Google Drive file."""
    import io
    import requests
    
    # Convert Google Drive view link to direct download link
    file_id = '1aIEB84p1YY4sCe5RqH--pu6PoU8uUG5v'
    download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
    
    try:
        # Download the CSV file
        response = requests.get(download_url)
        response.raise_for_status()
        
        # Load into pandas DataFrame
        csv_content = io.StringIO(response.text)
        df = pd.read_csv(csv_content)
        return df
    except Exception as e:
        # Fallback to mock data if download fails
        st.warning(f"Could not load real CSV data: {str(e)}. Using fallback data.")
        return pd.DataFrame({
            'night': [1, 2, 3, 4, 5],
            'sleep_onset': ['23:15', '22:45', '23:30', '23:00', '22:30'],
            'wake_time': ['07:30', '07:15', '07:45', '07:00', '07:30'],
            'sleep_duration_hours': [8.25, 8.50, 8.25, 8.00, 9.00],
            'sleep_efficiency': [0.92, 0.94, 0.89, 0.91, 0.95],
            'awakenings': [2, 1, 3, 2, 1],
            'quality_score': [8.5, 9.0, 7.5, 8.0, 9.5]
        })


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    """
    Main application function - UI testing version.
    """
    # Page configuration
    st.set_page_config(
        page_title="Participant File Finder & Editor [UI TEST MODE]",
        page_icon="📁",
        layout="wide"
    )
    
    # Add UI test mode banner
    st.warning("⚠️ **UI TEST MODE** - This is a mock version for testing the interface. No actual Google Drive connections are made.")
    
    st.title("GGIR QC Tool")
    st.markdown("---")
    
    # Sidebar for authentication
    with st.sidebar:
        st.header("Login")
        
        user_email = st.text_input(
            "Enter your email address:",
            placeholder="user@stonybrook.edu"
        )
        
        if user_email:
            if mock_check_authorization(user_email):
                st.success(f"✅ Login successful: {user_email}")
                st.session_state['authorized'] = True
                st.session_state['user_email'] = user_email
            else:
                st.error("❌ Unauthorized: Your email is not on the access list.")
                st.session_state['authorized'] = False
                st.stop()
        else:
            st.info("Please enter your email to access the application.")
            st.stop()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This is a QC tool for GGIR outputs.
        
        **Current Mode:** UI Testing (Mock Data)
        """)
    
    # Main content area
    if not st.session_state.get('authorized', False):
        st.warning("Please authenticate using the sidebar.")
        st.stop()
    
    # File search interface
    st.header("🔍 Find Participant Files")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_accelerometer = st.selectbox(
            "Select Accelerometer Type:",
            ["Select an accelerometer type..."] + ACCELEROMETER_TYPES,
            index=0
        )
    
    with col2:
        participant_id = st.text_input(
            "Enter Participant ID:",
            placeholder="e.g., PID123"
        )
    
    # Add sample IDs info
    st.info("💡 **UI Test Mode**: Enter any Participant ID (e.g., PID001, PID123) to see mock results.")
    
    search_button = st.button("🔎 Search Files", type="primary")
    
    # Check if we should display files (either just searched or already have participant data)
    should_display_files = (search_button and participant_id and selected_accelerometer != "Select an accelerometer type...") or st.session_state.get('participant_id')
    
    if search_button and participant_id and selected_accelerometer != "Select an accelerometer type...":
        # Clear previous session data when searching for new participant
        if st.session_state.get('participant_id') != participant_id:
            for key in ['original_df', 'current_df', 'last_df', 'save_count', 'pending_delete_confirmation', 'deleted_nights', 'delete_confirmed', 'pending_df', 'editor_key_counter']:
                if key in st.session_state:
                    del st.session_state[key]
        
        with st.spinner("Searching for files..."):
            # Simulate search delay
            time.sleep(0.5)
            
            # Mock file finding
            files = mock_find_files(selected_accelerometer, participant_id)
            
            st.success(f"✅ Found participant folder!")
            
            # Store in session state
            st.session_state['participant_id'] = participant_id
            st.session_state['accelerometer'] = selected_accelerometer
            st.session_state['files'] = files
    
    # Display files if we have participant data
    if should_display_files and st.session_state.get('participant_id'):
        participant_id = st.session_state['participant_id']
        selected_accelerometer = st.session_state['accelerometer']
        files = st.session_state.get('files', {})
        
        st.markdown("---")
        st.header("📂 Participant Files")
        
        # Show the constructed path
        path = f"{selected_accelerometer}/{participant_id}/output_{participant_id}/results/"
        st.info(f"📁 **Path**: `{path}`")
        
        # Display PDF links
        st.subheader("📄 View Reports (Read-Only)")
        
        col_pdf1, col_pdf2 = st.columns(2)
        
        with col_pdf1:
            st.markdown(f"**{PDF_FILENAME_1}**")
            st.markdown(f"[🔗 Open PDF]({files['pdf1']['webViewLink']})")
            st.caption("Click to view the sleep visualization report")
        
        with col_pdf2:
            st.markdown(f"**{PDF_FILENAME_2}**")
            st.markdown(f"[🔗 Open PDF]({files['pdf2']['webViewLink']})")
            st.caption("Click to view the data visualization report")
        
        st.markdown("---")
        
        # Editable CSV Data Section
        st.subheader("📊 Edit Data File")
        st.markdown(f"**{CSV_FILENAME}**")
        
        # Initialize session state for data editing
        if 'original_df' not in st.session_state:
            with st.spinner("Loading CSV data from Google Drive..."):
                df = mock_load_csv()
            st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
            st.session_state['original_df'] = df.copy()
            st.session_state['current_df'] = df.copy()
            st.session_state['save_count'] = 0
            st.session_state['last_saved_version'] = None
        
        # Editable data editor with dynamic rows
        st.markdown("**✏️ Edit Data Below** (You can add, delete, or modify rows)")
        edited_df = st.data_editor(
            st.session_state['current_df'],
            use_container_width=True,
            num_rows="dynamic",  # Allow users to add/delete rows
            height=400,
            key="data_editor"
        )
        
        # Check if data was modified
        data_changed = not edited_df.equals(st.session_state['current_df'])
        
        # Save button and status display
        st.markdown("")  # Add spacing
        col_save, col_status, col_download = st.columns([1, 2, 1])
        
        with col_save:
            save_button = st.button(
                "💾 Save Changes", 
                type="primary", 
                disabled=not data_changed, 
                key="save_btn",
                help="Save edited data as a new versioned file in Google Drive"
            )
        
        with col_status:
            if data_changed:
                st.warning("⚠️ You have unsaved changes")
            else:
                st.success("✅ All changes saved")
        
        with col_download:
            # Download button for current data
            csv_data = edited_df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download",
                data=csv_data,
                file_name=CSV_FILENAME,
                mime="text/csv",
                key="download_csv_btn",
                help="Download current data as CSV file"
            )
        
        # Handle save action with versioning
        if save_button and data_changed:
            with st.spinner("Saving changes to Google Drive..."):
                # Simulate save delay
                time.sleep(1)
                
                # Update current state
                st.session_state['current_df'] = edited_df.copy()
                
                # Create versioned filename
                version_num = st.session_state['save_count'] + 1
                st.session_state['save_count'] = version_num
                
                name_part, ext = CSV_FILENAME.rsplit('.', 1)
                new_filename = f"{name_part}_v{version_num}.{ext}"
                
                # Store save information in session state
                st.session_state['last_saved_version'] = new_filename
                st.session_state['last_saved_path'] = f"{path}{new_filename}"
                st.session_state['last_save_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.session_state['last_save_version_num'] = version_num
                
                # Calculate number of records changed
                records_changed = abs(len(edited_df) - len(st.session_state['original_df']))
                st.session_state['last_save_records_changed'] = records_changed
                
                # Show a persistent success toast
                st.toast("✅ Changes saved successfully!", icon="✅")
                time.sleep(0.5)
                st.rerun()
        
        # Display persistent success message if a save has occurred
        if st.session_state.get('last_saved_version'):
            st.success(f"✅ **Successfully saved changes!**")
            st.info(f"📁 New versioned file created: **{st.session_state['last_saved_version']}**")
            st.markdown(f"Path: `{st.session_state['last_saved_path']}`")
            
            # Log the save action
            with st.expander("📋 Save Details"):
                st.markdown(f"""
                - **User**: {st.session_state.get('user_email', 'Unknown')}
                - **Timestamp**: {st.session_state.get('last_save_timestamp', 'N/A')}
                - **Participant ID**: {participant_id}
                - **Accelerometer**: {selected_accelerometer}
                - **Version Number**: v{st.session_state.get('last_save_version_num', 'N/A')}
                - **Records Changed**: {st.session_state.get('last_save_records_changed', 0)}
                - **File Location**: `{st.session_state['last_saved_path']}`
                """)
                st.caption("💡 The original file remains unchanged. All edits are saved as new versioned files.")
            
            # Dismiss button below save details
            if st.button("✖️ Dismiss", key="dismiss_success", help="Clear this success message"):
                # Clear all save-related session state
                st.session_state['last_saved_version'] = None
                st.session_state['last_saved_path'] = None
                st.session_state['last_save_timestamp'] = None
                st.session_state['last_save_version_num'] = None
                st.session_state['last_save_records_changed'] = None
                st.rerun()
        
        # Show comparison with original data
        if not st.session_state['current_df'].equals(st.session_state['original_df']):
            st.markdown("---")
            with st.expander("📊 Compare with Original Data"):
                st.markdown("**Original data loaded from Google Drive:**")
                st.dataframe(
                    st.session_state['original_df'],
                    use_container_width=True,
                    height=300
                )
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.metric("Original Rows", len(st.session_state['original_df']))
                with col_info2:
                    st.metric("Current Rows", len(st.session_state['current_df']), 
                             delta=len(st.session_state['current_df']) - len(st.session_state['original_df']))
        
        # Optional: Add refresh button to reload from Google Drive
        st.markdown("---")
        if st.button("🔄 Reload from Google Drive", key="refresh_btn", help="Discard all changes and reload original data"):
            with st.spinner("Reloading data from Google Drive..."):
                df = mock_load_csv()
            st.session_state['original_df'] = df.copy()
            st.session_state['current_df'] = df.copy()
            st.session_state['save_count'] = 0
            st.success("✅ Data reloaded from Google Drive!")
            st.rerun()
    
    elif search_button:
        if selected_accelerometer == "Select an accelerometer type...":
            st.warning("⚠️ Please select an accelerometer type.")
        elif not participant_id:
            st.warning("⚠️ Please enter a Participant ID.")
        else:
            st.warning("⚠️ Please select an accelerometer type and enter a Participant ID.")
    
    # Add footer with test info
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.9em;'>
    <b>UI Test Mode</b> | Mock data and simulated API responses | For testing purposes only
    </div>
    """, unsafe_allow_html=True)


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
