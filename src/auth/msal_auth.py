"""
Microsoft Authentication Library (MSAL) integration

Handles Azure AD authentication and token acquisition.
"""

import streamlit as st
import msal
import os
from config.settings import config


def get_msal_app():
    """
    Initialize and return the MSAL Confidential Client Application.
    Uses environment variables or Streamlit secrets for credentials.
    
    Returns:
        ConfidentialClientApplication: MSAL app instance or None if credentials missing
    """
    try:
        # Try to get from Streamlit secrets first, then fall back to env vars
        if hasattr(st, 'secrets') and 'azure' in st.secrets:
            client_id = st.secrets['azure'].get('client_id')
            client_secret = st.secrets['azure'].get('client_secret')
            tenant_id = st.secrets['azure'].get('tenant_id')
        else:
            client_id = os.getenv(config.ENV_CLIENT_ID)
            client_secret = os.getenv(config.ENV_CLIENT_SECRET)
            tenant_id = os.getenv(config.ENV_TENANT_ID)
        
        if not all([client_id, client_secret, tenant_id]):
            st.error("❌ Missing Azure credentials. Please configure CLIENT_ID, CLIENT_SECRET, and TENANT_ID.")
            return None
        
        authority = config.AUTHORITY_URL.format(tenant_id=tenant_id)
        
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret
        )
        
        return app
    except Exception as e:
        st.error(f"Failed to initialize MSAL app: {str(e)}")
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_access_token():
    """
    Acquire an access token for Microsoft Graph API using client credentials flow.
    
    Returns:
        str: Access token or None if acquisition fails
    """
    msal_app = get_msal_app()
    if not msal_app:
        return None
    
    try:
        result = msal_app.acquire_token_for_client(scopes=config.SCOPES)
        
        if "access_token" in result:
            return result["access_token"]
        else:
            error_desc = result.get("error_description", "Unknown error")
            st.error(f"Failed to acquire access token: {error_desc}")
            return None
    except Exception as e:
        st.error(f"Error acquiring access token: {str(e)}")
        return None
