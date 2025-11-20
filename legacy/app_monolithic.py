"""
Secure Participant File Finder & Editor (GGIR QC Tool)

This Streamlit application provides authorized users at Stony Brook University 
with a simple, secure interface to find and interact with participant files 
stored in Microsoft OneDrive for Business or SharePoint.

Users select an accelerometer type (and phase if applicable) and enter a 
participant ID to access:
- One editable CSV file
- Two read-only PDF files

All CSV edits are saved as new versioned files to maintain data integrity.
"""

import streamlit as st
import pandas as pd
import msal
import requests
import io
from datetime import datetime
import os

# Import configuration
import config

# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

def get_msal_app():
    """
    Initialize and return the MSAL Confidential Client Application.
    Uses environment variables or Streamlit secrets for credentials.
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


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_authorized_users():
    """
    Fetch the list of authorized user emails from the App_Access_List.xlsx file.
    Returns a list of email addresses (lowercase for case-insensitive comparison).
    """
    try:
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
    """
    authorized_users = get_authorized_users()
    return user_email.lower() in authorized_users


# ============================================================================
# MICROSOFT GRAPH API OPERATIONS
# ============================================================================

def build_folder_path(device, phase, participant_id):
    """
    Build the folder path based on device, phase, and participant ID.
    
    Args:
        device: Selected device name
        phase: Selected phase (or None)
        participant_id: Participant ID
    
    Returns:
        Constructed folder path string
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
        access_token: Microsoft Graph API access token
        folder_path: Path to the folder (e.g., "device/pid/output_pid/results/")
        filename: Name of the file to find
    
    Returns:
        Dict with file information if found, None otherwise
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
        access_token: Microsoft Graph API access token
        file_id: ID of the file to download
    
    Returns:
        pandas DataFrame if successful, None otherwise
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
        access_token: Microsoft Graph API access token
        folder_path: Path to the folder containing the files
        base_filename: Base filename without version suffix (e.g., "data.csv")
    
    Returns:
        Next version number (integer)
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
        access_token: Microsoft Graph API access token
        folder_path: Path to the folder to upload to
        base_filename: Base filename without version suffix
        dataframe: pandas DataFrame to save
    
    Returns:
        Dict with new file information if successful, None otherwise
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


# ============================================================================
# STREAMLIT UI
# ============================================================================

def main():
    """
    Main application function.
    """
    # Page configuration
    st.set_page_config(
        page_title="GGIR QC Tool",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 GGIR QC Tool")
    st.markdown("Secure Participant File Finder & Editor")
    st.markdown("---")
    
    # Sidebar for authentication
    with st.sidebar:
        st.header("🔐 Login")
        
        user_email = st.text_input(
            "Email Address",
            placeholder="user@stonybrook.edu"
        )
        
        if user_email:
            if check_user_authorization(user_email):
                st.success(f"✅ Authorized")
                st.session_state['authorized'] = True
                st.session_state['user_email'] = user_email
            else:
                st.error("❌ Unauthorized access")
                st.info("Your email is not on the access list. Please contact the administrator.")
                st.session_state['authorized'] = False
                st.stop()
        else:
            st.info("Please enter your email to access the application.")
            st.stop()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        **GGIR QC Tool**
        
        Quality control tool for GGIR accelerometer data outputs.
        
        Stony Brook University  
        Version 3.4
        """)
    
    # Main content area
    if not st.session_state.get('authorized', False):
        st.warning("⚠️ Please authenticate using the sidebar.")
        st.stop()
    
    # File search interface
    st.header("🔍 Find Participant Files")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        selected_device = st.selectbox(
            "Device Type",
            config.SUPPORTED_DEVICES
        )
    
    # Conditional phase selection
    selected_phase = None
    if selected_device in config.DEVICE_PHASE_MAPPING:
        with col1:
            selected_phase = st.selectbox(
                "Study Phase",
                config.DEVICE_PHASE_MAPPING[selected_device]
            )
    
    with col2:
        participant_id = st.text_input(
            "Participant ID",
            placeholder="e.g., PID123"
        )
    
    search_button = st.button("🔎 Search Files", type="primary")
    
    if search_button and participant_id:
        with st.spinner("Searching for files..."):
            # Get access token
            access_token = get_access_token()
            
            if not access_token:
                st.error("❌ Failed to authenticate with Microsoft Graph API.")
                st.stop()
            
            # Build folder path
            folder_path = build_folder_path(selected_device, selected_phase, participant_id)
            
            # Display the path being searched
            st.info(f"📁 Searching: `{folder_path}`")
            
            # Find the three target files
            csv_file = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['csv']
            )
            pdf_file_sleep = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['pdf_sleep']
            )
            pdf_file_data = find_file_in_folder(
                access_token, 
                folder_path, 
                config.TARGET_FILES['pdf_data']
            )
            
            # Check if folder exists (at least one file found)
            if not any([csv_file, pdf_file_sleep, pdf_file_data]):
                st.error(f"❌ No files found for {selected_device}/{participant_id}")
                st.info("Please verify the device type, phase (if applicable), and participant ID are correct.")
                st.stop()
            
            st.success(f"✅ Found participant folder!")
            
            # Store in session state
            st.session_state['participant_id'] = participant_id
            st.session_state['device'] = selected_device
            st.session_state['phase'] = selected_phase
            st.session_state['folder_path'] = folder_path
            st.session_state['csv_file'] = csv_file
            st.session_state['pdf_file_sleep'] = pdf_file_sleep
            st.session_state['pdf_file_data'] = pdf_file_data
            
            st.markdown("---")
    
    # Display files if we have participant data
    if st.session_state.get('participant_id'):
        participant_id = st.session_state['participant_id']
        device = st.session_state['device']
        phase = st.session_state.get('phase')
        folder_path = st.session_state['folder_path']
        csv_file = st.session_state.get('csv_file')
        pdf_file_sleep = st.session_state.get('pdf_file_sleep')
        pdf_file_data = st.session_state.get('pdf_file_data')
        
        st.header("📂 Participant Files")
        
        # Display path
        path_display = f"{device}"
        if phase:
            path_display += f" / {phase}"
        path_display += f" / {participant_id}"
        st.info(f"📁 **Path**: {path_display}")
        
        # Display PDF links
        st.subheader("📄 Reports (Read-Only)")
        
        col_pdf1, col_pdf2 = st.columns(2)
        
        with col_pdf1:
            if pdf_file_sleep:
                st.markdown(f"**{config.TARGET_FILES['pdf_sleep']}**")
                st.markdown(f"[🔗 Open PDF]({pdf_file_sleep['webUrl']})")
            else:
                st.warning(f"⚠️ {config.TARGET_FILES['pdf_sleep']} not found")
        
        with col_pdf2:
            if pdf_file_data:
                st.markdown(f"**{config.TARGET_FILES['pdf_data']}**")
                st.markdown(f"[🔗 Open PDF]({pdf_file_data['webUrl']})")
            else:
                st.warning(f"⚠️ {config.TARGET_FILES['pdf_data']} not found")
        
        st.markdown("---")
        
        # Display editable CSV
        st.subheader("✏️ Edit Data File")
        
        if csv_file:
            st.markdown(f"**{config.TARGET_FILES['csv']}**")
            
            # Initialize session state for data editing
            if 'original_df' not in st.session_state:
                access_token = get_access_token()
                df = download_csv_content(access_token, csv_file['id'])
                
                if df is not None:
                    st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
                    st.session_state['original_df'] = df.copy()
                    st.session_state['current_df'] = df.copy()
                else:
                    st.error("❌ Failed to load CSV file.")
                    st.stop()
            
            # Editable data editor
            edited_df = st.data_editor(
                st.session_state['current_df'],
                use_container_width=True,
                num_rows="dynamic",
                key="data_editor"
            )
            
            # Check if data was modified
            data_changed = not edited_df.equals(st.session_state['current_df'])
            
            # Save button and status
            col_save, col_status = st.columns([1, 2])
            
            with col_save:
                save_button = st.button(
                    "💾 Save Changes",
                    type="primary",
                    disabled=not data_changed
                )
            
            with col_status:
                if data_changed:
                    st.warning("⚠️ Unsaved changes")
                else:
                    st.success("✅ All changes saved")
            
            # Handle save action
            if save_button and data_changed:
                with st.spinner("Saving new version..."):
                    access_token = get_access_token()
                    
                    # Upload versioned file
                    new_file = upload_versioned_csv(
                        access_token,
                        folder_path,
                        config.TARGET_FILES['csv'],
                        edited_df
                    )
                    
                    if new_file:
                        # Update current state
                        st.session_state['current_df'] = edited_df.copy()
                        
                        st.success(f"✅ Successfully saved as: **{new_file['name']}**")
                        st.markdown(f"[🔗 View file]({new_file['webUrl']})")
                        
                        # Log the save action
                        with st.expander("📋 Save Details"):
                            st.markdown(f"""
                            - **User**: {st.session_state.get('user_email', 'Unknown')}
                            - **Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                            - **Participant ID**: {participant_id}
                            - **Device**: {device}
                            - **Phase**: {phase if phase else 'N/A'}
                            - **File**: {new_file['name']}
                            """)
                    else:
                        st.error("❌ Failed to save the file. Please try again.")
        else:
            st.warning(f"⚠️ {config.TARGET_FILES['csv']} not found in the participant folder.")
    
    elif search_button:
        st.warning("⚠️ Please enter a Participant ID.")


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
