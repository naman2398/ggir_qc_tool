# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
make setup                    # Create venv and install dependencies

# Testing
make test                     # Run all tests (pytest -v)
make test-cov                 # Tests with coverage (src/ + config/)
venv/bin/pytest tests/test_file_viewer_helpers.py -v  # Single test file
venv/bin/pytest tests/test_api.py::test_function_name -v  # Single test

# Running
make run-mock                 # Launch UI without Azure credentials (dev default)
make run                      # Launch real app (requires .streamlit/secrets.toml)
```

`app_mock.py` stubs all SharePoint API calls — use it for UI development without Azure access.

## Architecture

**Layered Streamlit app:** `app.py` → `src/ui/` → `src/api/` → Microsoft Graph API → SharePoint

| Layer | Files | Responsibility |
|-------|-------|----------------|
| Entry | `app.py`, `app_mock.py` | Auth check, layout, browser unload guard |
| UI | `src/ui/file_viewer.py`, `search_interface.py`, `sidebar.py`, `activity_logging.py` | Rendering, editor state, logging |
| API | `src/api/file_operations.py` | All SharePoint/Graph API calls |
| Auth | `src/auth/msal_auth.py`, `user_auth.py` | Azure token, password validation |
| Config | `config/settings.py`, `config/participants.yaml` | Constants, participant registry |

## Key Design Patterns

### Phase-Namespaced Session State
Actical and Philips Health Band have multiple phases (e.g., Baseline, Overnight). All session state keys for these devices are suffixed: `original_df_Baseline`, `current_df_Baseline`, etc. Non-phased devices use no suffix. The variable `state_suffix = f"_{phase_name}"` appears throughout `file_viewer.py`.

### Row Signatures (`file_viewer.py: _row_signatures()`)
CSVs from different sources may have different column order, types, or NaN representations. Row signatures normalize rows to a stable JSON hash:
- Drop helper columns (`_to_delete`, `_added`, `Unnamed: 0`)
- Sort columns alphabetically
- NaN → `"__GGIR_NULL__"`, numbers → `"__NUM__<value>"`

Used to detect missing rows between the full summary CSV and the edit CSV.

### Two-Root SharePoint Strategy
- **Read source:** `GGIR_final_outputs/` (original, untouched)
- **Write target:** `GGIR_QC_outputs/` (safe edit zone)
- `find_qc_csv()` prefers the QC root, falls back to the final root

### Activity Logging Guard
Before switching participants or logging out, every viewed phase needs a log decision (logged or skipped). Scope token: `f"{participant_id}|{device}|{phase_label}"`. State keys: `log_decision::{scope}`, etc. Guard functions live in `activity_logging.py`.

### Save/Undo Stack
Each save pushes a snapshot (`original_df`, `current_df`, `last_saved`, `last_saved_url`) onto `save_state_history{suffix}`. Undo deletes the last SharePoint file and pops the stack.

## Configuration

**`config/settings.py`** is the single source of truth for:
- `SUPPORTED_DEVICES` — all device types
- `DEVICE_PHASE_MAPPING` — only Actical and Philips Health Band have phases
- `DEVICE_SHAREPOINT_FOLDER` — display name → SharePoint folder name (for devices that differ)
- `TARGET_FILES` — canonical filenames (`part4_nightsummary_sleep_cleaned.csv`, etc.)
- `PATH_TEMPLATE_*` — three path templates depending on device/phase structure
- SharePoint hostname, site path, document library, both root paths

**`config/participants.yaml`** — participant registry loaded at runtime (no restart needed after edits).

## Adding Devices or Participants

**New device:** Add to `SUPPORTED_DEVICES` in `config/settings.py`. Add to `DEVICE_PHASE_MAPPING` if it has phases. Add a folder-name alias to `DEVICE_SHAREPOINT_FOLDER` if SharePoint folder differs from display name.

**New participant:** The SharePoint folder must exist under both roots (`GGIR_final_outputs/{Device}/{PID}/` and `GGIR_QC_outputs/{Device}/{PID}/`). Then add PID to `config/participants.yaml` or use `python refresh_participants.py`.

## Session State Key Reference

Per-phase suffix `{s}` = `""` (single-phase) or `"_{phase_name}"` (multi-phase):

```
original_df{s}           — DataFrame as loaded from SharePoint
current_df{s}            — DataFrame with _to_delete / _added helper columns
data_editor_version{s}   — int bumped to force st.data_editor re-render
qc_df{s}                 — Read-only full summary DataFrame
save_state_history{s}    — list[dict] undo stack
editor_status{s}         — last operation result dict
pending_missing_sigs{s}  — row signatures highlighted yellow in summary grid
```
