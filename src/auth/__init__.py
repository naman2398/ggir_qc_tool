"""Authentication Module"""

from .msal_auth import get_access_token
from .user_auth import get_authorized_users, check_user_authorization

__all__ = [
    "get_access_token",
    "get_authorized_users",
    "check_user_authorization"
]
