"""Microsoft Authentication Library (MSAL) Integration"""

import os
import streamlit as st
import msal
from config import settings


def _get_credentials():
    """Get Azure credentials from environment variables or Streamlit secrets."""
    client_id = os.getenv("AZURE_CLIENT_ID") or st.secrets.get("azure", {}).get("client_id")
    client_secret = os.getenv("AZURE_CLIENT_SECRET") or st.secrets.get("azure", {}).get("client_secret")
    tenant_id = os.getenv("AZURE_TENANT_ID") or st.secrets.get("azure", {}).get("tenant_id")
    return client_id, client_secret, tenant_id


@st.cache_data(ttl=3600)
def get_access_token():
    """Acquire access token for Microsoft Graph API (cached 1 hour)."""
    client_id, client_secret, tenant_id = _get_credentials()
    
    if not all([client_id, client_secret, tenant_id]):
        st.error("Azure credentials not configured. Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID.")
        return None
    
    try:
        authority = settings.AUTHORITY_URL.format(tenant_id=tenant_id)
        app = msal.ConfidentialClientApplication(client_id, client_credential=client_secret, authority=authority)
        result = app.acquire_token_for_client(scopes=settings.SCOPES)
        
        if "access_token" in result:
            return result["access_token"]
        st.error(f"Token error: {result.get('error_description', 'Unknown')}")
        return None
    except Exception as e:
        st.error(f"Error acquiring token: {e}")
        return None
