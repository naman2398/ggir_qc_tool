"""
User Authorization Module
"""

import streamlit as st
import pandas as pd
import requests
import io
from urllib.parse import quote
from config import settings
from src.api.file_operations import get_drive_id


@st.cache_data(ttl=600)
def get_authorized_users(_access_token):
    """Fetch authorized emails from App_Access_List.xlsx (cached 10 min)."""
    try:
        drive_id = get_drive_id(_access_token)
        file_path = f"{settings.ROOT_FOLDER_PATH}/{settings.ACCESS_LIST_FILE}"
        encoded_path = quote(file_path, safe="/")
        
        # Get file content
        url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/root:/{encoded_path}:/content"
        resp = requests.get(url, headers={"Authorization": f"Bearer {_access_token}"})
        resp.raise_for_status()
        
        # Read Excel and extract emails from first column
        df = pd.read_excel(io.BytesIO(resp.content))
        return df.iloc[:, 0].dropna().astype(str).str.strip().str.lower().tolist()
    except Exception as e:
        st.error(f"Failed to fetch authorized users: {e}")
        return []


def check_user_authorization(access_token, user_email):
    """Check if user email is authorized."""
    return user_email.lower() in get_authorized_users(access_token)
