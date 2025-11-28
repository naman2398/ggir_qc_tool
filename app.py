"""GGIR QC Tool - Main Application"""

import streamlit as st
from src.ui.sidebar import render_sidebar
from src.ui.search_interface import render_search_interface
from src.ui.file_viewer import render_file_viewer


def main():
    st.set_page_config(page_title="GGIR QC Tool", page_icon="📊", layout="wide")
    st.title("📊 GGIR QC Tool")
    st.markdown("Secure Participant File Finder & Editor")
    st.markdown("---")
    
    if not render_sidebar():
        st.stop()
    
    files_found, _ = render_search_interface()
    
    if files_found or st.session_state.get("participant_id"):
        render_file_viewer()


if __name__ == "__main__":
    main()
