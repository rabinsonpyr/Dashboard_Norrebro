"""
Google Drive access via a service account (supports both reading and
writing the Excel file, unlike a plain public share link).
"""

import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

import config

SCOPES = ["https://www.googleapis.com/auth/drive"]

EXCEL_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def get_drive_service():
    if not config.SERVICE_ACCOUNT_INFO:
        raise RuntimeError(
            "No [gcp_service_account] found in secrets. Add it under this "
            "app's Settings → Secrets (see README.md)."
        )
    creds = service_account.Credentials.from_service_account_info(
        dict(config.SERVICE_ACCOUNT_INFO), scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def download_excel_bytes(file_id: str) -> bytes:
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.read()


def upload_excel_bytes(file_id: str, data: bytes) -> None:
    service = get_drive_service()
    media = MediaIoBaseUpload(
        io.BytesIO(data), mimetype=EXCEL_MIME_TYPE, resumable=True
    )
    service.files().update(fileId=file_id, media_body=media).execute()
