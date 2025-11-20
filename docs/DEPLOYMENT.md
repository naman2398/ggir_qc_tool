# GGIR QC Tool - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the GGIR QC Tool to Microsoft Azure App Service.

## Prerequisites

- Azure subscription with active account
- Azure CLI installed locally
- Git installed locally
- Python 3.9+ installed locally
- Access to SharePoint/OneDrive with appropriate permissions

## Step 1: Azure App Registration

### 1.1 Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Fill in the details:
   - **Name**: GGIR QC Tool
   - **Supported account types**: Accounts in this organizational directory only
   - Click **Register**

### 1.2 Note Down Credentials

After registration, note down:
- **Application (client) ID**
- **Directory (tenant) ID**

### 1.3 Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "GGIR QC Tool Secret")
4. Choose expiration period
5. Click **Add**
6. **Copy the secret value immediately** (you won't be able to see it again)

### 1.4 Configure API Permissions

1. Go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Application permissions**
5. Add the following permissions:
   - `Files.ReadWrite.All`
6. Click **Grant admin consent** for your organization

## Step 2: Prepare SharePoint/OneDrive

### 2.1 Create Folder Structure

Organize your participant files according to one of these structures:

**Standard Structure:**
```
<root_folder>/
  ├── ActiwatchL/
  │   └── <participantID>/
  │       └── output_<participantID>/
  │           └── results/
  │               ├── part4_nightsummary_sleep_cleaned.csv
  │               ├── visualisation_sleep.pdf
  │               └── visualisation_data.pdf
  ├── FitBit/
  └── FDG Actical/
```

**Phased Structure:**
```
<root_folder>/
  ├── Actical/
  │   ├── Baseline/
  │   │   └── <participantID>/
  │   │       └── output_<participantID>/
  │   │           └── results/
  │   ├── Overnight/
  │   ├── Pre-Overnight/
  │   └── Post-Overnight/
  └── Philips Health Band/
      ├── Pre-Scan/
      ├── Post-Scan/
      ├── Pre-Overnight/
      └── Post-Overnight/
```

### 2.2 Create Access List File

1. Create an Excel file named `App_Access_List.xlsx`
2. In the first column (Column A), list authorized user email addresses:
   ```
   user1@stonybrook.edu
   user2@stonybrook.edu
   researcher@stonybrook.edu
   ```
3. Upload this file to your SharePoint/OneDrive root folder

## Step 3: Local Testing

### 3.1 Clone Repository

```bash
git clone https://github.com/naman2398/ggir_qc_tool.git
cd ggir_qc_tool
```

### 3.2 Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 3.4 Configure Secrets

Create `.streamlit/secrets.toml`:

```toml
[azure]
client_id = "your-client-id-here"
client_secret = "your-client-secret-here"
tenant_id = "your-tenant-id-here"
root_folder_path = "GGIR_Data/Accelerometer_Files"
access_list_file = "App_Access_List.xlsx"
```

### 3.5 Run Locally

```bash
streamlit run app.py
```

Test the application at `http://localhost:8501`

## Step 4: Deploy to Azure App Service

### 4.1 Login to Azure

```bash
az login
```

### 4.2 Create Resource Group

```bash
az group create --name ggir-qc-rg --location eastus
```

### 4.3 Create App Service Plan

```bash
az appservice plan create \
  --name ggir-qc-plan \
  --resource-group ggir-qc-rg \
  --sku B1 \
  --is-linux
```

### 4.4 Create Web App

```bash
az webapp create \
  --resource-group ggir-qc-rg \
  --plan ggir-qc-plan \
  --name ggir-qc-tool \
  --runtime "PYTHON:3.9"
```

### 4.5 Configure Application Settings

```bash
az webapp config appsettings set \
  --resource-group ggir-qc-rg \
  --name ggir-qc-tool \
  --settings \
    CLIENT_ID="your-client-id" \
    CLIENT_SECRET="your-client-secret" \
    TENANT_ID="your-tenant-id" \
    ROOT_FOLDER_PATH="GGIR_Data/Accelerometer_Files" \
    ACCESS_LIST_FILE="App_Access_List.xlsx"
```

### 4.6 Create Startup Command

Create a file named `startup.sh`:

```bash
#!/bin/bash
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
```

Configure the startup command:

```bash
az webapp config set \
  --resource-group ggir-qc-rg \
  --name ggir-qc-tool \
  --startup-file "startup.sh"
```

### 4.7 Deploy Code

**Option A: Deploy from local Git**

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Configure deployment
az webapp deployment source config-local-git \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg

# Get deployment URL
az webapp deployment list-publishing-credentials \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg \
  --query scmUri \
  --output tsv

# Add Azure remote and push
git remote add azure <deployment-url>
git push azure main
```

**Option B: Deploy from GitHub**

```bash
az webapp deployment source config \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg \
  --repo-url https://github.com/naman2398/ggir_qc_tool \
  --branch main \
  --manual-integration
```

### 4.8 Enable Application Insights (Optional)

```bash
az monitor app-insights component create \
  --app ggir-qc-insights \
  --location eastus \
  --resource-group ggir-qc-rg

az webapp config appsettings set \
  --resource-group ggir-qc-rg \
  --name ggir-qc-tool \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

## Step 5: Verify Deployment

### 5.1 Check App Status

```bash
az webapp show \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg \
  --query state
```

### 5.2 View Logs

```bash
az webapp log tail \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg
```

### 5.3 Access Application

Open your browser and navigate to:
```
https://ggir-qc-tool.azurewebsites.net
```

## Step 6: Configure Custom Domain (Optional)

### 6.1 Add Custom Domain

```bash
az webapp config hostname add \
  --webapp-name ggir-qc-tool \
  --resource-group ggir-qc-rg \
  --hostname ggir-qc.yourdomain.edu
```

### 6.2 Enable HTTPS

```bash
az webapp config ssl bind \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg \
  --certificate-thumbprint <thumbprint> \
  --ssl-type SNI
```

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull origin main

# Push to Azure
git push azure main
```

### Scale Up/Down

```bash
# Scale up to higher tier
az appservice plan update \
  --name ggir-qc-plan \
  --resource-group ggir-qc-rg \
  --sku P1V2

# Scale down
az appservice plan update \
  --name ggir-qc-plan \
  --resource-group ggir-qc-rg \
  --sku B1
```

### Monitor Usage

```bash
# View metrics
az monitor metrics list \
  --resource /subscriptions/<subscription-id>/resourceGroups/ggir-qc-rg/providers/Microsoft.Web/sites/ggir-qc-tool \
  --metric-names CpuTime Requests
```

## Troubleshooting

### Issue: Application Not Starting

**Solution**: Check logs
```bash
az webapp log tail --name ggir-qc-tool --resource-group ggir-qc-rg
```

### Issue: Authentication Failing

**Solution**: Verify environment variables
```bash
az webapp config appsettings list \
  --name ggir-qc-tool \
  --resource-group ggir-qc-rg
```

### Issue: Cannot Access Files

**Solution**: 
1. Verify API permissions are granted
2. Check root folder path is correct
3. Ensure service principal has access to SharePoint

## Security Best Practices

1. **Rotate Secrets Regularly**: Update client secrets every 6-12 months
2. **Enable HTTPS Only**: Enforce HTTPS in production
3. **Restrict Access**: Use Azure AD Conditional Access policies
4. **Monitor Logs**: Enable Application Insights and set up alerts
5. **Backup Data**: Regularly backup the access list and important files
6. **Review Permissions**: Audit Graph API permissions quarterly

## Cost Estimation

Estimated monthly costs (as of 2025):
- **Basic B1 Plan**: ~$55/month
- **Standard S1 Plan**: ~$70/month
- **Premium P1V2 Plan**: ~$200/month

Factors affecting cost:
- Number of users
- Data transfer volume
- Application Insights usage

## Support

For deployment issues:
- Check Azure Portal for service health
- Review Application Insights logs
- Contact Azure Support if needed

For application issues:
- Review `design_document.md`
- Check `README.md`
- Contact the development team

---

**Last Updated**: November 19, 2025
