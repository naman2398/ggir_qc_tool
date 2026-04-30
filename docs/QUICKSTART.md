# GGIR QC Tool - Quick Start

## For Users

### Login
1. Open the application URL
2. Enter your Stony Brook email in the sidebar
3. If authorized, you'll see ✅ Authorized

### Find Files
1. Select **Device Type** (Actical, ActiwatchL, Philips Health Band, FitBit, FDG Actical)
2. Enter **Participant ID**
3. Click **🔎 Search Files**

### View & Edit
- **PDFs**: Click links to open reports (read-only)
- **CSV**: Edit data directly in the table
- **Save**: Click **💾 Save Changes** to create a new versioned file

> **Note**: Each save creates a new versioned file named like `{base}_{username}_{YYYYMMDD_HHMMSS}.{ext}`. Original files are never modified.

---

## For Administrators

### Setup
```bash
git clone https://github.com/naman2398/ggir_qc_tool.git
cd ggir_qc_tool
pip install -r requirements.txt
```

### Configure Secrets
Create `.streamlit/secrets.toml`:
```toml
[azure]
client_id = "your-client-id"
client_secret = "your-client-secret"
tenant_id = "your-tenant-id"
```

### Run
```bash
streamlit run app.py
```

For PDF viewing without SharePoint login, run the proxy in a second terminal:
```bash
make run-proxy
```

If the proxy runs on a different host or port, set:
```bash
export PDF_PROXY_BASE_URL="http://localhost:8502"
```

### Add Users
Add email addresses to `App_Access_List.xlsx` in SharePoint (column A with header "email").

### Add Devices
Edit `config/settings.py`:
```python
SUPPORTED_DEVICES.append("New Device")
DEVICE_PHASE_MAPPING["New Device"] = ["Phase1", "Phase2"]  # if phases needed
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't login | Check email is in `App_Access_List.xlsx` |
| Files not found | Verify folder structure: `device/[phase]/pid/output_pid/results/` |
| Can't save | Check Azure permissions include `Sites.ReadWrite.All` |
