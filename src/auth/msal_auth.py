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


def _acquire_access_token():
    """Acquire access token without Streamlit caching or UI side effects."""
    client_id, client_secret, tenant_id = _get_credentials()

    if not all([client_id, client_secret, tenant_id]):
        return None, (
            "Azure credentials not configured. "
            "Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID."
        )

    try:
        authority = settings.AUTHORITY_URL.format(tenant_id=tenant_id)
        app = msal.ConfidentialClientApplication(
            client_id, client_credential=client_secret, authority=authority
        )
        result = app.acquire_token_for_client(scopes=settings.SCOPES)

        if "access_token" in result:
            return result["access_token"], None
        return None, f"Token error: {result.get('error_description', 'Unknown')}"
    except Exception as e:
        return None, f"Error acquiring token: {e}"


@st.cache_data(ttl=3600)
def get_access_token():
    """Acquire access token for Microsoft Graph API (cached 1 hour)."""
    token, error = _acquire_access_token()
    if error:
        st.error(error)
    return token


def get_access_token_uncached():
    """Acquire access token for non-Streamlit contexts (no caching)."""
    token, error = _acquire_access_token()
    if error:
        raise RuntimeError(error)
    return token
