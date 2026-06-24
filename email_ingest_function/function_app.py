import base64
import logging
import os
from datetime import datetime, timezone

import azure.functions as func
import msal
import requests
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Epoch fallback for the very first run, so the initial poll doesn't try to
# pull every email that's ever existed in the mailbox.
EPOCH = "1970-01-01T00:00:00Z"


def _get_graph_token() -> str:
    authority = f"https://login.microsoftonline.com/{os.environ['GRAPH_TENANT_ID']}"
    client = msal.ConfidentialClientApplication(
        client_id=os.environ["GRAPH_CLIENT_ID"],
        client_credential=os.environ["GRAPH_CLIENT_SECRET"],
        authority=authority,
    )
    # app-only (client credentials) flow -- this runs unattended on a timer,
    # there's no user to interactively sign in.
    result = client.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in result:
        raise RuntimeError(f"Graph auth failed: {result.get('error_description')}")
    return result["access_token"]


def _checkpoint_blob(blob_service: BlobServiceClient):
    container = blob_service.get_container_client(os.environ["CHECKPOINT_CONTAINER"])
    if not container.exists():
        container.create_container()
    return container.get_blob_client("last_received_datetime.txt")


def _read_checkpoint(blob_client) -> str:
    if not blob_client.exists():
        return EPOCH
    return blob_client.download_blob().readall().decode("utf-8").strip()


def _write_checkpoint(blob_client, value: str):
    blob_client.upload_blob(value, overwrite=True)


def _fetch_new_messages(token: str, mailbox: str, since: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    url = (
        f"{GRAPH_BASE}/users/{mailbox}/messages"
        f"?$filter=receivedDateTime gt {since} and hasAttachments eq true"
        f"&$orderby=receivedDateTime asc"
        f"&$select=id,subject,receivedDateTime"
        f"&$top=50"
    )

    messages = []
    while url:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        body = response.json()
        messages.extend(body.get("value", []))
        url = body.get("@odata.nextLink")
    return messages


def _fetch_pdf_attachments(token: str, mailbox: str, message_id: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE}/users/{mailbox}/messages/{message_id}/attachments"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    return [
        a for a in response.json().get("value", [])
        if a.get("contentType") == "application/pdf" and "contentBytes" in a
    ]


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False)
def poll_mailbox(timer: func.TimerRequest) -> None:
    mailbox = os.environ["MAILBOX_ADDRESS"]
    blob_service = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
    attachments_container = blob_service.get_container_client(os.environ["ATTACHMENTS_CONTAINER"])
    if not attachments_container.exists():
        attachments_container.create_container()

    checkpoint_blob = _checkpoint_blob(blob_service)
    since = _read_checkpoint(checkpoint_blob)

    token = _get_graph_token()
    messages = _fetch_new_messages(token, mailbox, since)
    logging.info(f"[poll_mailbox] {len(messages)} new message(s) with attachments since {since}")

    latest_received = since
    for message in messages:
        for attachment in _fetch_pdf_attachments(token, mailbox, message["id"]):
            blob_name = f"{message['id']}_{attachment['name']}"
            pdf_bytes = base64.b64decode(attachment["contentBytes"])
            attachments_container.get_blob_client(blob_name).upload_blob(pdf_bytes, overwrite=True)
            logging.info(f"[poll_mailbox] uploaded {blob_name} ({len(pdf_bytes)} bytes)")

        if message["receivedDateTime"] > latest_received:
            latest_received = message["receivedDateTime"]

    if latest_received != since:
        _write_checkpoint(checkpoint_blob, latest_received)
