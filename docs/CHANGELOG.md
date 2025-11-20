# GGIR QC Tool - Changelog

All notable changes to this project will be documented in this file.

## [3.4.0] - 2025-11-19

### Added
- **Complete Azure/Microsoft 365 Integration**
  - Migrated from Google Drive to Microsoft Graph API
  - Microsoft Entra ID (Azure AD) authentication using MSAL
  - SharePoint/OneDrive file access and management
  
- **Modular Configuration System**
  - Created `config.py` with all device types, phases, and file paths
  - Separated configuration from business logic
  - Easy to update without modifying core application code

- **Enhanced Device Support**
  - Actical (with phase selection)
  - ActiwatchL (standard structure)
  - Philips Health Band (with phase selection)
  - FitBit (standard structure)
  - FDG Actical (standard structure)

- **Conditional Phase Selection**
  - Phase dropdown appears only for Actical and Philips Health Band
  - Dynamic UI based on device selection
  - Supports both standard and phased folder structures

- **Theme Configuration**
  - Light theme with Microsoft color palette
  - Custom `.streamlit/config.toml` for consistent branding
  - Support for both light and dark modes

- **Comprehensive Documentation**
  - `README.md`: Project overview and installation guide
  - `DEPLOYMENT.md`: Complete Azure deployment instructions
  - `QUICKSTART.md`: User and administrator quick reference
  - `design_document.md`: Detailed design specification
  - `.env.example`: Environment variables template
  - `.streamlit/secrets.toml.example`: Secrets configuration template

- **Version Control Files**
  - `.gitignore`: Comprehensive ignore patterns
  - Proper secret management configuration

### Changed
- **Authentication System**
  - Replaced Google OAuth with Microsoft Entra ID
  - Moved from Google Sheets allowlist to Excel file in SharePoint
  - Client credentials flow for service-to-service authentication

- **File Operations**
  - Replaced Google Drive API with Microsoft Graph API
  - Updated all file read/write operations for SharePoint/OneDrive
  - Maintained versioning system with new API

- **Path Construction**
  - Dynamic path building based on device and phase
  - Support for both standard and phased folder structures
  - Configurable root folder path

- **UI/UX Improvements**
  - Cleaner interface following minimalist design philosophy
  - Better status indicators (authorized/unauthorized, saved/unsaved)
  - Improved error messages and user feedback

### Technical Details

**Dependencies Updated:**
- Removed: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`
- Added: `msal`, `msgraph-core`, `azure-identity`, `openpyxl`
- Retained: `streamlit`, `pandas`, `requests`

**API Changes:**
- All Google Drive API calls replaced with Microsoft Graph API endpoints
- Authentication flow changed from OAuth 2.0 to MSAL client credentials
- File access now uses Graph API `/me/drive/` endpoints

**Configuration:**
- Environment variables: `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `ROOT_FOLDER_PATH`, `ACCESS_LIST_FILE`
- Streamlit secrets: `[azure]` section with all credentials
- Config module: Device lists, phase mappings, file names, path templates

**Security Enhancements:**
- Client credentials flow for secure service authentication
- Excel-based access control list
- Proper secret management with Azure App Service Configuration
- No client-side OAuth (more secure for service applications)

### File Structure

```
ggir_qc_tool/
├── .streamlit/
│   ├── config.toml                    # Theme configuration
│   └── secrets.toml.example           # Secrets template
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore patterns
├── app.py                             # Main application (rewritten)
├── app_test.py                        # Test version (kept for reference)
├── config.py                          # Configuration module (new)
├── requirements.txt                   # Updated dependencies
├── design_document.md                 # Design specification
├── README.md                          # Project documentation
├── DEPLOYMENT.md                      # Deployment guide (new)
└── QUICKSTART.md                      # Quick start guide (new)
```

### Design Philosophy

This release adheres to the three core principles:

1. **Simple**: Straightforward logic, easy to read and maintain
2. **Minimalistic**: Clean UI showing only necessary elements
3. **Functional**: Every feature serves a direct purpose

### Breaking Changes

- Complete platform migration (Google Drive → Microsoft Azure)
- Authentication method changed (Google OAuth → Microsoft Entra ID)
- Configuration format updated (requires new secrets setup)
- Device list changed (new supported devices)

### Migration Guide

For users migrating from Google Drive version:

1. Set up Azure App Registration
2. Configure Microsoft Graph API permissions
3. Update environment variables/secrets
4. Migrate access list to Excel format
5. Organize files in SharePoint/OneDrive
6. Test with sample participant before production use

See `DEPLOYMENT.md` for detailed instructions.

### Known Issues

None at release.

### Future Enhancements (Planned)

- [ ] JSON-based dynamic configuration (no code changes needed)
- [ ] Audit log of all file modifications
- [ ] Batch participant processing
- [ ] Advanced search and filtering
- [ ] Export reports to PDF
- [ ] Integration with other research tools
- [ ] Role-based access control (viewer, editor, admin)

---

## Version History

### [3.4.0] - 2025-11-19
Complete rewrite for Microsoft Azure/Microsoft 365 ecosystem

### [Previous Versions]
Earlier versions used Google Drive and are not documented here.

---

**Maintained by**: Development Team at Stony Brook University  
**Last Updated**: November 19, 2025
