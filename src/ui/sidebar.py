"""
Sidebar UI Component

Authentication and application information sidebar.
"""

import streamlit as st
from src.auth import check_user_authorization


def render_sidebar():
    """
    Render the authentication sidebar.
    
    Returns:
        bool: True if user is authorized, False otherwise
    """
    with st.sidebar:
        st.header("🔐 Login")
        
        user_email = st.text_input(
            "Email Address",
            placeholder="user@stonybrook.edu"
        )
        
        if user_email:
            if check_user_authorization(user_email):
                st.success(f"✅ Authorized")
                st.session_state['authorized'] = True
                st.session_state['user_email'] = user_email
            else:
                st.error("❌ Unauthorized access")
                st.info("Your email is not on the access list. Please contact the administrator.")
                st.session_state['authorized'] = False
                st.stop()
        else:
            st.info("Please enter your email to access the application.")
            st.stop()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        **GGIR QC Tool**
        
        Quality control tool for GGIR accelerometer data outputs.
        
        Stony Brook University  
        Version 3.4
        """)
    
    return st.session_state.get('authorized', False)
