from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from core_engine.tools.google_drive import get_google_drive_tools
from core_engine.tools.gmail import get_gmail_tools

def load_tools(resources: List[Dict[str, Any]]) -> List[BaseTool]:
    """
    Iterates over the resources defined in the JSON payload (originating from the DB).
    If a valid tool is found, it instantiates it via the designated tool factory.
    """
    active_tools = []
    
    for resource in resources:
        res_type = resource.get("type", "").lower()
        res_name = resource.get("name", "Unknown Resource")
        
        print(f"Loading Resource: {res_name} [{res_type}]")
        
        if res_type == "google_drive":
            drive_tools = get_google_drive_tools()
            active_tools.extend(drive_tools)
            print(f" - Loaded {len(drive_tools)} Google Drive tool(s).")
            
        elif res_type == "gmail":
            gmail_tools = get_gmail_tools()
            active_tools.extend(gmail_tools)
            print(f" - Loaded {len(gmail_tools)} Gmail tool(s).")
            
        else:
            print(f" - Resource type '{res_type}' is not supported yet.")
            
    return active_tools
