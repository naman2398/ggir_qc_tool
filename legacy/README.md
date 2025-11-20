# Legacy Code Archive

This folder contains archived code and documentation from previous versions of the GGIR QC Tool.

## Contents

### `app_monolithic.py`
**Original monolithic application** (565 lines)

- Single-file implementation with all functionality
- Used Google Drive API (pre-Azure migration)
- Kept for reference and rollback purposes
- **Do not use in production**

**Historical Context:**
- Written before modularization
- Mixed authentication, API, and UI code
- Harder to maintain and test

**Why Archived:**
- Replaced by modular architecture in `src/`
- Better separation of concerns in new version
- Improved testability and maintainability

---

### `app_test_google_drive.py`
**Mock testing version for Google Drive**

- Used for UI testing with simulated Google Drive responses
- Contains hardcoded Google Drive file links
- No longer relevant after Azure migration
- **Obsolete - do not use**

**Why Archived:**
- Application migrated to Microsoft Graph API
- Test files now in `tests/` directory
- Google Drive integration removed

---

### `design_doc_azure_env.docx`
**Original design document** (Word format)

- Pre-migration design specifications
- Superseded by `docs/design_document.md`
- Kept for historical reference

---

## Migration History

### Version 3.4.0 (November 2025)
- ✅ Migrated from Google Drive to Microsoft Azure
- ✅ Refactored monolithic code to modular architecture
- ✅ Separated concerns into auth/, api/, ui/ modules
- ✅ Created comprehensive test suite
- ✅ Improved documentation

### Why We Moved to Modular Architecture

**Before (Monolithic):**
```
app.py (565 lines)
├── Configuration
├── Authentication
├── Google Drive API
├── UI Components
└── Main Logic
```

**After (Modular):**
```
app.py (45 lines - orchestration only)
├── config/ - Configuration
├── src/auth/ - Authentication
├── src/api/ - Microsoft Graph API
├── src/ui/ - UI Components
└── tests/ - Test Suite
```

---

## Should You Use These Files?

### ❌ No - Use Current Version

**Use instead:**
- `app.py` - Current modular application
- `src/` - Organized source code
- `tests/` - Test suite
- `docs/` - Current documentation

### 📚 Reference Only

These files are kept for:
- Historical reference
- Understanding evolution of the codebase
- Emergency rollback (if needed)
- Learning from past implementations

---

## Rollback Procedure (Emergency Only)

If you need to rollback to the monolithic version:

```bash
# 1. Backup current version
mv app.py app_modular_backup.py
mv src/ src_backup/

# 2. Restore legacy version
cp legacy/app_monolithic.py app.py

# 3. Note: This will revert to Google Drive!
# You'll need to reconfigure for Google Drive API
```

**⚠️ Warning:** The monolithic version uses Google Drive, not Azure. You'll need to:
- Reconfigure Google Drive credentials
- Update secrets.toml
- Restore Google Drive API dependencies

---

## Code Comparison

| Aspect | Legacy (Monolithic) | Current (Modular) |
|--------|---------------------|-------------------|
| **Architecture** | Single file | Multiple modules |
| **Lines of code** | 565 lines | ~530 total (better organized) |
| **Cloud provider** | Google Drive | Microsoft Azure |
| **Testability** | Poor | Excellent |
| **Maintainability** | Difficult | Easy |
| **Documentation** | Inline only | Comprehensive docs |
| **File organization** | Single file | 11+ focused modules |

---

## Best Practices Learned

From maintaining the legacy code, we learned:

1. **Separation of Concerns**: Mix auth, API, and UI in separate modules
2. **Configuration Management**: Centralize config in dedicated module
3. **Testability**: Write testable, isolated functions
4. **Documentation**: Maintain comprehensive docs separate from code
5. **Modularity**: Keep files focused and small

These lessons informed the current modular architecture.

---

## Questions?

If you need to reference the legacy code:
- See `docs/REORGANIZATION.md` for detailed comparison
- See `docs/ARCHITECTURE.md` for current design
- Contact the development team for migration questions

---

**Last Updated**: November 19, 2025  
**Status**: Archived - Reference Only  
**Current Version**: 3.4.0 (Modular)
