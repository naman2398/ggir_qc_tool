"""
File Operations via Microsoft Graph API

All SharePoint/OneDrive file access and manipulation operations.
"""

import streamlit as st
import pandas as pd
import requests
import io
import os
from config.settings import config


def build_folder_path(device, phase, participant_id):
    """
    Build the folder path based on device, phase, and participant ID.
    
    Args:
        device (str): Selected device name
        phase (str): Selected phase (or None)
        participant_id (str): Participant ID
    
    Returns:
        str: Constructed folder path string
    """
    if phase:
        return config.PATH_TEMPLATE_PHASED.format(
            device=device,
            phase=phase,
            pid=participant_id
        )
    else:
        return config.PATH_TEMPLATE_STANDARD.format(
            device=device,
            pid=participant_id
        )


def find_file_in_folder(access_token, folder_path, filename):
    """
    Find a specific file in a SharePoint/OneDrive folder.
    
    Args:
        access_token (str): Microsoft Graph API access token
        folder_path (str): Path to the folder (e.g., "device/pid/output_pid/results/")
        filename (str): Name of the file to find
    
    Returns:
        dict: File information if found, None otherwise
    """
    try:
        # Get root folder path from config
        if hasattr(st, 'secrets') and 'azure' in st.secrets:
            root_path = st.secrets['azure'].get('root_folder_path', '')
        else:
            root_path = os.getenv(config.ENV_ROOT_FOLDER_PATH, '')
        
        # Combine root path with folder path
        full_path = f"{root_path}/{folder_path}".rstrip('/')
        
        # Construct the file path
        file_path = f"{full_path}/{filename}"
        
        # Try to get the file directly
        url = f"{config.GRAPH_API_ENDPOINT}/me/drive/root:/{file_path}"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            file_info = response.json()
            return {
                'id': file_info['id'],
                'name': file_info['name'],
                'webUrl': file_info.get('webUrl', ''),
                'downloadUrl': file_info.get('@microsoft.graph.downloadUrl', '')
            }
        else:
            return None
    except Exception as e:
        st.error(f"Error finding file '{filename}': {str(e)}")
        return None


def download_csv_content(access_token, file_id):
    """
    Download the content of a CSV file from SharePoint/OneDrive.
    
    Args:
        access_token (str): Microsoft Graph API access token
        file_id (str): ID of the file to download
    
    Returns:
        pd.DataFrame: DataFrame if successful, None otherwise
    """
    try:
        # Get download URL
        url = f"{config.GRAPH_API_ENDPOINT}/me/drive/items/{file_id}/content"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Read CSV into DataFrame
        csv_content = io.StringIO(response.content.decode('utf-8'))
        df = pd.read_csv(csv_content)
        
        return df
    except Exception as e:
        st.error(f"Error downloading CSV file: {str(e)}")
        return None


def get_next_version_number(access_token, folder_path, base_filename):
    """
    Determine the next version number for a file by checking existing versions.
    
    Args:
        access_token (str): Microsoft Graph API access token
        folder_path (str): Path to the folder containing the files
        base_filename (str): Base filename without version suffix (e.g., "data.csv")
    
    Returns:
        int: Next version number
    """
    try:
        # Extract base name and extension
        if '.' in base_filename:
            name_part, ext = base_filename.rsplit('.', 1)
        else:
            name_part = base_filename
            ext = ''
        
        # Get root folder path from config
        if hasattr(st, 'secrets') and 'azure' in st.secrets:
            root_path = st.secrets['azure'].get('root_folder_path', '')
        else:
            root_path = os.getenv(config.ENV_ROOT_FOLDER_PATH, '')
        
        # Combine root path with folder path
        full_path = f"{root_path}/{folder_path}".rstrip('/')
        
        # List files in the folder
        url = f"{config.GRAPH_API_ENDPOINT}/me/drive/root:/{full_path}:/children"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        files = response.json().get('value', [])
        
        max_version = 0
        version_pattern = f"{name_part}_v"
        
        for file in files:
            filename = file['name']
            if version_pattern in filename:
                try:
                    # Extract version number (e.g., "data_v3.csv" -> 3)
                    if ext:
                        version_str = filename.replace(version_pattern, '').replace(f'.{ext}', '')
                    else:
                        version_str = filename.replace(version_pattern, '')
                    version_num = int(version_str)
                    max_version = max(max_version, version_num)
                except ValueError:
                    continue
        
        return max_version + 1
    except Exception as e:
        st.error(f"Error determining version number: {str(e)}")
        return 1


def upload_versioned_csv(access_token, folder_path, base_filename, dataframe):
    """
    Upload a new versioned CSV file to SharePoint/OneDrive.
    
    Args:
        access_token (str): Microsoft Graph API access token
        folder_path (str): Path to the folder to upload to
        base_filename (str): Base filename without version suffix
        dataframe (pd.DataFrame): DataFrame to save
    
    Returns:
        dict: New file information if successful, None otherwise
    """
    try:
        # Get next version number
        version_num = get_next_version_number(access_token, folder_path, base_filename)
        
        # Create versioned filename
        if '.' in base_filename:
            name_part, ext = base_filename.rsplit('.', 1)
            new_filename = f"{name_part}_v{version_num}.{ext}"
        else:
            new_filename = f"{base_filename}_v{version_num}"
        
        # Convert DataFrame to CSV bytes
        csv_buffer = io.StringIO()
        dataframe.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode('utf-8')
        
        # Get root folder path from config
        if hasattr(st, 'secrets') and 'azure' in st.secrets:
            root_path = st.secrets['azure'].get('root_folder_path', '')
        else:
            root_path = os.getenv(config.ENV_ROOT_FOLDER_PATH, '')
        
        # Combine root path with folder path
        full_path = f"{root_path}/{folder_path}".rstrip('/')
        
        # Upload file
        file_path = f"{full_path}/{new_filename}"
        url = f"{config.GRAPH_API_ENDPOINT}/me/drive/root:/{file_path}:/content"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/csv'
        }
        
        response = requests.put(url, headers=headers, data=csv_bytes)
        response.raise_for_status()
        
        file_info = response.json()
        
        return {
            'id': file_info['id'],
            'name': file_info['name'],
            'webUrl': file_info.get('webUrl', '')
        }
    except Exception as e:
        st.error(f"Error uploading versioned file: {str(e)}")
        return None
