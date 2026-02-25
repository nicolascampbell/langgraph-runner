from typing import List

from langchain_core.tools import BaseTool
from langchain_google_community.gmail.utils import build_resource_service, get_gmail_credentials
from langchain_google_community.gmail.toolkit import GmailToolkit


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
