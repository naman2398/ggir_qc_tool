"""
Configuration Module for GGIR QC Tool

This module contains all configuration constants including device types,
phase mappings, file names, and path templates.
"""

# ============================================================================
# DEVICE CONFIGURATION
# ============================================================================

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

# ============================================================================
# PHASE CONFIGURATION
# ============================================================================

# Only devices listed here will trigger the Phase Dropdown
DEVICE_PHASE_MAPPING = {
    DEVICE_ACTICAL: [
        "Baseline",
        "Overnight",
        "Pre-Overnight",
        "Post-Overnight"
    ],
    DEVICE_PHILIPS: [
        "Pre-Scan",
        "Post-Scan",
        "Pre-Overnight",
        "Post-Overnight"
    ]
}

# ============================================================================
# FILE CONFIGURATION
# ============================================================================

TARGET_FILES = {
    "csv": "part4_nightsummary_sleep_cleaned.csv",
    "pdf_sleep": "visualisation_sleep.pdf",
    "pdf_data": "visualisation_data.pdf"
}

# ============================================================================
# PATH TEMPLATES
# ============================================================================

# Placeholders {device}, {phase}, {pid} will be replaced at runtime
PATH_TEMPLATE_STANDARD = "{device}/{pid}/output_{pid}/results/"
PATH_TEMPLATE_PHASED = "{device}/{phase}/{pid}/output_{pid}/results/"

# ============================================================================
# ENVIRONMENT VARIABLE KEYS
# ============================================================================

ENV_CLIENT_ID = "CLIENT_ID"
ENV_CLIENT_SECRET = "CLIENT_SECRET"
ENV_TENANT_ID = "TENANT_ID"
ENV_ROOT_FOLDER_PATH = "ROOT_FOLDER_PATH"
ENV_ACCESS_LIST_FILE = "ACCESS_LIST_FILE"

# ============================================================================
# MICROSOFT GRAPH API CONFIGURATION
# ============================================================================

GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
SCOPES = ["https://graph.microsoft.com/.default"]

# Required Graph API permissions
REQUIRED_PERMISSIONS = [
    "Files.ReadWrite.All"
]
