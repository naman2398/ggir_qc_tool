"""Sidebar UI Component"""

import streamlit as st
from src.auth.msal_auth import get_access_token
from src.auth.user_auth import check_user_authorization


def render_sidebar():
    """Render auth sidebar. Returns True if authorized."""
    with st.sidebar:
        st.header("🔐 Login")
        
        user_email = st.text_input("Email Address", placeholder="user@stonybrook.edu")
        
        if user_email:
            access_token = get_access_token()
            if not access_token:
                st.error("❌ Failed to authenticate with Azure")
                st.stop()
            
            if check_user_authorization(access_token, user_email):
                st.success("✅ Authorized")
                st.session_state["authorized"] = True
                st.session_state["user_email"] = user_email
                st.session_state["access_token"] = access_token
            else:
                st.error("❌ Unauthorized access")
                st.info("Your email is not on the access list.")
                st.session_state["authorized"] = False
                st.stop()
        else:
            st.info("Please enter your email to access the application.")
            st.stop()
        
        st.markdown("---")
        st.markdown("**GGIR QC Tool** v3.4\n\nStony Brook University")
    
    return st.session_state.get("authorized", False)
