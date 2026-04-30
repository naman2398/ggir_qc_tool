"""
GGIR QC Tool Configuration
"""

import os

# Device Configuration
DEVICE_ACTICAL = "Actical"
DEVICE_ACTIWATCH = "ActiwatchL"
DEVICE_PHILIPS = "Philips Health Band"
DEVICE_FITBIT = "FitBit"
DEVICE_FDG_ACTICAL = "FDG Actical"
DEVICE_CENTREPOINT_LEAP = "CentrePointLeap"

SUPPORTED_DEVICES = [
    DEVICE_ACTICAL,
    DEVICE_ACTIWATCH,
    DEVICE_PHILIPS,
    DEVICE_FITBIT,
    DEVICE_FDG_ACTICAL,
    DEVICE_CENTREPOINT_LEAP,
]

# Display-name to SharePoint-folder mapping for devices whose folder names differ.
DEVICE_SHAREPOINT_FOLDER = {
    DEVICE_FDG_ACTICAL: "FDG-Actical",
    DEVICE_FITBIT: "Fitbit",
}

# Phase Configuration (only devices listed here show phase dropdown)
DEVICE_PHASE_MAPPING = {
    DEVICE_ACTICAL: ["Baseline", "Overnight", "Pre-Overnight", "Post-Overnight"],
    DEVICE_PHILIPS: ["Pre-Scan", "Post-Scan", "Pre-Overnight", "Post-Overnight"]
}

# Target Files
TARGET_FILES = {
    "csv": "part4_nightsummary_sleep_cleaned.csv",
    "csv_full": "part4_nightsummary_sleep_full.csv",
    "csv_full_subfolder": "QC/",
    "pdf_sleep": "visualisation_sleep.pdf",
    "pdf_data": "file summary reports/"
}

SUMMARY_REPORT_SUBFOLDER = TARGET_FILES["pdf_data"]

# Path Templates
PATH_TEMPLATE_STANDARD = "{device}/{pid}/output_{pid}/results/"
PATH_TEMPLATE_PHASED = "{device}/{phase}/{pid}/output_{pid}/results/"
PATH_TEMPLATE_PARTICIPANT_PHASED = "{device}/{pid}/output_{pid}_{phase}/results/"

# Participant Registry
PARTICIPANTS_FILE = "config/participants.yaml"

# SharePoint Configuration
SHAREPOINT_HOSTNAME = "stonybrookmedicine.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/CUBIT"
DOCUMENT_LIBRARY = "CBT-I Documents"
ROOT_FOLDER_PATH = "Actigraphy Analysis (Multi-Study Data Sets)/GGIR_final_outputs"
QC_ROOT_FOLDER_PATH = "Actigraphy Analysis (Multi-Study Data Sets)/GGIR_QC_outputs"
ACCESS_LIST_FILE = "App_Access_List.xlsx"

# Activity logging file configuration
ACTIVITY_LOG_FILE = "user_comments.csv"
ACTIVITY_LOG_HEADERS = [
    "User_email",
    "Monitor",
    "Participant_ID",
    "Study_Phase",
    "QC_Outcome",
    "Comments",
    "timestamp_QC'ed",
]

# Microsoft Graph API
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]

# PDF proxy configuration (used to serve PDFs without SharePoint login)
PDF_PROXY_BASE_URL = os.getenv("PDF_PROXY_BASE_URL", "http://localhost:8502")
PDF_PROXY_CACHE_ENABLED = os.getenv("PDF_PROXY_CACHE_ENABLED", "false").lower() in ("1", "true", "yes")
PDF_PROXY_CACHE_DIR = os.getenv("PDF_PROXY_CACHE_DIR", ".pdf_cache")
