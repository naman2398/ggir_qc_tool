# Design Document: Secure Participant File Finder & Editor (Azure / GGIR QC Tool)

Version: 3.4

Date: November 19, 2025

Location: Stony Brook University, New York

Author: Gemini Assistant

Status: Final

## 1\. Overview

This document outlines the design for the **Secure Participant File Finder & Editor (GGIR QC Tool)**, migrated for implementation within the Microsoft Azure and Microsoft 365 ecosystem. The application's purpose is to provide authorized users at Stony Brook University with a simple, secure interface to find and interact with participant files stored in a structured Microsoft OneDrive for Business or SharePoint folder.

The application supports two folder structures:

- **Standard Structure:** &lt;accelerometer&gt;/&lt;participantID&gt;/output_&lt;participantID&gt;/results/
- **Phased Structure:** &lt;accelerometer&gt;/&lt;phase&gt;/&lt;participantID&gt;/output_&lt;participantID&gt;/results/

Users will select one of five specific accelerometer types (and a study phase if applicable) and enter a participant ID. Based on this combination, the application will navigate the hierarchical folder structure to open three specific files: one editable CSV file and two read-only PDF documents.

## 2\. Goals and Objectives

- **Secure Access:** Ensure only pre-approved Microsoft accounts (via Microsoft Entra ID) can use the application.
- **Modular Configuration:** Decouple device names, file paths, and phase mappings into a separate configuration file (config.py) for easier maintenance.
- **UI Flexibility:** Support both Light and Dark modes to accommodate user preference and lighting conditions.
- **Controlled Editing:** Allow users to edit the contents of the participant's primary CSV data file (part4_nightsummary_sleep_cleaned.csv).
- **Data Integrity & Versioning:** Prevent overwriting of original data by saving all edits to the CSV as a new, sequentially versioned file (e.g., \_v1.csv).

## 3\. System Architecture and Design

The architecture leverages Microsoft's cloud components, with backend interactions managed through the **Microsoft Graph API** and configuration separated from logic.

### 3.1 Components

- **Frontend (UI):** A web interface built with Streamlit featuring:
  - **Theme Support:** Automatic or user-toggleable Light/Dark mode.
  - **Sidebar Authentication:** Secure login using Microsoft Authentication Library (MSAL).
  - **Device Dropdown:** Selector for the 5 supported accelerometer types.
  - **Phase Dropdown (Conditional):** Appears only for "Actical" or "Philips Health Band".
  - **Participant Input:** Text input for Participant ID.
  - **File Viewer/Editor:** PDF links and st.data_editor for CSVs.
  - **Save Button:** Triggers the version check and upload process.
- **Backend Logic (app.py):** Handles authentication, Graph API calls, and UI rendering. It imports all constants and pathing logic from config.py.
- **Configuration Module (config.py):** A separate Python file containing:
  - List of supported devices.
  - Phase mappings.
  - File names and target path templates.
  - Environment variable keys.
- **Hosting Platform:** **Microsoft Azure App Service**.
- **Data Sources:**
  - **SharePoint/OneDrive Document Library.**
  - **Access Control List:** App_Access_List.xlsx.

### 3.2 Data Access and Editing Flow

- **Initialization:** app.py loads settings from config.py.
- **Authentication:** User logs in via Microsoft Entra ID.
- **Authorization:** Backend verifies user email against App_Access_List.xlsx.
- **Device Selection:** User selects from the configured list:
  - _Actical, ActiwatchL, Philips Health Band, FitBit, FDG Actical_.
- **Conditional Logic:**
  - If **Actical** is selected: Show dropdown for \[Baseline, Overnight, Pre-Overnight, Post-Overnight\].
  - If **Philips Health Band** is selected: Show dropdown for \[Pre-Scan, Post-Scan, Pre-Overnight, Post-Overnight\].
  - If **ActiwatchL, FitBit,** or **FDG Actical** is selected: No phase dropdown is shown.
- **Participant Entry:** User enters Participant ID.
- **Path Construction:** app.py calls a helper function (imported from config.py or utilizing config constants) to build the path strings based on the selection.
- **Graph API Retrieval:** The app queries the Graph API for the target files.
- **Display & Edit:** PDFs displayed as links; CSV loaded into editor.
- **Saving:** New version uploaded to SharePoint.

### 3.3 Design and Code Philosophy

The project adheres to a strict philosophy of **Simplicity, Minimalism, and Functionality** to ensure long-term maintainability and ease of use.

