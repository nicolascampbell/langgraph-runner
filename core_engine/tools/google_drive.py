from typing import List
import os

from langchain_core.tools import BaseTool, tool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


@tool
def google_drive_list_files(query: str = "") -> str:
    """
    Search and list files in Google Drive.
    If query is provided, it searches for files matching the given query string.
    Returns a string summary of the files found, including their names, IDs, and MIME types.
    """
    try:
        if not os.path.exists("token.json"):
            return "Error: token.json not found. Authentication required."

        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/drive"])
        service = build("drive", "v3", credentials=creds)

        args = {
            "pageSize": 10,
            "fields": "nextPageToken, files(id, name, mimeType)"
        }
        if query:
            args["q"] = query

        results = service.files().list(**args).execute()
        items = results.get("files", [])

        if not items:
            return "No files found."

        output = "Files found:\n"
        for item in items:
            output += f"- {item['name']} (ID: {item['id']}, Type: {item['mimeType']})\n"
        return output
    except Exception as e:
        return f"Error interacting with Google Drive API: {str(e)}"

@tool
def google_drive_create_file(filename: str, content: str) -> str:
    """
    Creates a new Google Doc in the user's Google Drive with the given filename and text content.
    Returns the created file's name and ID on success.
    """
    try:
        if not os.path.exists("token.json"):
            return "Error: token.json not found. Authentication required."

        creds = Credentials.from_authorized_user_file("token.json", ["https://www.googleapis.com/auth/drive"])
        service = build("drive", "v3", credentials=creds)

        file_metadata = {
            "name": filename,
            "mimeType": "application/vnd.google-apps.document",
        }
        media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain")

        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name",
        ).execute()

        return f"Successfully created Google Doc '{created['name']}' with ID: {created['id']}"
    except Exception as e:
        return f"Error creating file in Google Drive: {str(e)}"


def get_google_drive_tools() -> List[BaseTool]:
    """
    Initializes and returns the custom Google Drive tools.
    """
    return [google_drive_list_files, google_drive_create_file]
