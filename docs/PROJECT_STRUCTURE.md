# GGIR QC Tool - Project Structure Guide

## Complete Directory Structure

```
ggir_qc_tool/
│
├── 📄 README.md                      # Project overview and quick start
├── 📄 requirements.txt               # Python dependencies
├── 📄 .gitignore                     # Git ignore patterns
├── 📄 .env.example                   # Environment variables template
│
├── 🚀 app_new.py                     # Main application (modular version) ⭐
├── 📝 app.py                         # Main application (legacy monolithic)
├── 🧪 app_test.py                    # Test/mock version
│
├── 📁 config/                        # ⚙️ Configuration Module
│   ├── __init__.py                   # Package initialization
│   └── settings.py                   # Application settings & constants
│       ├── Device configurations
│       ├── Phase mappings
│       ├── File names
│       ├── Path templates
│       └── API endpoints
│
├── 📁 src/                           # 💻 Source Code
│   ├── __init__.py                   # Package initialization
│   │
│   ├── 📁 auth/                      # 🔐 Authentication Module
│   │   ├── __init__.py
│   │   ├── msal_auth.py             # Microsoft Entra ID authentication
│   │   │   ├── get_msal_app()
│   │   │   └── get_access_token()
│   │   └── user_auth.py             # User authorization
│   │       ├── get_authorized_users()
│   │       └── check_user_authorization()
│   │
│   ├── 📁 api/                       # 🌐 API Integration Module
│   │   ├── __init__.py
│   │   └── file_operations.py       # Microsoft Graph API operations
│   │       ├── build_folder_path()
│   │       ├── find_file_in_folder()
│   │       ├── download_csv_content()
│   │       ├── upload_versioned_csv()
│   │       └── get_next_version_number()
│   │
│   ├── 📁 ui/                        # 🎨 User Interface Module
│   │   ├── __init__.py
│   │   ├── sidebar.py               # Authentication sidebar
│   │   │   └── render_sidebar()
│   │   ├── search_interface.py      # Search and selection UI
│   │   │   └── render_search_interface()
│   │   └── file_viewer.py           # File display and editor
│   │       └── render_file_viewer()
│   │
│   └── 📁 utils/                     # 🛠️ Utilities Module
│       └── __init__.py               # Helper functions (future)
│
├── 📁 docs/                          # 📚 Documentation
│   ├── README.md                     # Complete documentation
│   ├── QUICKSTART.md                 # Quick start guide
│   ├── DEPLOYMENT.md                 # Azure deployment guide
│   ├── CHANGELOG.md                  # Version history
│   ├── ARCHITECTURE.md               # Architecture documentation
│   └── design_document.md            # Original design specification
│
├── 📁 tests/                         # 🧪 Test Suite
│   ├── __init__.py
│   ├── test_config.py               # Configuration tests
│   ├── test_api.py                  # API function tests
│   ├── test_auth.py                 # Authentication tests (future)
│   └── test_ui.py                   # UI component tests (future)
│
└── 📁 .streamlit/                    # ⚙️ Streamlit Configuration
    ├── config.toml                   # Theme and app settings
    └── secrets.toml.example          # Secrets template (DO NOT COMMIT ACTUAL)
```

---

## Module Responsibilities

### 🚀 Entry Points

| File | Purpose | When to Use |
|------|---------|-------------|
| `app_new.py` | **Modular main app** | ✅ **Recommended** - Production use |
| `app.py` | Legacy monolithic app | 📦 Reference/backup only |
| `app_test.py` | Mock testing version | 🧪 UI testing without API |

---

### ⚙️ Configuration Layer (`config/`)

**Purpose**: Centralized application settings

| File | Contains | Modify When |
|------|----------|-------------|
| `settings.py` | All constants & configs | Adding devices, changing paths, updating API endpoints |

**Key Constants**:
- ✅ `SUPPORTED_DEVICES` - List of accelerometer types
- ✅ `DEVICE_PHASE_MAPPING` - Phase options per device
- ✅ `TARGET_FILES` - File names to search for
- ✅ `PATH_TEMPLATE_*` - Folder path structures
- ✅ `GRAPH_API_ENDPOINT` - Microsoft Graph URL

---

### 💻 Source Code (`src/`)

#### 🔐 Authentication (`src/auth/`)

**Purpose**: Handle all authentication and authorization

| File | Functions | Purpose |
|------|-----------|---------|
| `msal_auth.py` | `get_msal_app()`<br>`get_access_token()` | Azure AD auth<br>Token management |
| `user_auth.py` | `get_authorized_users()`<br>`check_user_authorization()` | Fetch allowlist<br>Verify access |

**Flow**: User email → Check allowlist → Get token → Access granted

---

#### 🌐 API Integration (`src/api/`)

**Purpose**: Microsoft Graph API operations

