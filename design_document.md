# Design Document: Secure Participant File Finder & Editor (GGIR QC Tool)

**Last Updated:** November 19, 2025

## 1. Overview

This document outlines the design and implementation of the Secure Participant File Finder & Editor, a Streamlit application that provides authorized users with a simple, secure interface to find and interact with participant files stored in a structured Google Drive folder. Users select an accelerometer type from a predefined list and enter a participant ID. The application navigates a hierarchical folder structure (`accelerometer_name/participant_ID/output_participant_ID/results/`) to access three specific files: one editable CSV file and two read-only PDF documents. When users save edits to the CSV, the application automatically creates a new versioned copy, ensuring a clear audit trail and protecting the integrity of original data.

## 2. Goals and Objectives

- **Secure Access**: Ensure only pre-approved Google accounts can use the application.
- **Targeted File Access**: Provide a simple interface to open a predefined set of three files using an accelerometer type and a participant ID.
- **Controlled Editing**: Allow users to edit the contents of the participant's primary CSV data file in a controlled environment.
- **Data Integrity & Versioning**: Prevent overwriting of original data by saving all edits to the CSV as a new, sequentially versioned file.
- **Ease of Management**: Allow administrators to manage the user access list dynamically without modifying application code.

## 3. System Architecture and Design

The architecture supports both reading PDF links and a full read/write/version cycle for the CSV file, leveraging serverless cloud components and a hierarchical folder structure in Google Drive.

### 3.1 Components

- **Frontend (UI)**: A web interface built with Streamlit featuring:
  - Sidebar authentication with email input
  - Dropdown selector for accelerometer types (ActiGraph, GENEActiv, Axivity, ActiSleep, Other)
  - Text input field for participant ID
  - Search button to locate participant files
  - Clickable links to two read-only PDF files
  - Interactive data editor widget (`st.data_editor`) with dynamic row support for the CSV file
  - Save button with versioning information
  - Success/error notifications with detailed logging

- **Backend Logic**: A single, well-commented Python script (`app.py`, ~541 lines) that handles:
  - Google Drive API service initialization using service account credentials
  - Google Sheets API service initialization for allowlist management
  - User authorization checking against Google Sheets allowlist
  - Hierarchical folder navigation in Google Drive
  - File discovery and content retrieval
  - CSV download and DataFrame conversion
  - Automatic version detection and incremental versioning
  - CSV upload with versioned filenames

- **Hosting Platform**: Streamlit Community Cloud, which serves the application and securely manages credentials via Streamlit Secrets

- **Data Sources**:
  - **Google Drive**: A root folder containing hierarchical structure:
    - `[Accelerometer Type]/[Participant ID]/output_[Participant ID]/results/`
    - Contains: `part4_nightsummary_sleep_cleaned.csv`, `visualisation_sleep.pdf`, `visualisation_data.pdf`
  - **Google Sheets**: An allowlist spreadsheet storing authorized user email addresses (typically in column A)

### 3.2 Data Access and Editing Flow

1. **Authentication**: User enters their email address in the sidebar. The application queries the Google Sheets allowlist and validates authorization. Unauthorized users are blocked with an error message.

2. **File Search**: User selects an accelerometer type from the dropdown (e.g., "ActiGraph") and enters a participant ID (e.g., "PID123"), then clicks "Search Files."

3. **Path Construction**: The backend constructs the hierarchical path: `[Accelerometer]/[Participant ID]/output_[Participant ID]/results/`

4. **Folder Navigation**: Using the `find_folder_by_path()` function, the application:
   - Starts from the root folder ID (from secrets)
   - Navigates through each folder level using Google Drive API queries
   - Returns the target folder ID if found, or displays an error if not found

5. **File Discovery**: The application searches for three specific files in the target folder:
   - `part4_nightsummary_sleep_cleaned.csv` (editable)
   - `visualisation_sleep.pdf` (read-only)
   - `visualisation_data.pdf` (read-only)

6. **Display Results**:
   - PDF files: Displayed as hyperlinks using their `webViewLink` property
   - CSV file: Downloaded via `download_csv_content()`, converted to pandas DataFrame, and displayed in `st.data_editor` with dynamic row editing enabled

7. **Editing**: User modifies data in the interactive grid (can add, delete, or edit rows)

8. **Saving with Versioning**:
   - User clicks "Save Changes"
   - `get_next_version_number()` scans the folder for existing versions (e.g., `_v1`, `_v2`)
   - `upload_versioned_csv()` creates a new file with incremented version number
   - Original file remains untouched
   - Success message displays new filename, web view link, user details, and timestamp

9. **Audit Trail**: Each save operation logs user email, timestamp, participant ID, and accelerometer type for tracking purposes.

### 3.3 Design Philosophy

**Simplicity and Minimalism**: The implementation will prioritize simplicity, clarity, and a minimalistic user interface. The backend logic will be contained within a single, well-commented Python script to ensure maintainability and ease of understanding.

## 4. Requirements

### 4.1 Functional Requirements

The system shall:

