# GGIR QC Tool - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI (app.py)                    │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                   UI Components (src/ui/)                    │
│  sidebar.py │ search_interface.py │ file_viewer.py          │
└─────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────┬──────────────────────────────────────┐
│   Auth (src/auth/)   │      API (src/api/)                  │
│  msal_auth.py        │  file_operations.py                  │
│  user_auth.py        │                                      │
└──────────────────────┴──────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                 Configuration (config/settings.py)           │
└─────────────────────────────────────────────────────────────┘
                            │
┌──────────────────────┬──────────────────────────────────────┐
│  Microsoft Entra ID  │    Microsoft Graph API (SharePoint)  │
└──────────────────────┴──────────────────────────────────────┘
```

## Modules

### config/settings.py
Device types, phase mappings, SharePoint paths, API endpoints.

### src/auth/
- `msal_auth.py`: Azure token acquisition (`get_access_token()`)
- `user_auth.py`: User authorization (`check_user_authorization()`)

### src/api/file_operations.py
- `get_drive_id()`: Get SharePoint drive ID
- `build_folder_path()`: Construct file paths
- `find_file()`: Search for files
- `download_csv()`: Download CSV data
- `upload_csv()`: Save versioned CSV

### src/ui/
- `sidebar.py`: Login UI (`render_sidebar()`)
- `search_interface.py`: Device/participant search (`render_search_interface()`)
- `file_viewer.py`: CSV editor (`render_file_viewer()`)

## Data Flow

1. **Login**: User email → `check_user_authorization()` → Access token
2. **Search**: Device + Phase + PID → `build_folder_path()` → `find_file()`
3. **Edit**: Load CSV → Edit in UI → `upload_csv()` → New versioned file

## Adding a New Device

Edit `config/settings.py`:
```python
SUPPORTED_DEVICES.append("New Device")
# If phases needed:
DEVICE_PHASE_MAPPING["New Device"] = ["Phase1", "Phase2"]
```

No other changes required.
