# Setup Guide: Secure Participant File Finder & Editor

This guide walks you through the complete setup process from scratch.

## Table of Contents

1. [Google Cloud Setup](#1-google-cloud-setup)
2. [Google Drive Setup](#2-google-drive-setup)
3. [Google Sheets Setup](#3-google-sheets-setup)
4. [Local Development](#4-local-development)
5. [Deployment](#5-deployment)

---

## 1. Google Cloud Setup

### Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "GGIR-QC-App")
4. Click "Create"

### Enable Required APIs

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for and enable:
   - **Google Drive API**
   - **Google Sheets API**

### Create a Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Enter a name (e.g., "ggir-qc-service-account")
4. Click "Create and Continue"
5. For role, select "Editor" (or create a custom role)
6. Click "Continue" → "Done"

### Download Service Account Key

1. In "APIs & Services" → "Credentials", find your service account
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" → "Create new key"
5. Select "JSON" format
6. Click "Create" - the key file will download automatically
7. **Keep this file secure** - it provides access to your Google resources

---

## 2. Google Drive Setup

### Organize Your Folder Structure

Your Google Drive should have the following structure:

```
Root Folder (e.g., "GGIR_Participant_Data")/
├── ActiGraph/
│   ├── PID001/
│   │   └── output_PID001/
│   │       └── results/
│   │           ├── part4_nightsummary_sleep_cleaned.csv
│   │           ├── visualisation_sleep.pdf
│   │           └── visualisation_data.pdf
│   ├── PID002/
│   │   └── output_PID002/
│   │       └── results/
│   │           └── ...
│   └── ...
├── GENEActiv/
│   └── ...
├── Axivity/
│   └── ...
└── ...
```

### Share Folder with Service Account

1. Open Google Drive and navigate to your root folder
2. Right-click the folder → "Share"
3. Paste your service account email (found in the JSON key file as `client_email`)
4. Set permission to "Editor"
5. Uncheck "Notify people" (service accounts don't need notifications)
6. Click "Share"

### Get Folder ID

1. Open the root folder in Google Drive
2. Look at the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
3. Copy the `FOLDER_ID_HERE` part - you'll need this later

---

## 3. Google Sheets Setup

### Create the Allowlist Sheet

1. Create a new Google Sheet
2. Name it "GGIR QC App Access List" (or similar)
3. In cell A1, type "Authorized Emails" (optional header)
4. Starting from A2 (or A1 if no header), add authorized email addresses:
   ```
   user1@stonybrook.edu
   user2@stonybrook.edu
   user3@stonybrook.edu
   ```

### Share Sheet with Service Account

1. Click the "Share" button
2. Paste your service account email
3. Set permission to "Viewer" (read-only is sufficient)
4. Uncheck "Notify people"
5. Click "Share"

### Get Sheet ID

1. Look at the URL of your Google Sheet
2. It looks like: `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`
3. Copy the `SPREADSHEET_ID` part - you'll need this later

---

## 4. Local Development

### Install Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git

### Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd GGIR_QC

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Secrets

1. Create the secrets directory:
   ```bash
   mkdir -p .streamlit
   ```

2. Create the secrets file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

3. Edit `.streamlit/secrets.toml`:

   ```toml
   [google_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "your-cert-url"

   root_folder_id = "YOUR_DRIVE_FOLDER_ID"
   allowlist_sheet_id = "YOUR_SPREADSHEET_ID"
   allowlist_range = "Sheet1!A:A"
   ```

   **Note**: You can copy the values directly from your downloaded service account JSON file.

### Test Locally

```bash
streamlit run app.py
```

The app should open at `http://localhost:8501`. Test with:
- An authorized email from your Google Sheet
- A valid accelerometer type and participant ID

---

## 5. Deployment

### Prepare Repository

1. Ensure `.gitignore` includes `.streamlit/secrets.toml`
2. Commit and push your code:
   ```bash
   git add .
   git commit -m "Initial application setup"
   git push origin main
   ```

### Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Fill in:
   - **Repository**: Your GitHub repo
   - **Branch**: main (or your default branch)
   - **Main file path**: app.py
5. Click "Advanced settings"
6. In the "Secrets" section, paste the **entire contents** of your `.streamlit/secrets.toml` file
7. Click "Deploy"

### Verify Deployment

1. Wait for deployment to complete (usually 2-5 minutes)
2. Test the deployed app with an authorized email
3. Verify you can search and access files

---

## Quick Reference: Required IDs

You'll need to collect these IDs during setup:

| Item | Where to Find It | Example Format |
|------|-----------------|----------------|
| Service Account Email | Downloaded JSON key file | `service-account@project.iam.gserviceaccount.com` |
| Root Folder ID | Google Drive URL | `1AbCdEfGhIjKlMnOpQrStUvWxYz` |
| Allowlist Sheet ID | Google Sheets URL | `1BcDeFgHiJkLmNoPqRsTuVwXyZ2aBcDeFgHiJkLmNo` |
| Allowlist Range | Sheet name and column | `Sheet1!A:A` |

---

## Security Checklist

Before going live, verify:

- [ ] Service account JSON key is not committed to Git
- [ ] `.streamlit/secrets.toml` is in `.gitignore`
- [ ] Service account has minimum necessary permissions
- [ ] Google Drive folder is only shared with service account (not public)
- [ ] Allowlist sheet is only shared with service account
- [ ] All authorized users are listed in the allowlist sheet
- [ ] Test authentication with unauthorized email (should be rejected)

---

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Permission denied" on Google Drive
- Verify service account has "Editor" access to the Drive folder
- Check that you shared with the correct service account email

### "Could not find folder"
- Verify the folder structure matches the expected pattern
- Check folder names match exactly (case-sensitive)
- Ensure service account can access all parent folders

### App won't start on Streamlit Cloud
- Check that secrets are properly formatted (valid TOML syntax)
- Verify all required secrets are present
- Check deployment logs for specific error messages

---

## Next Steps

After successful deployment:

1. Add all authorized users to the Google Sheet
2. Test with multiple user accounts
3. Create test participant folders to verify functionality
4. Document any custom accelerometer types or folder structures
5. Set up monitoring/logging if needed

---

## Support

For issues or questions:
- Check the main [README.md](README.md) for common problems
- Review the [design_document.md](design_document.md) for architecture details
- Contact your development team or system administrator

---

**Congratulations!** Your Secure Participant File Finder & Editor is now set up and ready to use.
