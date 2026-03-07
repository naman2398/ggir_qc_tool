"""User Authorization Module"""

import hmac
import os
import re
import streamlit as st
from config import settings


# =============================================================================
# SIMPLE PASSWORD AUTHENTICATION (Active)
# Uses APP_PASSWORD environment variable or Streamlit secrets
# =============================================================================

def get_app_password():
    """Get app password from environment variables or Streamlit secrets."""
    return os.getenv("APP_PASSWORD") or st.secrets.get("app", {}).get("password")


def check_password_authorization(input_password):
    """Check if the input password matches the configured app password."""
    app_password = get_app_password()
    if not app_password:
        st.error("App password not configured. Set APP_PASSWORD environment variable.")
        return False
    return hmac.compare_digest(input_password, app_password)


def extract_username_from_email(user_email):
    """Extract a filesystem-safe username from email local part."""
    if not user_email or "@" not in user_email:
        return "unknown_user"

    local_part = user_email.strip().lower().split("@", 1)[0]
    normalized = re.sub(r"[^a-z0-9]+", "_", local_part).strip("_")
    return normalized or "unknown_user"


def check_email_password_authorization(user_email, input_password):
    """Validate email format and app password."""
    if not user_email or "@" not in user_email:
        st.error("Please enter a valid email address.")
        return False
    return check_password_authorization(input_password)


# =============================================================================
# EXCEL-BASED USER AUTHORIZATION (Commented out - requires SharePoint access)
# Uncomment when SharePoint permissions are available for App_Access_List.xlsx
# =============================================================================

# @st.cache_data(ttl=600)
# def get_authorized_users(_access_token):
#     """Fetch authorized emails from App_Access_List.xlsx (cached 10 min)."""
#     try:
#         drive_id = get_drive_id(_access_token)
#         file_path = f"{settings.ROOT_FOLDER_PATH}/{settings.ACCESS_LIST_FILE}"
#         encoded_path = quote(file_path, safe="/")
#         
#         # Get file content
#         url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/content"
#         resp = requests.get(url, headers={"Authorization": f"Bearer {_access_token}"})
#         resp.raise_for_status()
#         
#         # Read Excel and extract emails from first column
#         df = pd.read_excel(io.BytesIO(resp.content))
#         return df.iloc[:, 0].dropna().astype(str).str.strip().str.lower().tolist()
#     except Exception as e:
#         st.error(f"Failed to fetch authorized users: {e}")
#         return []
# 
# 
# def check_user_authorization(access_token, user_email):
#     """Check if user email is authorized."""
#     return user_email.lower() in get_authorized_users(access_token)
