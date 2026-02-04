"""Authentication Module"""

from .msal_auth import get_access_token
from .user_auth import get_app_password, check_password_authorization

# Commented out - requires SharePoint access for App_Access_List.xlsx
# from .user_auth import get_authorized_users, check_user_authorization

__all__ = [
    "get_access_token",
    "get_app_password",
    "check_password_authorization",
    # "get_authorized_users",
    # "check_user_authorization"
]
