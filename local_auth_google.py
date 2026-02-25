import os
from google_auth_oauthlib.flow import InstalledAppFlow

# The scopes required by the Gmail and Google Drive tools
SCOPES = [
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/drive"
]

def main():
    print("Google Local Authentication flow starting...")
    
    if os.path.exists("token.json"):
        print("A token.json file already exists! You're already authenticated.")
        return
        
    if not os.path.exists("credentials.json"):
        print("ERROR: Could not find 'credentials.json' in this directory.")
        print("Please download an OAuth 2.0 Client ID from the Google Cloud Console")
        print("and save it here as 'credentials.json'.")
        return

    # Spin up the local webserver flow to prompt the user to login
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
    )
    
    # This will open the default web browser and ask the user to authenticate
    # We force port 8080 so it matches the explicit whitelist we will set in GCP
    creds = flow.run_local_server(port=8080)

    # Save the credentials for the next run (including the refresh token)
    with open("token.json", "w") as token:
        token.write(creds.to_json())
        
    print("\nSUCCESS! Saved 'token.json' to the local directory.")
    print("The LangGraph agents can now use the Google modules.")

if __name__ == "__main__":
    main()
