# Design Document: Secure Participant File Finder & Editor



## 1. Overview

This document outlines the design for the Secure Participant File Finder & Editor. The application's purpose is to provide authorized users at Stony Brook University with a simple, secure interface to find and interact with participant files stored in a structured Google Drive folder. Users will select an accelerometer type from a predefined list and then enter a participant ID. Based on this combination, the application will navigate a hierarchical folder structure (`accelerometer_name/participant_ID/output_participant_ID/results/`) to open three hardcoded files: one editable CSV file and two read-only PDF documents. When a user saves the edited CSV, the application automatically creates a new, versioned copy, ensuring a clear audit trail and protecting the integrity of the original data.

## 2. Goals and Objectives

- **Secure Access**: Ensure only pre-approved Google accounts can use the application.
- **Targeted File Access**: Provide a simple interface to open a predefined set of three files using an accelerometer type and a participant ID.
- **Controlled Editing**: Allow users to edit the contents of the participant's primary CSV data file in a controlled environment.
- **Data Integrity & Versioning**: Prevent overwriting of original data by saving all edits to the CSV as a new, sequentially versioned file.
- **Ease of Management**: Allow administrators to manage the user access list dynamically without modifying application code.

## 3. System Architecture and Design

The architecture supports both reading PDF links and a full read/write/version cycle for the CSV file, leveraging serverless cloud components and a hierarchical folder structure in Google Drive.

### 3.1 Components

- **Frontend (UI)**: A web interface built with Streamlit. The UI will display:
  - A dropdown selector to choose from a predefined list of accelerometer types.
  - A text input field to enter the participant ID.
  - Clickable links to the two non-editable PDF files.
  - An interactive data editor widget (`st.data_editor`) for the editable CSV file.

- **Backend Logic**: A single Python script (`app.py`) handles user authentication, authorization, and all Google Drive API interactions.

- **Hosting Platform**: Streamlit Community Cloud, which serves the application and manages secure credentials.

- **Data Sources**:
  - **Google Drive**: A root folder containing subfolders for each accelerometer type, which in turn contain subfolders for each participant (e.g., `ActiGraph/PID123/`).
  - **Google Sheets**: A single sheet used as an "allowlist" to store the email addresses of authorized users.

### 3.2 Data Access and Editing Flow

1. An authorized user selects an accelerometer type (e.g., "ActiGraph") from the dropdown list.
2. The user enters a participant ID (e.g., PID123) and clicks "Search."
3. The backend logic constructs the target path (`ActiGraph/PID123/output_PID123/results/`) and queries Google Drive for three specific, hardcoded filenames within that participant's folder:
   - `part4_nightsummary_sleep_cleaned.csv` (for editing)
   - `visualisation_sleep.pdf` (read-only)
   - `visualisation_data.pdf` (read-only)
4. The application retrieves the web links for the two PDF files and displays them as hyperlinks.
5. The application downloads the content of the `PID123_data.csv` file and loads it into the `st.data_editor` widget.
6. The user edits the data in the grid and clicks "Save Changes."
7. The backend checks for existing versions (`_v1`, `_v2`, etc.) within the same folder and creates a new versioned file (e.g., `part4_nightsummary_sleep_cleaned_v1.csv`) in the `ActiGraph/PID123/output_PID123/results/` folder.
8. The UI displays a confirmation message, confirming that the new version has been saved.

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

- For development and version control, the application code shall use placeholder strings (e.g., "YOUR_CLIENT_ID", "PASTE_YOUR_JSON_HERE") for all sensitive credentials. These placeholders will be replaced by the actual secrets managed in the Streamlit Community Cloud environment upon deployment.
- All application secrets (API keys, client IDs) will be managed via Streamlit Community Cloud's Secrets and will not be stored in the code repository.
- User authentication will be handled via the industry-standard OAuth 2.0 protocol.
- The application's Service Account must have "Contributor" (or "Editor") permissions on the target Google Drive folder to allow for the creation of new files.

## 5. Deployment and Maintenance

### 5.1 Deployment

The application will be deployed from its GitHub repository to Streamlit Community Cloud. The deployment process is continuous, meaning any changes pushed to the main branch will automatically trigger a redeployment.

### 5.2 User Management (Rolling Basis)

Managing user access is designed to be simple and require no technical intervention:

- **To Add a User**: An administrator opens the designated "App Access List" Google Sheet and adds the new user's email address.
- **To Remove a User**: An administrator opens the Google Sheet and deletes the row containing the user's email address.

The application is configured to re-fetch this list periodically, so changes will take effect automatically without needing to restart or redeploy the app.
