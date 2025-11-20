"""
GGIR QC Tool - Main Application

Secure Participant File Finder & Editor for GGIR accelerometer data.
Stony Brook University - Version 3.4.0
"""

import streamlit as st
from src.ui import render_sidebar, render_search_interface, render_file_viewer


def main():
    """Main application entry point."""
    
    # Page configuration
    st.set_page_config(
        page_title="GGIR QC Tool",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 GGIR QC Tool")
    st.markdown("Secure Participant File Finder & Editor")
    st.markdown("---")
    
    # Render authentication sidebar
    is_authorized = render_sidebar()
    
    # Main content area
    if not is_authorized:
        st.warning("⚠️ Please authenticate using the sidebar.")
        st.stop()
    
    # Render search interface
    files_found, search_performed = render_search_interface()
    
    # Render file viewer if files were found or already in session
    if files_found or st.session_state.get('participant_id'):
        render_file_viewer()
    elif search_performed:
        pass  # Search was performed but no files found (error already shown)


if __name__ == "__main__":
    main()
