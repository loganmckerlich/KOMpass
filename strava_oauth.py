"""
Strava OAuth implementation following official Strava API documentation.
https://developers.strava.com/docs/authentication/
"""
import os
import requests
import urllib.parse
from typing import Dict, Optional


class StravaOAuth:
    """Handles Strava OAuth flow according to official documentation"""
    
    def __init__(self):
        self.client_id = os.environ.get("STRAVA_CLIENT_ID")
        self.client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
        self.authorization_base_url = "https://www.strava.com/oauth/authorize"
        self.token_url = "https://www.strava.com/oauth/token"
        self.api_base_url = "https://www.strava.com/api/v3"
        
        if not self.client_id or self.client_id == "your_client_id_here":
            raise ValueError("STRAVA_CLIENT_ID environment variable is required")
        if not self.client_secret:
            raise ValueError("STRAVA_CLIENT_SECRET environment variable is required")
    
    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate authorization URL following Strava's OAuth documentation.
        
        Args:
            redirect_uri: Must exactly match the redirect URI registered with Strava
            state: Optional state parameter for security
            
        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "approval_prompt": "force",  # Force approval prompt per Strava docs
            "scope": "read,activity:read_all"  # Comma-separated as per Strava docs
        }
        
        if state:
            params["state"] = state
            
        query_string = urllib.parse.urlencode(params)
        return f"{self.authorization_base_url}?{query_string}"
    
    def exchange_code_for_token(self, authorization_code: str, redirect_uri: str) -> Dict:
        """
        Exchange authorization code for access token.
        
        Args:
            authorization_code: Code received from Strava callback
            redirect_uri: Same redirect URI used in authorization request
            
        Returns:
            Dictionary containing token information
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": authorization_code,
            "grant_type": "authorization_code"
        }
        
        response = requests.post(self.token_url, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: Refresh token from previous authentication
            
        Returns:
            Dictionary containing new token information
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        response = requests.post(self.token_url, data=data)
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_athlete(self, access_token: str) -> Dict:
        """
        Get athlete information using access token.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Dictionary containing athlete information
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(f"{self.api_base_url}/athlete", headers=headers)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code != 200:
            raise Exception(f"Failed to get athlete info: {response.status_code} - {response.text}")
        
        return response.json()