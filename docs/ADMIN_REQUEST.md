# Azure App Registration Request

**Subject:** Request: Azure App Registration & Permissions for GGIR QC Tool

---

Hi,

I'm deploying an internal QC tool for actigraphy research data on our Azure Web App. I need your help to set up the required authentication and permissions.

---

## What I Need

### 1. Create App Registration

Location: Azure Portal → Microsoft Entra ID → App registrations → New registration

| Setting | Value |
|---------|-------|
| Name | `GGIR-QC-Tool` |
| Supported account types | Accounts in this organizational directory only |
| Redirect URI | Leave blank |

### 2. Create Client Secret

Location: App registration → Certificates & secrets → New client secret

| Setting | Value |
|---------|-------|
| Description | `GGIR-QC-Production` |
| Expires | 24 months |

### 3. Add API Permissions & Grant Admin Consent

Location: App registration → API permissions → Add a permission → Microsoft Graph → Application permissions

| Permission | Purpose |
|------------|---------|
| `Sites.Read.All` | Read files from SharePoint |
| `Files.ReadWrite.All` | Save edited files back to SharePoint |

After adding, please click **"Grant admin consent for [Organization]"**

---

## SharePoint Site Accessed

The app will access files in:
```
https://stonybrookmedicine.sharepoint.com/sites/CUBIT
```

Folder path:
```
CBT-I Documents/Actigraphy Analysis (Multi-Study Data Sets)/GGIR_final_outputs/
```

---

## Values I Need Back

| Value | Location |
|-------|----------|
| Application (client) ID | App registration → Overview |
| Directory (tenant) ID | App registration → Overview |
| Client Secret Value | From step 2 (copy immediately, shown only once) |

---

Please let me know if you have any questions.

Thanks!