| File | Functions | Purpose |
|------|-----------|---------|
| `file_operations.py` | `build_folder_path()` | Construct paths |
| | `find_file_in_folder()` | Search files |
| | `download_csv_content()` | Download data |
| | `upload_versioned_csv()` | Save with versions |
| | `get_next_version_number()` | Version tracking |

**Flow**: Search → Find → Download → Edit → Upload versioned

---

#### 🎨 User Interface (`src/ui/`)

**Purpose**: Streamlit UI components

| File | Function | Renders |
|------|----------|---------|
| `sidebar.py` | `render_sidebar()` | Login & about info |
| `search_interface.py` | `render_search_interface()` | Device/phase/PID search |
| `file_viewer.py` | `render_file_viewer()` | PDF links & CSV editor |

**Flow**: Sidebar auth → Search → View/Edit files

---

#### 🛠️ Utilities (`src/utils/`)

**Purpose**: Shared helper functions (future expansion)

Currently empty - placeholder for:
- Date/time formatting
- Data validation utilities
- Custom logging
- Error handling helpers

---

### 📚 Documentation (`docs/`)

| File | Audience | Content |
|------|----------|---------|
| `README.md` | Everyone | Complete project docs |
| `QUICKSTART.md` | Users & Admins | Quick reference guide |
| `DEPLOYMENT.md` | Admins | Azure setup instructions |
| `ARCHITECTURE.md` | Developers | System design |
| `CHANGELOG.md` | Everyone | Version history |
| `design_document.md` | Developers | Original specs |

---

### 🧪 Tests (`tests/`)

**Purpose**: Automated testing

| File | Tests | Run With |
|------|-------|----------|
| `test_config.py` | Configuration validity | `pytest tests/test_config.py` |
| `test_api.py` | API functions | `pytest tests/test_api.py` |
| `test_auth.py` | Auth logic (future) | `pytest tests/test_auth.py` |
| `test_ui.py` | UI components (future) | `pytest tests/test_ui.py` |

**Run all tests**: `pytest tests/ -v --cov=src`

---

### ⚙️ Streamlit Config (`.streamlit/`)

| File | Purpose | Notes |
|------|---------|-------|
| `config.toml` | Theme & app settings | ✅ Commit to git |
| `secrets.toml` | Azure credentials | ❌ **DO NOT COMMIT** |
| `secrets.toml.example` | Secrets template | ✅ Commit as example |

---

## File Count Summary

```
Total Files: ~30

By Type:
├── Python source: 15 files
├── Documentation: 6 files
├── Tests: 4 files
├── Config: 3 files
└── Other: 2 files

By Purpose:
├── Core application: 3 files (app*.py)
├── Modular source: 11 files (src/*)
├── Configuration: 2 files (config/*)
├── Tests: 4 files (tests/*)
├── Documentation: 6 files (docs/*)
└── Project setup: 4 files
```

---

## Import Patterns

### ✅ Recommended Imports

```python
# In app_new.py
from src.ui import render_sidebar, render_search_interface, render_file_viewer

# In UI components
from src.auth import get_access_token, check_user_authorization
from src.api import build_folder_path, find_file_in_folder
from config.settings import config

# In tests
from config.settings import config
from src.api import build_folder_path
```

### ❌ Avoid

```python
# Don't import from specific files
from src.auth.msal_auth import get_access_token  # ❌

# Use package-level imports instead
from src.auth import get_access_token  # ✅
```

---

## Code Organization Benefits

### 1. **Clear Separation of Concerns**
- UI code in `src/ui/`
- Business logic in `src/auth/` and `src/api/`
- Configuration in `config/`
- Tests in `tests/`

### 2. **Easy to Navigate**
- Find auth code: look in `src/auth/`
- Find UI code: look in `src/ui/`
- Find configs: look in `config/`
- Find docs: look in `docs/`

### 3. **Testability**
- Each module can be tested independently
- Mock dependencies easily
- Clear test organization

### 4. **Maintainability**
- Small, focused files
- Single responsibility per module
- Clear dependencies

### 5. **Scalability**
- Easy to add new modules
- No circular dependencies
- Clear extension points

---

## Quick Reference

### Adding a New Feature

1. **Configuration change?** → Edit `config/settings.py`
2. **New API operation?** → Add to `src/api/file_operations.py`
3. **New UI component?** → Create in `src/ui/new_component.py`
4. **New auth method?** → Add to `src/auth/`
5. **Write tests** → Add to `tests/test_*.py`
6. **Document** → Update `docs/`

### Finding Code

- **"Where is authentication?"** → `src/auth/`
- **"Where is file download?"** → `src/api/file_operations.py`
- **"Where is the CSV editor?"** → `src/ui/file_viewer.py`
- **"Where are device names?"** → `config/settings.py`
- **"How do I deploy?"** → `docs/DEPLOYMENT.md`

---

**Last Updated**: November 19, 2025
