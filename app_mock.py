"""Mock App for Local UI Testing (No Azure Credentials Required)"""

import streamlit as st
import pandas as pd
from config import settings

# Mock data
MOCK_USERS = ["test@example.com", "admin@example.com"]
MOCK_CSV_DATA = pd.DataFrame({
    "ID": ["P001", "P002", "P003"],
    "filename": ["file1.bin", "file2.bin", "file3.bin"],
    "device_serial": ["ABC123", "DEF456", "GHI789"],
    "start_time": ["2025-01-01 08:00", "2025-01-02 09:00", "2025-01-03 10:00"],
    "end_time": ["2025-01-08 08:00", "2025-01-09 09:00", "2025-01-10 10:00"],
    "QC_status": ["Pass", "Fail", "Pending"],
    "notes": ["Good data", "Missing days", "Review needed"]
})


def render_sidebar():
    """Mock sidebar with authentication."""
    with st.sidebar:
        st.title("🔐 Authentication")
        
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.user_email = None
        
        if not st.session_state.authenticated:
            email = st.text_input("Email", placeholder="test@example.com")
            if st.button("Login", type="primary"):
                if email in MOCK_USERS:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.rerun()
                else:
                    st.error("Not authorized")
        else:
            st.success(f"✅ {st.session_state.user_email}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.rerun()


def render_search():
    """Mock search interface."""
    st.header("🔍 Search Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        device = st.selectbox("Device Type", settings.SUPPORTED_DEVICES)
    
    with col2:
        phases = settings.DEVICE_PHASE_MAPPING.get(device, [])
        phase = st.selectbox("Phase", phases) if phases else None
    
    with col3:
        participant_id = st.text_input("Participant ID", placeholder="e.g., P001")
    
    if st.button("Search", type="primary"):
        if participant_id:
            st.session_state.search_results = {
                "device": device,
                "phase": phase,
                "participant_id": participant_id,
                "found": True
            }
        else:
            st.warning("Enter a Participant ID")


def render_file_viewer():
    """Mock file viewer with CSV editor."""
    if "search_results" not in st.session_state:
        st.info("Use the search above to find files")
        return
    
    results = st.session_state.search_results
    
    if not results.get("found"):
        st.warning("No files found")
        return
    
    st.header(f"📁 Files for {results['participant_id']}")
    
    tab1, tab2 = st.tabs(["📊 CSV Editor", "📄 PDF Viewer"])
    
    with tab1:
        st.subheader("data_quality_report.csv")
        
        # Editable dataframe
        edited_df = st.data_editor(
            MOCK_CSV_DATA,
            use_container_width=True,
            num_rows="dynamic"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Save Changes", type="primary"):
                st.success("Changes saved! (Mock)")
        
        if edited_df is not None and not edited_df.equals(MOCK_CSV_DATA):
            st.info("You have unsaved changes")
    
    with tab2:
        st.subheader("visualisation_sleep.pdf")
        st.image("https://via.placeholder.com/800x600?text=PDF+Preview+Placeholder", 
                 caption="Mock PDF Preview")


def main():
    st.set_page_config(
        page_title="GGIR QC Tool (Mock)",
        page_icon="🧪",
        layout="wide"
    )
    
    st.title("🧪 GGIR QC Tool - Mock Mode")
    st.caption("⚠️ This is a mock version for UI testing. No real data is loaded.")
    
    render_sidebar()
    
    if st.session_state.get("authenticated"):
        render_search()
        st.divider()
        render_file_viewer()
    else:
        st.info("👈 Please login using the sidebar")
        st.markdown("**Mock users:** `test@example.com`, `admin@example.com`")


if __name__ == "__main__":
    main()
