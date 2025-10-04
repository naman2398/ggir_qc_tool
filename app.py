"""
Secure Participant File Finder & Editor

This Streamlit application provides authorized users with a simple interface
to find and interact with participant files stored in Google Drive.

Users select an accelerometer type and enter a participant ID to access:
- One editable CSV file
- Two read-only PDF files

All CSV edits are saved as new versioned files to maintain data integrity.
"""

import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Hardcoded list of accelerometer types
ACCELEROMETER_TYPES = [
    "ActiGraph",
    "GENEActiv",
    "Axivity",
    "ActiSleep",
    "Other"
]

# Hardcoded filenames to search for
CSV_FILENAME = "part4_nightsummary_sleep_cleaned.csv"
PDF_FILENAME_1 = "visualisation_sleep.pdf"
PDF_FILENAME_2 = "visualisation_data.pdf"

# ============================================================================
# AUTHENTICATION & AUTHORIZATION
# ============================================================================

@st.cache_resource(ttl=600)  # Cache for 10 minutes
def get_google_drive_service():
    """
    Initialize and return the Google Drive API service using Service Account credentials.
    Credentials are loaded from Streamlit secrets.
    """
    try:
        # Load service account credentials from Streamlit secrets
        credentials_dict = st.secrets["google_service_account"]
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Failed to initialize Google Drive service: {str(e)}")
        return None


@st.cache_resource(ttl=600)  # Cache for 10 minutes
def get_google_sheets_service():
    """
    Initialize and return the Google Sheets API service using Service Account credentials.
    """
    try:
        credentials_dict = st.secrets["google_service_account"]
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        return service
    except Exception as e:
        st.error(f"Failed to initialize Google Sheets service: {str(e)}")
        return None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_authorized_users():
    """
    Fetch the list of authorized user emails from the Google Sheet allowlist.
    Returns a list of email addresses (lowercase for case-insensitive comparison).
    """
    try:
        sheets_service = get_google_sheets_service()
        if not sheets_service:
            return []
        
        spreadsheet_id = st.secrets.get("allowlist_sheet_id", "")
        range_name = st.secrets.get("allowlist_range", "Sheet1!A:A")
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        # Flatten list and convert to lowercase, skip empty rows
        emails = [row[0].strip().lower() for row in values if row and row[0].strip()]
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
# GOOGLE DRIVE OPERATIONS
# ============================================================================

def find_folder_by_path(service, root_folder_id, path_components):
    """
    Navigate through Google Drive folder hierarchy to find a folder.
    
    Args:
        service: Google Drive API service instance
        root_folder_id: ID of the root folder to start searching from
        path_components: List of folder names representing the path
    
    Returns:
        Folder ID if found, None otherwise
    """
    current_folder_id = root_folder_id
    
    for folder_name in path_components:
        query = f"name='{folder_name}' and '{current_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        try:
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=10
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                return None
            
            # Take the first matching folder
            current_folder_id = files[0]['id']
        except Exception as e:
            st.error(f"Error navigating to folder '{folder_name}': {str(e)}")
            return None
    
    return current_folder_id


