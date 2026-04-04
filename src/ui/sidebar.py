"""Sidebar UI Component"""

import streamlit as st
from src.auth.msal_auth import get_access_token
from src.auth.user_auth import check_email_password_authorization, extract_username_from_email
from src.ui.activity_logging import (
    DECISION_LOGGED,
    DECISION_SKIPPED,
    decision_key,
    has_pending_log_decisions,
    pending_phase_labels,
    required_phase_labels,
)

# =============================================================================
# EXCEL-BASED USER AUTHORIZATION (Commented out - requires SharePoint access)
# Uncomment when SharePoint permissions are available for App_Access_List.xlsx
# =============================================================================
# from src.auth.user_auth import check_user_authorization


def render_sidebar():
    """Render auth sidebar. Returns True if authorized."""

    with st.sidebar:
        if st.session_state.get("authorized", False) and st.session_state.get("access_token"):
            st.header("🔐 Session")
            st.caption(f"User: {st.session_state.get('user_email', 'unknown')}")

            participant_id = st.session_state.get("participant_id")
            monitor = st.session_state.get("device")
            if participant_id and monitor:
                st.caption(f"Participant: {participant_id}")
                st.caption(f"Monitor: {monitor}")

                st.markdown("**Activity Logging**")
                phases = required_phase_labels(st.session_state)
                if phases:
                    completed = 0
                    for phase in phases:
                        d_key = decision_key(participant_id, monitor, phase)
                        decision = st.session_state.get(d_key)
                        if decision == DECISION_LOGGED:
                            completed += 1
                            st.caption(f"- {phase}: Logged")
                        elif decision == DECISION_SKIPPED:
                            completed += 1
                            st.caption(f"- {phase}: Skipped")
                        else:
                            st.caption(f"- {phase}: Pending")
                    st.caption(f"Progress: {completed}/{len(phases)} phase(s) decided")

            pending = has_pending_log_decisions(st.session_state)
            if pending:
                phases = ", ".join(pending_phase_labels(st.session_state))
                st.warning(
                    "Choose Log Activity or Skip Log before logout. "
                    f"Pending phase(s): {phases}"
                )

            if st.button("Logout", disabled=pending, key="logout_button"):
                st.session_state.clear()
                st.rerun()

            return True

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
