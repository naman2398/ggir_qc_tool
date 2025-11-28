# GGIR QC Tool - Deployment Guide

## Prerequisites
- Azure subscription
- Python 3.9+
- Access to SharePoint site

## Step 1: Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com) → **Azure Active Directory** → **App registrations**
2. Click **New registration** → Name: "GGIR QC Tool" → Register
3. Note down: **Application (client) ID** and **Directory (tenant) ID**
4. Go to **Certificates & secrets** → **New client secret** → Copy the value
5. Go to **API permissions** → **Add permission** → **Microsoft Graph** → **Application permissions**
6. Add: `Sites.Read.All`, `Sites.ReadWrite.All`
7. Click **Grant admin consent**

## Step 2: SharePoint Setup

### Folder Structure
```
CBT-I Documents/
└── Actigraphy Analysis (Multi-Study Data Sets)/
    └── GGIR_final_outputs/
        ├── App_Access_List.xlsx
        ├── Actical/
        │   └── Baseline/
        │       └── PID123/
        │           └── output_PID123/
        │               └── results/
        │                   ├── part4_nightsummary_sleep_cleaned.csv
        │                   ├── visualisation_sleep.pdf
        │                   └── visualisation_data.pdf
        ├── ActiwatchL/
        ├── Philips Health Band/
        ├── FitBit/
        └── FDG Actical/
```

### Access List File
Create `App_Access_List.xlsx` with one column:
```
| email                          |
|--------------------------------|
| user1@stonybrookmedicine.edu   |
| user2@stonybrookmedicine.edu   |
```

## Step 3: Local Testing

```bash
git clone https://github.com/naman2398/ggir_qc_tool.git
cd ggir_qc_tool
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:
```toml
[azure]
client_id = "your-client-id"
client_secret = "your-client-secret"
tenant_id = "your-tenant-id"
```

Run:
```bash
streamlit run app.py
```

## Step 4: Deploy to Azure App Service

```bash
# Login
az login

# Create resources
az group create --name ggir-qc-rg --location eastus
az appservice plan create --name ggir-qc-plan --resource-group ggir-qc-rg --sku B1 --is-linux
az webapp create --resource-group ggir-qc-rg --plan ggir-qc-plan --name ggir-qc-tool --runtime "PYTHON:3.9"

# Configure secrets
az webapp config appsettings set --resource-group ggir-qc-rg --name ggir-qc-tool --settings \
  CLIENT_ID="your-client-id" \
  CLIENT_SECRET="your-client-secret" \
  TENANT_ID="your-tenant-id"

# Deploy
az webapp deployment source config --name ggir-qc-tool --resource-group ggir-qc-rg \
  --repo-url https://github.com/naman2398/ggir_qc_tool --branch main --manual-integration
```

## Step 5: Verify

```bash
az webapp log tail --name ggir-qc-tool --resource-group ggir-qc-rg
```

Access: `https://ggir-qc-tool.azurewebsites.net`
