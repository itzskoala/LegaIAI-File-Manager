# SharePoint Connection Setup

## Step 1 — Register an App in Azure

1. Go to https://portal.azure.com
2. Search for **"App registrations"** and click it
3. Click **"New registration"**
   - Name: anything (e.g. `LegalAI`)
   - Supported account types: **Single tenant**
   - Click **Register**
4. Copy the **Application (client) ID** — this is your `CLIENT_ID`
5. Copy the **Directory (tenant) ID** — this is your `TENANT_ID`

## Step 2 — Create a Client Secret

1. In your app, go to **Certificates & secrets**
2. Click **New client secret**, give it a name, click **Add**
3. Copy the secret **Value** immediately (it won't show again) — this is your `CLIENT_SECRET`

## Step 3 — Grant SharePoint Permissions

1. In your app, go to **API permissions**
2. Click **Add a permission → Microsoft Graph → Application permissions**
3. Search for and add:
   - `Sites.Read.All`
   - `Files.Read.All`
4. Click **Grant admin consent** (requires admin rights on your tenant)

## Step 4 — Add Credentials to the Script

Open `sharepoint_connect.py` and fill in:

```python
TENANT_ID     = "paste-your-tenant-id-here"
CLIENT_ID     = "paste-your-client-id-here"
CLIENT_SECRET = "paste-your-client-secret-here"
```

## Step 5 — Install Dependencies

```bash
pip install msal requests
```

## Step 6 — Run It

```bash
python sharepoint_connect.py
```

If everything is set up correctly, you'll see a list of SharePoint sites printed out.
