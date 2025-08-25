import os
import requests
import json
import urllib.parse

# Strava App Configuration
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "your_client_id_here")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

# For backward compatibility - legacy environment variables
STRAVA_ACCESS_TOKEN = os.environ.get("STRAVA_ACCESS_TOKEN")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")

STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

def get_authorization_url(redirect_uri, state=None):
    """Generate Strava OAuth authorization URL"""
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "read,activity:read_all",
        "approval_prompt": "force"
    }
    if state:
        params["state"] = state
    
    return f"{STRAVA_AUTH_URL}?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(authorization_code, redirect_uri):
    """Exchange authorization code for access token"""
    if not STRAVA_CLIENT_SECRET:
        raise ValueError("STRAVA_CLIENT_SECRET environment variable is required")
    
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": authorization_code,
        "grant_type": "authorization_code"
    }
    
    response = requests.post(STRAVA_TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token):
    """Refresh an expired access token"""
    if not STRAVA_CLIENT_SECRET:
        raise ValueError("STRAVA_CLIENT_SECRET environment variable is required")
    
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    response = requests.post(STRAVA_TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()

def get_headers(access_token=None):
    """Get headers for API requests"""
    token = access_token or STRAVA_ACCESS_TOKEN
    if not token:
        raise ValueError("No access token available")
    
    return {
        "Authorization": f"Bearer {token}"
    }

def get_athlete(access_token=None):
    """Get athlete information using provided or default access token"""
    url = f"{STRAVA_API_BASE_URL}/athlete"
    response = requests.get(url, headers=get_headers(access_token))
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    try:
        athlete = get_athlete()
        print("Authenticated athlete profile:")
        # Safely print unicode characters
        print(json.dumps(athlete, indent=2, ensure_ascii=False))
    except ValueError as e:
        print(f"Error: {e}")
        print("To use this script directly, set the STRAVA_ACCESS_TOKEN environment variable.")
        print("For OAuth flow, use the main.py Streamlit app instead.")