- Require users to authenticate via their Google account.
- Restrict access based on a Google Sheet allowlist.
- Provide a dropdown menu to select an accelerometer type from a hardcoded list.
- Provide a text input field to search for a participant ID.
- Upon search, navigate to a folder path constructed from the selected accelerometer and participant ID (e.g., `[accelerometer_name]/[participant_id]/`).
- Retrieve and display three specific files from that folder based on hardcoded naming patterns:
  - One CSV file (e.g., `/output_[participant_id]/results/part4_nightsummary_sleep_cleaned.csv`), which will be displayed in an editable grid.
  - Two PDF files (e.g., `/output_[participant_id]/results/visualisation_sleep.pdf` and `visualisation_data.pdf`), which will be displayed as read-only hyperlinks.
- Provide a "Save Changes" button for the editable CSV data.
- Upon saving, create a new version of the CSV file in its original Google Drive folder, appending an incremental version suffix (e.g., `_v1`, `_v2`).
- Never overwrite or modify an existing file.

### 4.2 Security Requirements

The system shall:

- **Credential Management**: Store all sensitive credentials in Streamlit Community Cloud Secrets (never in code repository):
  - `google_service_account`: Complete JSON service account credentials
  - `root_folder_id`: Google Drive root folder ID
  - `allowlist_sheet_id`: Google Sheets spreadsheet ID for authorization
  - `allowlist_range`: Cell range for authorized emails (default: "Sheet1!A:A")

- **Authentication**: Use Google Service Account authentication with appropriate OAuth scopes:
  - `https://www.googleapis.com/auth/drive` for Drive API access
  - `https://www.googleapis.com/auth/spreadsheets.readonly` for Sheets API access

- **Authorization**: Implement email-based allowlist checking:
  - Fetch authorized users from Google Sheets with 5-minute cache (`@st.cache_data(ttl=300)`)
  - Perform case-insensitive email comparison
  - Block unauthorized users immediately with error message

- **Service Account Permissions**: The service account must have:
  - Viewer access to the allowlist Google Sheet
  - Editor/Contributor access to the root Google Drive folder (to create versioned files)
  - Access to all participant subfolders

- **API Service Caching**: Cache Google API service instances for 10 minutes (`@st.cache_resource(ttl=600)`) to improve performance and reduce authentication overhead

- **Session Management**: Use Streamlit session state to maintain user authorization status and prevent re-authentication on every interaction

## 5. Deployment and Maintenance

### 5.1 Deployment

The application will be deployed from its GitHub repository to Streamlit Community Cloud. The deployment process is continuous, meaning any changes pushed to the main branch will automatically trigger a redeployment.

### 5.2 User Management (Rolling Basis)

Managing user access requires no code changes or redeployment:

- **To Add a User**: 
  1. Open the designated allowlist Google Sheet
  2. Add the new user's email address in column A
  3. Changes take effect within 5 minutes (cache refresh interval)

- **To Remove a User**: 
  1. Open the allowlist Google Sheet
  2. Delete the row containing the user's email address
  3. User will be denied access within 5 minutes

The application caches the authorized user list for 5 minutes using `@st.cache_data(ttl=300)`, balancing performance with timely access control updates.

## 6. Technical Implementation Details

### 6.1 Key Functions

**Authentication & Authorization:**
- `get_google_drive_service()`: Initializes Drive API service with cached credentials (10-min TTL)
- `get_google_sheets_service()`: Initializes Sheets API service with cached credentials (10-min TTL)
- `get_authorized_users()`: Fetches and caches allowlist from Google Sheets (5-min TTL)
- `check_user_authorization(email)`: Validates user email against allowlist

**Google Drive Operations:**
- `find_folder_by_path(service, root_id, path_components)`: Navigates folder hierarchy recursively
- `find_file_in_folder(service, folder_id, filename)`: Searches for specific file in folder
- `download_csv_content(service, file_id)`: Downloads CSV and converts to pandas DataFrame
- `get_next_version_number(service, folder_id, base_filename)`: Determines next version number by scanning existing files
- `upload_versioned_csv(service, folder_id, base_filename, dataframe)`: Creates and uploads new versioned CSV file

**UI Components:**
- Sidebar: Authentication, user info, and about section
- Main area: File search interface, PDF links, editable data grid, save functionality

### 6.2 Configuration Constants

```python
ACCELEROMETER_TYPES = ["ActiGraph", "GENEActiv", "Axivity", "ActiSleep", "Other"]
CSV_FILENAME = "part4_nightsummary_sleep_cleaned.csv"
PDF_FILENAME_1 = "visualisation_sleep.pdf"
PDF_FILENAME_2 = "visualisation_data.pdf"
```

### 6.3 Error Handling

The application includes comprehensive error handling for:
- Failed API service initialization
- Missing or inaccessible folders
- File not found scenarios
- Download/upload failures
- Invalid credentials or permissions

All errors display user-friendly messages in the Streamlit UI.

### 6.4 Performance Optimizations

- **API Service Caching**: 10-minute cache for Google API services
- **Allowlist Caching**: 5-minute cache for authorized users list
- **Efficient Queries**: Uses Google Drive API filters to minimize data transfer
- **Session State**: Maintains user context without re-fetching data

## 7. Future Enhancements

Potential improvements for future versions:

- Add support for multiple CSV files per participant
- Implement bulk participant file operations
- Add data validation rules before saving
- Include version comparison/diff viewer
- Add export functionality for multiple file formats
- Implement role-based permissions (viewer vs. editor)
- Add audit log export functionality
- Support for custom accelerometer types
