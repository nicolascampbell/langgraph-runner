import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Force UTF-8 output so non-ASCII characters in email subjects/bodies don't crash on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from core_engine.tools.google_drive import google_drive_list_files, google_drive_create_file
from core_engine.tools.gmail import get_gmail_tools


def test_drive_list():
    print("\n=== Google Drive: List Files ===")
    result = google_drive_list_files.invoke({"query": ""})
    print(result)


def test_gmail_list():
    print("\n=== Gmail: List 3 Inbox Emails ===")
    tools = get_gmail_tools()
    if not tools:
        print("No Gmail tools loaded. Check credentials.")
        return

    search_tool = next((t for t in tools if "search" in t.name.lower()), None)
    if not search_tool:
        print(f"Search tool not found. Available tools: {[t.name for t in tools]}")
        return

    result = search_tool.invoke({"query": "in:inbox", "max_results": 3, "resource": "messages"})
    print(result)


def test_drive_write():
    print("\n=== Google Drive: Write Test Document ===")
    result = google_drive_create_file.invoke({
        "filename": "workmate-runner-test",
        "content": "This is a test document created by workmate-runner to verify Google Drive write access.",
    })
    print(result)


if __name__ == "__main__":
    test_drive_list()
    test_gmail_list()
    test_drive_write()