def find_file_in_folder(service, folder_id, filename):
    """
    Find a specific file in a Google Drive folder.
    
    Args:
        service: Google Drive API service instance
        folder_id: ID of the folder to search in
        filename: Name of the file to find
    
    Returns:
        Dict with file information (id, name, webViewLink) if found, None otherwise
    """
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    
    try:
        results = service.files().list(
            q=query,
            fields="files(id, name, webViewLink, webContentLink)",
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            return files[0]
        return None
    except Exception as e:
        st.error(f"Error finding file '{filename}': {str(e)}")
        return None


def download_csv_content(service, file_id):
    """
    Download the content of a CSV file from Google Drive.
    
    Args:
        service: Google Drive API service instance
        file_id: ID of the file to download
    
    Returns:
        pandas DataFrame if successful, None otherwise
    """
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_content.seek(0)
        df = pd.read_csv(file_content)
        return df
    except Exception as e:
        st.error(f"Error downloading CSV file: {str(e)}")
        return None


def get_next_version_number(service, folder_id, base_filename):
    """
    Determine the next version number for a file by checking existing versions.
    
    Args:
        service: Google Drive API service instance
        folder_id: ID of the folder containing the files
        base_filename: Base filename without version suffix (e.g., "data.csv")
    
    Returns:
        Next version number (integer)
    """
    # Extract base name and extension
    if '.' in base_filename:
        name_part, ext = base_filename.rsplit('.', 1)
    else:
        name_part = base_filename
        ext = ''
    
    # Search for files with version pattern
    version_pattern = f"{name_part}_v"
    query = f"'{folder_id}' in parents and trashed=false and name contains '{version_pattern}'"
    
    try:
        results = service.files().list(
            q=query,
            fields="files(name)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        max_version = 0
        for file in files:
            filename = file['name']
            # Extract version number (e.g., "data_v3.csv" -> 3)
            try:
                if ext:
                    version_str = filename.replace(name_part + '_v', '').replace('.' + ext, '')
                else:
                    version_str = filename.replace(name_part + '_v', '')
                version_num = int(version_str)
                max_version = max(max_version, version_num)
            except ValueError:
                continue
        
        return max_version + 1
    except Exception as e:
        st.error(f"Error determining version number: {str(e)}")
        return 1


def upload_versioned_csv(service, folder_id, base_filename, dataframe):
    """
    Upload a new versioned CSV file to Google Drive.
    
    Args:
        service: Google Drive API service instance
        folder_id: ID of the folder to upload to
        base_filename: Base filename without version suffix
        dataframe: pandas DataFrame to save
    
    Returns:
        Dict with new file information if successful, None otherwise
    """
    try:
        # Get next version number
        version_num = get_next_version_number(service, folder_id, base_filename)
        
        # Create versioned filename
        if '.' in base_filename:
            name_part, ext = base_filename.rsplit('.', 1)
            new_filename = f"{name_part}_v{version_num}.{ext}"
        else:
            new_filename = f"{base_filename}_v{version_num}"
        
        # Convert DataFrame to CSV
        csv_buffer = io.StringIO()
        dataframe.to_csv(csv_buffer, index=False)
        csv_bytes = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
        
        # Upload file
        file_metadata = {
            'name': new_filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(
            io.BytesIO(csv_bytes.getvalue()),
            mimetype='text/csv',
            resumable=True
        )
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        return file
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
        page_title="Participant File Finder & Editor",
        page_icon="📁",
        layout="wide"
    )
    
    st.title("🔐 Secure Participant File Finder & Editor")
    st.markdown("---")
    
    # Authentication check (placeholder for OAuth implementation)
    # In production, this would use actual OAuth 2.0 authentication
    # For now, we'll use a simple email input for demonstration
    
    with st.sidebar:
        st.header("User Authentication")
        user_email = st.text_input(
            "Enter your email address:",
            placeholder="user@stonybrook.edu"
        )
        
        if user_email:
            if check_user_authorization(user_email):
                st.success(f"✅ Authorized: {user_email}")
                st.session_state['authorized'] = True
                st.session_state['user_email'] = user_email
            else:
                st.error("❌ Unauthorized: Your email is not on the access list.")
                st.session_state['authorized'] = False
                st.stop()
        else:
            st.info("Please enter your email to access the application.")
            st.stop()
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This application provides secure access to participant files 
        stored in Google Drive. You can view PDFs and edit CSV files 
        with automatic versioning.
        """)
    
    # Main content area
    if not st.session_state.get('authorized', False):
        st.warning("Please authenticate using the sidebar.")
        st.stop()
    
    # File search interface
    st.header("🔍 Find Participant Files")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_accelerometer = st.selectbox(
            "Select Accelerometer Type:",
            ACCELEROMETER_TYPES
        )
    
    with col2:
        participant_id = st.text_input(
            "Enter Participant ID:",
            placeholder="e.g., PID123"
        )
    
    search_button = st.button("🔎 Search Files", type="primary")
    
    if search_button and participant_id:
        with st.spinner("Searching for files..."):
            # Initialize Google Drive service
            drive_service = get_google_drive_service()
            
            if not drive_service:
                st.error("Failed to connect to Google Drive. Please check your configuration.")
                st.stop()
            
            # Get root folder ID from secrets
            root_folder_id = st.secrets.get("root_folder_id", "")
            
            if not root_folder_id:
                st.error("Root folder ID not configured. Please contact the administrator.")
                st.stop()
            
            # Construct path: accelerometer_name/participant_ID/output_participant_ID/results/
            path_components = [
                selected_accelerometer,
                participant_id,
                f"output_{participant_id}",
                "results"
            ]
            
            # Find the target folder
            target_folder_id = find_folder_by_path(drive_service, root_folder_id, path_components)
            
            if not target_folder_id:
                st.error(f"❌ Could not find folder for {selected_accelerometer}/{participant_id}")
                st.info("Please verify the accelerometer type and participant ID are correct.")
                st.stop()
            
            st.success(f"✅ Found participant folder!")
            
            # Store in session state
            st.session_state['target_folder_id'] = target_folder_id
            st.session_state['participant_id'] = participant_id
            st.session_state['accelerometer'] = selected_accelerometer
            
            # Find the three files
            csv_file = find_file_in_folder(drive_service, target_folder_id, CSV_FILENAME)
            pdf_file_1 = find_file_in_folder(drive_service, target_folder_id, PDF_FILENAME_1)
            pdf_file_2 = find_file_in_folder(drive_service, target_folder_id, PDF_FILENAME_2)
            
            st.markdown("---")
            st.header("📂 Participant Files")
            
            # Display PDF links
            st.subheader("📄 View Reports (Read-Only)")
            
            col_pdf1, col_pdf2 = st.columns(2)
            
            with col_pdf1:
                if pdf_file_1:
                    st.markdown(f"**{PDF_FILENAME_1}**")
                    st.markdown(f"[🔗 Open PDF]({pdf_file_1.get('webViewLink', '')})")
                else:
                    st.warning(f"⚠️ {PDF_FILENAME_1} not found")
            
            with col_pdf2:
                if pdf_file_2:
                    st.markdown(f"**{PDF_FILENAME_2}**")
                    st.markdown(f"[🔗 Open PDF]({pdf_file_2.get('webViewLink', '')})")
                else:
                    st.warning(f"⚠️ {PDF_FILENAME_2} not found")
            
            st.markdown("---")
            
            # Display editable CSV
            st.subheader("✏️ Edit Data File")
            
            if csv_file:
                st.markdown(f"**{CSV_FILENAME}**")
                
                # Download and display CSV
                df = download_csv_content(drive_service, csv_file['id'])
                
                if df is not None:
                    st.info(f"📊 Loaded {len(df)} rows × {len(df.columns)} columns")
                    
                    # Store original data in session state
                    st.session_state['original_df'] = df
                    st.session_state['csv_file_id'] = csv_file['id']
                    
                    # Editable data editor
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        num_rows="dynamic",
                        key="data_editor"
                    )
                    
                    # Save button
                    col_save, col_info = st.columns([1, 3])
                    
                    with col_save:
                        save_button = st.button("💾 Save Changes", type="primary")
                    
                    with col_info:
                        st.info("💡 Saving will create a new versioned file (e.g., *_v1.csv)")
                    
                    if save_button:
                        with st.spinner("Saving new version..."):
                            # Upload versioned file
                            new_file = upload_versioned_csv(
                                drive_service,
                                target_folder_id,
                                CSV_FILENAME,
                                edited_df
                            )
                            
                            if new_file:
                                st.success(f"✅ Successfully saved as: **{new_file['name']}**")
                                st.markdown(f"[🔗 View file]({new_file.get('webViewLink', '')})")
                                
                                # Log the save action
                                st.info(f"""
                                **Save Details:**
                                - User: {st.session_state.get('user_email', 'Unknown')}
                                - Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                - Participant: {participant_id}
                                - Accelerometer: {selected_accelerometer}
                                """)
                            else:
                                st.error("❌ Failed to save the file. Please try again.")
                else:
                    st.error("❌ Failed to load CSV file content.")
            else:
                st.warning(f"⚠️ {CSV_FILENAME} not found in the participant folder.")
    
    elif search_button:
        st.warning("⚠️ Please enter a Participant ID.")


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
