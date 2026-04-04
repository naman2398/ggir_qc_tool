"""GGIR QC Tool - Main Application"""

import streamlit as st
from streamlit.components.v1 import html
from src.ui.sidebar import render_sidebar
from src.ui.search_interface import render_search_interface
from src.ui.file_viewer import render_file_viewer
from src.ui.activity_logging import has_pending_log_decisions


def _render_beforeunload_warning(enable_warning):
    """Best-effort browser warning when user tries to close or refresh with pending decisions."""
    if enable_warning:
        html(
            """
            <script>
            const msg = "You still need to choose Log Activity or Skip Log before leaving this QC session.";
            window.parent.onbeforeunload = () => msg;
            </script>
            """,
            height=0,
        )
    else:
        html(
            """
            <script>
            window.parent.onbeforeunload = null;
            </script>
            """,
            height=0,
        )


def main():
    st.set_page_config(page_title="GGIR QC Tool", page_icon="📊", layout="wide")
    st.title("GGIR QC Tool")
    st.markdown("---")
    
    if not render_sidebar():
        st.stop()

    _render_beforeunload_warning(has_pending_log_decisions(st.session_state))
    
    files_found, _ = render_search_interface()
    
    if files_found or st.session_state.get("participant_id"):
        render_file_viewer()


if __name__ == "__main__":
    main()
