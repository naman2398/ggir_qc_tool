# GGIR QC Tool

**Secure Participant File Finder & Editor**

Stony Brook University | Version 3.5

## Overview

Streamlit application for viewing and editing GGIR accelerometer data files stored in Microsoft SharePoint.

## Quick Start

```bash
git clone https://github.com/naman2398/ggir_qc_tool.git
cd ggir_qc_tool
pip install -r requirements.txt
streamlit run app.py
```

Configure `.streamlit/secrets.toml`:
```toml
[azure]
client_id = "your-client-id"
client_secret = "your-client-secret"
tenant_id = "your-tenant-id"
```

## Project Structure

```
ggir_qc_tool/
├── app.py                    # Main application
├── config/
│   └── settings.py           # Device configs, SharePoint paths
├── src/
│   ├── auth/                 # Authentication (MSAL, user auth)
│   ├── api/                  # SharePoint file operations
│   └── ui/                   # Streamlit UI components
├── tests/                    # Unit tests
├── docs/                     # Documentation
└── legacy/                   # Archived old code
```

## Features

- **5 Device Types**: Actical, ActiwatchL, Philips Health Band, FitBit, FDG Actical
- **Conditional Phases**: Actical and Philips Health Band require phase selection
- **Version Control**: Edits saved as new versioned files (original preserved)
- **Access Control**: Excel-based user authorization

## Documentation

- [Quick Start](docs/QUICKSTART.md) — User guide and admin setup
- [Deployment](docs/DEPLOYMENT.md) — Azure deployment instructions
- [Architecture](docs/ARCHITECTURE.md) — System design overview
- [Changelog](docs/CHANGELOG.md) — Version history
- [Design Document](docs/design_document.md) — Original specification

## Adding a New Participant

Before a participant can appear in the app's dropdown, their data folder must exist in **both** SharePoint roots under the correct device:

```
GGIR_final_outputs/{Device}/{PID}/
GGIR_QC_outputs/{Device}/{PID}/
```

### Option A — In-app (for non-technical users)

1. Open the app and select the correct **Device Type**.
2. Click the **"➕ Add new participant to list"** expander below the search form.
3. Type the Participant ID and click **Add to list**.
   - The app checks SharePoint automatically. If the folder is missing in either root, an error is shown.
   - On success, the ID is saved to `config/participants.yaml` and appears in the dropdown immediately.

### Option B — Edit the YAML directly (for developers)

Open `config/participants.yaml` and add the participant ID under the correct device:

```yaml
ActiwatchL:
  - "PID123"
  - "NEW_PID"   # ← add here
```

The app picks up the change on the next interaction (no restart required).
Ensure the two SharePoint folders exist before doing this — the app will search them when the user clicks **Search Files**.

### Option C — Refresh script (for developers, after bulk folder creation)

After creating multiple participant folders in SharePoint (e.g., via `mirror_qc_folder_structure.py`), re-run the refresh script to update the registry automatically:

```bash
python refresh_participants.py           # merge new participants in
python refresh_participants.py --dry-run # preview without writing
python refresh_participants.py --device "Actical"  # one device only
python refresh_participants.py --fresh   # overwrite YAML completely
```

The script only adds a PID if its folder is present in **both** roots. PIDs found in only one root are printed as warnings.

## Adding a New Device

Edit `config/settings.py`:
```python
SUPPORTED_DEVICES.append("New Device")
DEVICE_PHASE_MAPPING["New Device"] = ["Phase1", "Phase2"]  # if phases needed
```

## License

Proprietary — Stony Brook University
