"""
GGIR QC Tool Configuration
"""

# Device Configuration
DEVICE_ACTICAL = "Actical"
DEVICE_ACTIWATCH = "ActiwatchL"
DEVICE_PHILIPS = "Philips Health Band"
DEVICE_FITBIT = "FitBit"
DEVICE_FDG_ACTICAL = "FDG Actical"

SUPPORTED_DEVICES = [
    DEVICE_ACTICAL,
    DEVICE_ACTIWATCH,
    DEVICE_PHILIPS,
    DEVICE_FITBIT,
    DEVICE_FDG_ACTICAL
]

# Phase Configuration (only devices listed here show phase dropdown)
DEVICE_PHASE_MAPPING = {
    DEVICE_ACTICAL: ["Baseline", "Overnight", "Pre-Overnight", "Post-Overnight"],
    DEVICE_PHILIPS: ["Pre-Scan", "Post-Scan", "Pre-Overnight", "Post-Overnight"]
}

# Target Files
TARGET_FILES = {
    "csv": "part4_nightsummary_sleep_cleaned.csv",
    "pdf_sleep": "visualisation_sleep.pdf",
    "pdf_data": "visualisation_data.pdf"
}

# Path Templates
PATH_TEMPLATE_STANDARD = "{device}/{pid}/output_{pid}/results/"
PATH_TEMPLATE_PHASED = "{device}/{phase}/{pid}/output_{pid}/results/"

# SharePoint Configuration
SHAREPOINT_HOSTNAME = "stonybrookmedicine.sharepoint.com"
SHAREPOINT_SITE_PATH = "/sites/CUBIT"
DOCUMENT_LIBRARY = "CBT-I Documents"
ROOT_FOLDER_PATH = "Actigraphy Analysis (Multi-Study Data Sets)/GGIR_final_outputs"
ACCESS_LIST_FILE = "App_Access_List.xlsx"

# Microsoft Graph API
GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]
