"""
Authentication module for GGIR QC Tool

Handles Microsoft Entra ID authentication and user authorization.
"""

from .msal_auth import get_msal_app, get_access_token
from .user_auth import get_authorized_users, check_user_authorization

__all__ = [
    'get_msal_app',
    'get_access_token',
    'get_authorized_users',
    'check_user_authorization'
]
