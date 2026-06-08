import msal
import requests

# --- Your Azure App credentials ---
# You get these from the Azure portal (see SETUP.md for instructions)
TENANT_ID     = "your-tenant-id"       # Azure AD tenant ID
CLIENT_ID     = "your-client-id"       # App (client) ID
CLIENT_SECRET = "your-client-secret"   # Client secret value

# The Graph API base URL
GRAPH_URL = "https://graph.microsoft.com/v1.0"


def get_access_token():
    """Get an access token from Microsoft using your app credentials."""

    # Tell MSAL which Azure tenant to authenticate against
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"

    # Create the MSAL app object
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET
    )

    # Request a token for the Graph API
    result = app.acquire_token_for_client(
        scopes=["https://graph.microsoft.com/.default"]
    )

    # Check if we got a token back
    if "access_token" not in result:
        print("Failed to get token:", result.get("error_description"))
        return None

    print("Successfully got an access token!")
    return result["access_token"]


def test_sharepoint_connection(token):
    """Make a simple call to the Graph API to confirm we can reach SharePoint."""

    headers = {"Authorization": f"Bearer {token}"}

    # This endpoint lists all SharePoint sites your app can access
    response = requests.get(f"{GRAPH_URL}/sites?search=*", headers=headers)

    if response.status_code == 200:
        sites = response.json().get("value", [])
        print(f"\nConnection successful! Found {len(sites)} site(s):")
        for site in sites:
            print(f"  - {site.get('displayName')} ({site.get('webUrl')})")
    else:
        print(f"Connection failed. Status: {response.status_code}")
        print(response.json())


# --- Run it ---
if __name__ == "__main__":
    token = get_access_token()
    if token:
        test_sharepoint_connection(token)