- **Simple:** The architecture prioritizes straightforward logic over complex abstractions. The code is structured to be easily readable by future maintainers (potentially graduate students or researchers), avoiding unnecessary dependencies or over-engineering.
- **Minimalistic:** The User Interface (UI) shows only what is strictly necessary. Clutter is reduced by using conditional rendering (e.g., the "Phase" dropdown only appears when required). Visual noise is kept to a minimum to allow researchers to focus on the data.
- **Functional:** Every element serves a direct purpose. The focus is entirely on the core workflow-finding a file, viewing it, and saving edits. There are no superfluous animations, purely decorative elements, or features that do not directly support the QC process.

## 4\. Requirements

### 4.1 Functional Requirements

- **Supported Devices:** The system must strictly support only: **Actical, ActiwatchL, Philips Health Band, FitBit, FDG Actical**.
- **UI Theming:** The application must support both Light and Dark themes, adapting to system settings or user choice via the Streamlit settings menu.
- **Configuration:** All hardcoded strings (filenames, device lists, phase lists) must be extracted to config.py.
- **Phase Logic:**
  - **Actical:** Requires Phase selection.
  - **Philips Health Band:** Requires Phase selection.
  - **Others:** Direct Participant ID lookup.
- **Versioning:** \[Original_Name\]\_v\[X\].csv.

### 4.2 Security Requirements

- **Secret Management:** CLIENT_ID, CLIENT_SECRET, TENANT_ID stored in Azure App Service Configuration.
- **Graph Permissions:** Files.ReadWrite.All.

## 5\. Deployment and Maintenance

- **Deployment:** Azure App Service (Linux/Python).
- **Updates:** To add a new device or change a filename, developers modify config.py rather than the main application logic.

## 6\. Technical Implementation Details

### 6.1 Configuration Module (config.py)

This file acts as the single source of truth.

\# config.py  
<br/>\# --- Device Configuration ---  
DEVICE_ACTICAL = "Actical"  
DEVICE_ACTIWATCH = "ActiwatchL"  
DEVICE_PHILIPS = "Philips Health Band"  
DEVICE_FITBIT = "FitBit"  
DEVICE_FDG_ACTICAL = "FDG Actical"  
<br/>SUPPORTED_DEVICES = \[  
DEVICE_ACTICAL,  
DEVICE_ACTIWATCH,  
DEVICE_PHILIPS,  
DEVICE_FITBIT,  
DEVICE_FDG_ACTICAL  
\]  
<br/>\# --- Phase Configuration ---  
\# Only devices listed here will trigger the Phase Dropdown  
DEVICE_PHASE_MAPPING = {  
DEVICE_ACTICAL: \[  
"Baseline", "Overnight", "Pre-Overnight", "Post-Overnight"  
\],  
DEVICE_PHILIPS: \[  
"Pre-Scan", "Post-Scan", "Pre-Overnight", "Post-Overnight"  
\]  
}  
<br/>\# --- File Configuration ---  
TARGET_FILES = {  
"csv": "part4_nightsummary_sleep_cleaned.csv",  
"pdf_sleep": "visualisation_sleep.pdf",  
"pdf_data": "visualisation_data.pdf"  
}  
<br/>\# --- Path Templates ---  
\# Placeholders {device}, {phase}, {pid} will be replaced at runtime  
PATH_TEMPLATE_STANDARD = "{device}/{pid}/output_{pid}/results/"  
PATH_TEMPLATE_PHASED = "{device}/{phase}/{pid}/output_{pid}/results/"  

### 6.2 Main Application Logic (app.py)

The main script imports the config and uses it to drive logic.

import config  
<br/>\# ... UI Setup ...  
selected_device = st.selectbox("Select Device", config.SUPPORTED_DEVICES)  
<br/>\# Conditional Phase Selection  
selected_phase = None  
if selected_device in config.DEVICE_PHASE_MAPPING:  
selected_phase = st.selectbox(  
"Select Study Phase",  
config.DEVICE_PHASE_MAPPING\[selected_device\]  
)  
<br/>\# ... Path Construction ...  
if selected_phase:  
folder_path = config.PATH_TEMPLATE_PHASED.format(  
device=selected_device,  
phase=selected_phase,  
pid=participant_id  
)  
else:  
folder_path = config.PATH_TEMPLATE_STANDARD.format(  
device=selected_device,  
pid=participant_id  
)  

### 6.3 Theme Configuration (.streamlit/config.toml)

To ensure the background flexibility, the project should include a Streamlit configuration file or rely on default behavior.

\[theme\]  
base="light" # Defaults to light, but allows user toggle  
primaryColor="#0078D4" # Microsoft Blue  

## 7\. Future Enhancements

- **Dynamic Config Loading:** Load config.py values from a JSON file stored in SharePoint to allow non-developer updates to file paths.