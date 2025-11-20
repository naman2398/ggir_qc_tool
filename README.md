# GGIR QC Tool

**Secure Participant File Finder & Editor**

Version: 3.4.0  
Institution: Stony Brook University, New York

## Quick Links

- [🚀 Quick Start Guide](docs/QUICKSTART.md)
- [☁️ Deployment Guide](docs/DEPLOYMENT.md)
- [🏗️ Architecture Guide](docs/ARCHITECTURE.md)
- [🗂️ Project Structure](docs/PROJECT_STRUCTURE.md)
- [📝 Changelog](docs/CHANGELOG.md)
- [📋 Design Document](docs/design_document.md)
- [🗂️ Legacy Code](legacy/README.md)

## Overview

The GGIR QC Tool is a secure Streamlit application for managing and editing GGIR accelerometer data files stored in Microsoft OneDrive/SharePoint.

## Project Structure

```
ggir_qc_tool/
├── app.py                        # Main application (modular version) ⭐
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore patterns
│
├── config/                       # Configuration
│   ├── __init__.py
│   └── settings.py               # Application settings and constants
│
├── src/                          # Source code
│   ├── __init__.py
│   ├── auth/                     # Authentication module
│   │   ├── __init__.py
│   │   ├── msal_auth.py         # Microsoft Entra ID authentication
│   │   └── user_auth.py         # User authorization
│   │
│   ├── api/                      # Microsoft Graph API integration
│   │   ├── __init__.py
│   │   └── file_operations.py   # File access and manipulation
│   │
│   ├── ui/                       # User interface components
│   │   ├── __init__.py
│   │   ├── sidebar.py           # Authentication sidebar
│   │   ├── search_interface.py  # Search UI
│   │   └── file_viewer.py       # File viewer and editor
│   │
│   └── utils/                    # Utility functions
│       └── __init__.py
│
├── docs/                         # Documentation
│   ├── QUICKSTART.md            # Quick start guide
│   ├── DEPLOYMENT.md            # Deployment instructions
│   ├── ARCHITECTURE.md          # Architecture guide
│   ├── PROJECT_STRUCTURE.md     # Detailed structure guide
│   ├── CHANGELOG.md             # Version history
│   └── design_document.md       # Design specification
│
├── tests/                        # Test files
│   ├── __init__.py
│   ├── test_config.py           # Configuration tests
│   └── test_api.py              # API tests
│
├── legacy/                       # Archived legacy code
│   ├── README.md                # Legacy documentation
│   ├── app_monolithic.py        # Original single-file app
│   └── app_test_google_drive.py # Old Google Drive test
│
└── .streamlit/                   # Streamlit configuration
    ├── config.toml              # Theme configuration
    └── secrets.toml.example     # Secrets template
```

## Key Features

- **Modular Architecture**: Clean separation of concerns (auth, API, UI, config)
- **Secure Authentication**: Microsoft Entra ID integration
- **5 Device Types**: Actical, ActiwatchL, Philips Health Band, FitBit, FDG Actical
- **Conditional Phase Selection**: Dynamic UI based on device type
- **Data Versioning**: Automatic file versioning on save
- **Access Control**: Excel-based user authorization

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/naman2398/ggir_qc_tool.git
cd ggir_qc_tool

# Install dependencies
pip install -r requirements.txt

# Configure secrets (copy and edit)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Run application
streamlit run app.py
```

### Configuration

Create `.streamlit/secrets.toml`:

```toml
[azure]
client_id = "your-azure-client-id"
client_secret = "your-azure-client-secret"
tenant_id = "your-azure-tenant-id"
root_folder_path = "path/to/sharepoint/folder"
access_list_file = "App_Access_List.xlsx"
```

## Architecture Benefits

### Modular Design
- **auth/**: Handles all authentication logic (MSAL + user authorization)
- **api/**: Manages Microsoft Graph API interactions
- **ui/**: Contains reusable UI components
- **config/**: Centralized configuration management

### Maintainability
- Each module has a single responsibility
- Easy to test individual components
- Simple to add new features
- Clear code organization

### Scalability
- Add new devices by editing `config/settings.py`
- Add new UI components in `src/ui/`
- Extend API functionality in `src/api/`
- No need to modify core application logic

## Development

### Adding New Devices

Edit `config/settings.py`:

```python
SUPPORTED_DEVICES = [
    DEVICE_ACTICAL,
    DEVICE_ACTIWATCH,
    "New Device Name"  # Add here
]
```

### Adding New Features

1. **New API Function**: Add to `src/api/file_operations.py`
2. **New UI Component**: Create in `src/ui/new_component.py`
3. **New Auth Method**: Add to `src/auth/`
4. **New Config**: Update `config/settings.py`

### Testing

```bash
# Run tests (to be implemented)
pytest tests/

# Run with test data
streamlit run app_test.py
```

## Legacy Code

Previous versions of the application are archived in the `legacy/` folder:
- `app_monolithic.py`: Original single-file version (Google Drive)
- `app_test_google_drive.py`: Old test version
- See `legacy/README.md` for details

**Note:** The current application uses a modular architecture and Microsoft Azure. Legacy files are for reference only.

## Documentation

Comprehensive documentation is available in the `docs/` folder:

- **[QUICKSTART.md](docs/QUICKSTART.md)**: Quick reference for users and admins
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Azure deployment instructions
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System architecture guide
- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)**: Detailed structure reference
- **[CHANGELOG.md](docs/CHANGELOG.md)**: Version history
- **[design_document.md](docs/design_document.md)**: Design specifications

## Support

For issues or questions:
- Check documentation in `docs/`
- Review configuration in `config/settings.py`
- Contact Stony Brook University IT Support

## License

Proprietary software developed for Stony Brook University.

---

**Last Updated**: November 19, 2025
