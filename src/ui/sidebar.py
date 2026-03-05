"""Sidebar UI Component"""

import streamlit as st
from src.auth.msal_auth import get_access_token
from src.auth.user_auth import check_email_password_authorization, extract_username_from_email

# =============================================================================
# EXCEL-BASED USER AUTHORIZATION (Commented out - requires SharePoint access)
# Uncomment when SharePoint permissions are available for App_Access_List.xlsx
# =============================================================================
# from src.auth.user_auth import check_user_authorization


def render_sidebar():
    """Render auth sidebar. Returns True if authorized."""
    
    # If already authorized, don't show login UI
    if st.session_state.get("authorized", False) and st.session_state.get("access_token"):
        return True
    
    with st.sidebar:
        st.header("🔐 Login")
        
        # =============================================================================
        # SIMPLE PASSWORD AUTHENTICATION (Active)
        # =============================================================================
        email_input = st.text_input("Email", placeholder="name@stonybrook.edu")
        password_input = st.text_input("Password", type="password", placeholder="Enter access password")
        login_button = st.button("Login", type="primary")

        if login_button:
            if check_email_password_authorization(email_input, password_input):
                # Get Azure access token for SharePoint operations
                access_token = get_access_token()
                if not access_token:
                    st.error("❌ Failed to authenticate with Azure")
                    st.stop()
                
                st.session_state["authorized"] = True
                st.session_state["user_email"] = email_input.strip().lower()
                st.session_state["username"] = extract_username_from_email(email_input)
                st.session_state["access_token"] = access_token
                st.rerun()  # Rerun to hide login UI
            else:
                st.session_state["authorized"] = False
                st.stop()
        else:
            st.info("Please enter your email and access password.")
            st.stop()
        
        # =============================================================================
        # EMAIL-BASED AUTHENTICATION (Commented out - requires SharePoint access)
        # Uncomment and comment out password auth above when App_Access_List.xlsx is accessible
        # =============================================================================
        # user_email = st.text_input("Email Address", placeholder="user@stonybrook.edu")
        # 
        # if user_email:
        #     access_token = get_access_token()
        #     if not access_token:
        #         st.error("❌ Failed to authenticate with Azure")
        #         st.stop()
        #     
        #     if check_user_authorization(access_token, user_email):
        #         st.success("✅ Authorized")
        #         st.session_state["authorized"] = True
        #         st.session_state["user_email"] = user_email
        #         st.session_state["access_token"] = access_token
        #     else:
        #         st.error("❌ Unauthorized access")
        #         st.info("Your email is not on the access list.")
        #         st.session_state["authorized"] = False
        #         st.stop()
        # else:
        #     st.info("Please enter your email to access the application.")
        #     st.stop()
    
    return st.session_state.get("authorized", False)
