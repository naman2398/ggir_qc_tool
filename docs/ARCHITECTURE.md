# GGIR QC Tool - Architecture Documentation

## System Architecture

The GGIR QC Tool follows a **modular, layered architecture** designed for maintainability, testability, and scalability.

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit UI Layer                       │
│                      (app_new.py)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   UI Components Layer                        │
│              (src/ui/sidebar.py, etc.)                       │
├─────────────────────────────────────────────────────────────┤
│  - render_sidebar()        : Authentication UI               │
│  - render_search_interface(): Search and selection           │
│  - render_file_viewer()    : File display and editing        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                       │
├──────────────────────┬──────────────────────────────────────┤
│   Authentication     │      API Operations                   │
│   (src/auth/)        │      (src/api/)                       │
├──────────────────────┼──────────────────────────────────────┤
│ - msal_auth.py       │ - file_operations.py                 │
│   · get_msal_app()   │   · build_folder_path()              │
│   · get_access_token()│   · find_file_in_folder()           │
│                      │   · download_csv_content()            │
│ - user_auth.py       │   · upload_versioned_csv()           │
│   · get_authorized() │   · get_next_version_number()        │
│   · check_user()     │                                       │
└──────────────────────┴──────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Configuration Layer                        │
│                  (config/settings.py)                        │
├─────────────────────────────────────────────────────────────┤
│  - Device configurations                                     │
│  - Phase mappings                                            │
│  - File names and paths                                      │
│  - API endpoints                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               External Services Layer                        │
├──────────────────────┬──────────────────────────────────────┤
│  Microsoft Entra ID  │    Microsoft Graph API               │
│  (Azure AD)          │    (SharePoint/OneDrive)             │
├──────────────────────┼──────────────────────────────────────┤
│  - Authentication    │  - File read/write                   │
│  - Token management  │  - Folder navigation                 │
│                      │  - Access control file               │
└──────────────────────┴──────────────────────────────────────┘
```

## Module Breakdown

### 1. **config/** - Configuration Layer
**Purpose**: Centralized configuration management

**Files**:
- `settings.py`: All application constants and settings

**Responsibilities**:
- Device type definitions
- Phase mappings
- File naming conventions
- Path templates
- API endpoints
- Environment variable keys

**Benefits**:
- Single source of truth
- Easy to modify without code changes
- Type-safe constants

---

### 2. **src/auth/** - Authentication Module
**Purpose**: Handle all authentication and authorization

**Files**:
- `msal_auth.py`: Microsoft Entra ID authentication
- `user_auth.py`: User access control

**Responsibilities**:
- MSAL client initialization
- Access token acquisition and caching
- User authorization against Excel allowlist
- Session management

**Key Functions**:
```python
get_msal_app()           # Initialize MSAL client
get_access_token()       # Get Graph API token
get_authorized_users()   # Fetch allowlist
check_user_authorization() # Verify user access
```

---

### 3. **src/api/** - API Integration Module
**Purpose**: Microsoft Graph API interactions

**Files**:
- `file_operations.py`: All file-related operations

**Responsibilities**:
- Folder path construction
- File search and retrieval
- CSV download and upload
- Version number management

**Key Functions**:
```python
build_folder_path()      # Construct file paths
find_file_in_folder()    # Search for files
download_csv_content()   # Download CSV data
upload_versioned_csv()   # Save with versioning
get_next_version_number() # Version tracking
```

---

### 4. **src/ui/** - User Interface Module
**Purpose**: Streamlit UI components

**Files**:
- `sidebar.py`: Authentication sidebar
- `search_interface.py`: Device/participant search
- `file_viewer.py`: File display and editing

**Responsibilities**:
- User input collection
- UI state management
- Component rendering
- User feedback messages

**Component Flow**:
```
sidebar → search_interface → file_viewer
   ↓             ↓                ↓
 auth      find files       edit/save
```

---

### 5. **src/utils/** - Utilities Module
**Purpose**: Shared helper functions (future expansion)

**Potential Functions**:
- Date/time formatting
- Data validation
- Logging utilities
- Error handling helpers

---

### 6. **tests/** - Test Suite
**Purpose**: Automated testing

**Files**:
- `test_config.py`: Configuration tests
- `test_api.py`: API function tests
- `test_auth.py`: Authentication tests (future)
- `test_ui.py`: UI component tests (future)

---

## Data Flow

### 1. **Authentication Flow**
```
User enters email
       ↓
