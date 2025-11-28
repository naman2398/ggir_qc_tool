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

## Adding a New Device

Edit `config/settings.py`:
```python
SUPPORTED_DEVICES.append("New Device")
DEVICE_PHASE_MAPPING["New Device"] = ["Phase1", "Phase2"]  # if phases needed
```

## License

Proprietary — Stony Brook University
