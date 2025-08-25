import os
import requests
import json
import urllib.parse

# Environment variables
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

# Strava API URLs
STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"
STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"

def get_authorization_url(redirect_uri, scope="read", state=None):
    """
    Generate the Strava authorization URL for OAuth flow.
    
    Args:
        redirect_uri (str): The redirect URI configured in your Strava app
        scope (str): Comma-separated list of scopes (e.g., "read,activity:read")
        state (str): Optional state parameter for CSRF protection
    
    Returns:
        str: The authorization URL to redirect user to
    """
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "approval_prompt": "auto"
    }
    
    if state:
        params["state"] = state
    
    return f"{STRAVA_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(code, redirect_uri):
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        code (str): Authorization code from Strava callback
        redirect_uri (str): Same redirect URI used in authorization
    
    Returns:
        dict: Token response containing access_token, refresh_token, etc.
    """
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    
    response = requests.post(STRAVA_TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()

def refresh_access_token(refresh_token):
    """
    Refresh the access token using refresh token.
    
    Args:
        refresh_token (str): The refresh token
    
    Returns:
        dict: New token response
    """
    data = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(STRAVA_TOKEN_URL, data=data)
    response.raise_for_status()
    return response.json()

def get_headers(access_token):
    """
    Get headers for API requests.
    
    Args:
        access_token (str): The access token
    
    Returns:
        dict: Headers with authorization
    """
    return {
        "Authorization": f"Bearer {access_token}"
    }

def get_athlete(access_token):
    """
    Get authenticated athlete information.
    
    Args:
        access_token (str): The access token
    
    Returns:
        dict: Athlete information
    """
    url = f"{STRAVA_API_BASE_URL}/athlete"
    response = requests.get(url, headers=get_headers(access_token))
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    athlete = get_athlete()
    print("Authenticated athlete profile:")
    # Safely print unicode characters
    print(json.dumps(athlete, indent=2, ensure_ascii=False))
