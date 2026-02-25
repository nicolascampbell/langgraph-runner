from typing import List
from langchain_core.tools import BaseTool, tool
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_google_community.gmail.utils import build_resource_service, get_gmail_credentials
from langchain_google_community.gmail.toolkit import GmailToolkit

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

def get_google_drive_tools() -> List[BaseTool]:
    """
    Initializes and returns the custom Google Drive tools.
    """
    return [google_drive_list_files]

def get_gmail_tools() -> List[BaseTool]:
    """
    Initializes and returns the Gmail toolkit tools.
    Requires credentials.json and token.json to be accessible by the environment.
    """
    try:
        # The utils module handles looking up the local token files.
        credentials = get_gmail_credentials(
            token_file="token.json",
            scopes=["https://mail.google.com/"],
            client_sercret_file="credentials.json",
        )
        api_resource = build_resource_service(credentials=credentials)
        toolkit = GmailToolkit(api_resource=api_resource)
        return toolkit.get_tools()
    except Exception as e:
        print(f"Error initializing Gmail tools: {e}")
        return []
