"""
User Authorization Module

Handles user access control using Excel-based allowlist.
"""

import streamlit as st
import pandas as pd
import requests
import io
import os
from config.settings import config


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_authorized_users():
    """
    Fetch the list of authorized user emails from the App_Access_List.xlsx file.
    
    Returns:
        list: Email addresses (lowercase for case-insensitive comparison)
    """
    try:
        from .msal_auth import get_access_token
        
        access_token = get_access_token()
        if not access_token:
            return []
        
        # Get access list file path from config
        if hasattr(st, 'secrets') and 'azure' in st.secrets:
            access_list_path = st.secrets['azure'].get('access_list_file', 'App_Access_List.xlsx')
        else:
            access_list_path = os.getenv(config.ENV_ACCESS_LIST_FILE, 'App_Access_List.xlsx')
        
        # Search for the access list file in SharePoint/OneDrive
        search_url = f"{config.GRAPH_API_ENDPOINT}/me/drive/root/search(q='{access_list_path}')"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        files = response.json().get('value', [])
        if not files:
            st.warning("⚠️ Access list file not found. Using empty authorization list.")
            return []
        
        # Download the first matching file
        file_id = files[0]['id']
        download_url = f"{config.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}/content"
        
        download_response = requests.get(download_url, headers=headers)
        download_response.raise_for_status()
        
        # Read Excel file
        excel_data = pd.read_excel(io.BytesIO(download_response.content))
        
        # Assume emails are in the first column
        emails = excel_data.iloc[:, 0].dropna().astype(str).str.strip().str.lower().tolist()
        
        return emails
    except Exception as e:
        st.error(f"Failed to fetch authorized users: {str(e)}")
        return []


def check_user_authorization(user_email):
    """
    Check if the provided user email is in the authorized users list.
    
    Args:
        user_email (str): Email address to check
        
    Returns:
        bool: True if authorized, False otherwise
    """
    authorized_users = get_authorized_users()
    return user_email.lower() in authorized_users
