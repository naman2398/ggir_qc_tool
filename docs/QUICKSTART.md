# GGIR QC Tool - Quick Start Guide

## For End Users

### Accessing the Application

1. Open your web browser and navigate to the application URL provided by your administrator
2. Enter your Stony Brook University email address in the login sidebar
3. If authorized, you'll see a success message

### Using the Tool

#### Step 1: Select Device Type
Choose your accelerometer device from the dropdown:
- Actical
- ActiwatchL
- Philips Health Band
- FitBit
- FDG Actical

#### Step 2: Select Phase (if applicable)
If you selected **Actical** or **Philips Health Band**, a second dropdown will appear:

**For Actical:**
- Baseline
- Overnight
- Pre-Overnight
- Post-Overnight

**For Philips Health Band:**
- Pre-Scan
- Post-Scan
- Pre-Overnight
- Post-Overnight

#### Step 3: Enter Participant ID
Type the participant identifier (e.g., PID123, SUBJ001)

#### Step 4: Search for Files
Click the "🔎 Search Files" button

### Working with Files

Once files are found, you'll see:

#### PDF Reports (Read-Only)
- **visualisation_sleep.pdf**: Sleep analysis visualization
- **visualisation_data.pdf**: Data quality visualization
- Click the links to open PDFs in a new tab

#### CSV Data File (Editable)
- **part4_nightsummary_sleep_cleaned.csv**: Editable sleep summary data
- You can:
  - Edit cell values
  - Add new rows
  - Delete rows
  - Sort columns

### Saving Changes

1. Make your edits to the CSV data
2. You'll see "⚠️ Unsaved changes" indicator
3. Click "💾 Save Changes" button
4. A new versioned file will be created (e.g., `part4_nightsummary_sleep_cleaned_v1.csv`)
5. The original file remains unchanged

**Important**: Each save creates a new version. You cannot overwrite existing files.

## For Administrators

### Quick Setup

1. **Prerequisites**
   - Azure subscription
   - Access to SharePoint/OneDrive
   - Python 3.9+

2. **Clone Repository**
   ```bash
   git clone https://github.com/naman2398/ggir_qc_tool.git
   cd ggir_qc_tool
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Secrets**
   
   Create `.streamlit/secrets.toml`:
   ```toml
   [azure]
   client_id = "your-client-id"
   client_secret = "your-client-secret"
   tenant_id = "your-tenant-id"
   root_folder_path = "path/to/data"
   access_list_file = "App_Access_List.xlsx"
   ```

5. **Run Locally**
   ```bash
   streamlit run app.py
   ```

### Adding New Users

1. Open `App_Access_List.xlsx` in SharePoint/OneDrive
2. Add user email addresses in column A
3. Save the file
4. Changes take effect within 10 minutes (cache refresh)

### Adding New Devices

Edit `config.py`:

```python
# Add device to the list
SUPPORTED_DEVICES = [
    DEVICE_ACTICAL,
    DEVICE_ACTIWATCH,
    DEVICE_PHILIPS,
    DEVICE_FITBIT,
    DEVICE_FDG_ACTICAL,
    "New Device Name"  # Add here
]

# If device requires phases:
DEVICE_PHASE_MAPPING = {
    DEVICE_ACTICAL: [...],
    DEVICE_PHILIPS: [...],
    "New Device Name": ["Phase 1", "Phase 2"]  # Add here
}
```

Restart the application - no other changes needed!

### Troubleshooting

#### Users Can't Login
- Verify email is in `App_Access_List.xlsx`
- Check file is in the correct location
- Wait 10 minutes for cache to refresh

#### Files Not Found
- Verify folder structure matches design:
  - Standard: `device/pid/output_pid/results/`
  - Phased: `device/phase/pid/output_pid/results/`
- Check file names match exactly:
  - `part4_nightsummary_sleep_cleaned.csv`
  - `visualisation_sleep.pdf`
  - `visualisation_data.pdf`

#### Can't Save Changes
- Check Azure API permissions include `Files.ReadWrite.All`
- Verify client secret hasn't expired
- Check application logs in Azure Portal

#### Application Won't Start
- Verify all environment variables are set
- Check Python version is 3.9+
- Review error logs: `az webapp log tail --name ggir-qc-tool`

### Support Contacts

- **Technical Issues**: IT Support at Stony Brook University
- **Access Requests**: Research Administrator
- **Data Issues**: Primary Investigator

## Keyboard Shortcuts

- **Tab**: Navigate between fields
- **Enter**: Submit search
- **Ctrl/Cmd + S**: Save changes (when editing)
- **Esc**: Cancel current operation

## Best Practices

### For Users
1. Always review your changes before saving
2. Use descriptive comments when making significant edits
3. Download a copy of important data before major changes
4. Report any data inconsistencies to your supervisor

### For Administrators
1. Backup the access list file regularly
2. Rotate Azure client secrets every 6 months
3. Monitor application logs weekly
4. Test with a dummy participant before rolling out changes
5. Keep the design document updated

## FAQ

**Q: Can I undo changes after saving?**  
A: No, but the original file is preserved. You can refer to it anytime.

**Q: How many versions can I create?**  
A: Unlimited. Each save increments the version number.

**Q: Can I work offline?**  
A: No, the application requires internet access to Microsoft Graph API.

**Q: What browsers are supported?**  
A: Chrome, Firefox, Safari, and Edge (latest versions).

**Q: Can multiple users edit the same participant file?**  
A: Yes, but each user creates their own version. Coordinate with your team to avoid conflicts.

**Q: How long does the login session last?**  
A: Sessions persist while the browser is open. Close the tab to log out.

**Q: Can I export data to Excel?**  
A: Yes, use the download button in the CSV editor.

---

**Need Help?** Contact your administrator or refer to the full documentation in `README.md` and `DEPLOYMENT.md`.

**Last Updated**: November 19, 2025