sidebar.py validates input
       ↓
user_auth.check_user_authorization()
       ↓
msal_auth.get_access_token()
       ↓
User authorized / Access token retrieved
```

### 2. **File Search Flow**
```
User selects device + phase + participant ID
       ↓
search_interface.py collects input
       ↓
api.build_folder_path(device, phase, pid)
       ↓
api.find_file_in_folder() for each file
       ↓
Files stored in session state
```

### 3. **File Edit Flow**
```
User views CSV data
       ↓
file_viewer.py displays data_editor
       ↓
User makes changes
       ↓
api.get_next_version_number()
       ↓
api.upload_versioned_csv()
       ↓
New version saved to SharePoint
```

---

## Design Principles

### 1. **Separation of Concerns**
- Each module has a single, clear responsibility
- UI logic separated from business logic
- Configuration isolated from code

### 2. **Dependency Injection**
- Functions accept parameters instead of global state
- Easy to mock for testing
- Flexible configuration sources

### 3. **Stateless Functions**
- Most functions are pure (no side effects)
- State managed through Streamlit session
- Predictable behavior

### 4. **Error Handling**
- Graceful degradation
- User-friendly error messages
- Logging for debugging

### 5. **Caching Strategy**
```python
@st.cache_data(ttl=3600)  # Access token: 1 hour
@st.cache_data(ttl=600)   # User list: 10 minutes
```

---

## Extending the Application

### Adding a New Device Type

**Step 1**: Update configuration
```python
# config/settings.py
DEVICE_NEW = "New Device"
SUPPORTED_DEVICES.append(DEVICE_NEW)

# If phase required:
DEVICE_PHASE_MAPPING[DEVICE_NEW] = ["Phase1", "Phase2"]
```

**Step 2**: No other changes needed! The UI will automatically adapt.

---

### Adding a New API Function

**Step 1**: Add function to `src/api/file_operations.py`
```python
def new_operation(access_token, params):
    """New Graph API operation."""
    # Implementation
    pass
```

**Step 2**: Export in `src/api/__init__.py`
```python
from .file_operations import new_operation
__all__ = [..., 'new_operation']
```

**Step 3**: Use in UI components
```python
from src.api import new_operation
result = new_operation(token, params)
```

---

### Adding a New UI Component

**Step 1**: Create new file `src/ui/new_component.py`
```python
def render_new_component():
    """Render new UI component."""
    st.header("New Feature")
    # Implementation
```

**Step 2**: Export in `src/ui/__init__.py`
```python
from .new_component import render_new_component
__all__ = [..., 'render_new_component']
```

**Step 3**: Use in main app
```python
from src.ui import render_new_component
render_new_component()
```

---

## Security Architecture

### Authentication Chain
```
1. User email input
2. Check against Excel allowlist in SharePoint
3. MSAL client credentials flow
4. Access token with 1-hour TTL
5. Token used for all Graph API calls
```

### Authorization Levels
- **User**: Can view and edit participant files
- **System**: Service principal with Files.ReadWrite.All

### Data Protection
- Original files never modified
- All edits create new versions
- Audit trail via file metadata
- No local data storage

---

## Performance Considerations

### Caching Strategy
- **Access tokens**: 1 hour (matches Azure token lifetime)
- **User list**: 10 minutes (balance security and performance)
- **File content**: Not cached (ensure fresh data)

### Optimization Opportunities
- Implement pagination for large file lists
- Add database for user management
- Use Azure Blob Storage for large files
- Implement client-side caching

---

## Future Architecture Enhancements

### Planned Improvements
1. **Database Integration**: User management and audit logs
2. **Background Jobs**: Batch processing, scheduled tasks
3. **Real-time Collaboration**: Multiple users, live updates
4. **Advanced Analytics**: Data visualization, reporting
5. **Mobile Support**: Responsive design, mobile app
6. **API Layer**: REST API for external integrations

### Scalability Path
```
Current: Monolithic Streamlit app
   ↓
Phase 1: Modular Streamlit app (✅ Done)
   ↓
Phase 2: Backend API + Frontend separation
   ↓
Phase 3: Microservices architecture
   ↓
Phase 4: Cloud-native containerized deployment
```

---

**Last Updated**: November 19, 2025
