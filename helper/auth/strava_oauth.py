"""
Strava OAuth implementation following official Strava API documentation.
https://developers.strava.com/docs/authentication/
"""
import os
import requests
import urllib.parse
from typing import Dict, Optional
from ..config.logging_config import get_logger

logger = get_logger(__name__)


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
            "scope": "read,activity:read_all,profile:read_all"  # Expanded scope for comprehensive data
        }
        
        if state:
            params["state"] = state
            
        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.authorization_base_url}?{query_string}"
        
        # Log for debugging OAuth issues
        logger.debug(f"Generated authorization URL with redirect_uri: {redirect_uri}")
        logger.debug(f"Full authorization URL: {auth_url}")
        
        return auth_url
    
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
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        logger.debug(f"Exchanging code for token with redirect_uri: {redirect_uri}")
        
        response = requests.post(self.token_url, data=data)
        
        if response.status_code != 200:
            error_msg = f"Token exchange failed: {response.status_code} - {response.text}"
            logger.error(f"Token exchange error: {error_msg}")
            
            # Provide specific guidance for common OAuth errors
            if response.status_code == 400:
                if "invalid_grant" in response.text.lower():
                    error_msg += "\n\nThis usually means:\n"
                    error_msg += "1. The authorization code has expired (they expire quickly)\n"
                    error_msg += "2. The authorization code has already been used\n"
                    error_msg += "3. The redirect_uri doesn't match what was used in the authorization request"
                elif "invalid_client" in response.text.lower():
                    error_msg += "\n\nThis usually means your STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET is incorrect."
            
            raise Exception(error_msg)
        
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
    
    def get_athlete_stats(self, access_token: str) -> Dict:
        """
        Get athlete statistics including power records and performance metrics.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Dictionary containing athlete statistics and power records
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(f"{self.api_base_url}/athletes/{{id}}/stats".replace("{{id}}", "authenticated"), headers=headers)
        
        # For the authenticated athlete, we can use the special endpoint
        response = requests.get(f"{self.api_base_url}/athlete/stats", headers=headers)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code != 200:
            raise Exception(f"Failed to get athlete stats: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_athlete_zones(self, access_token: str) -> Dict:
        """
        Get athlete power and heart rate zones.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Dictionary containing power and heart rate zones
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(f"{self.api_base_url}/athlete/zones", headers=headers)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code != 200:
            raise Exception(f"Failed to get athlete zones: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_athlete_activities(self, access_token: str, page: int = 1, per_page: int = 30, after_timestamp: Optional[int] = None) -> Dict:
        """
        Get athlete's recent activities for fitness analysis.
        
        Args:
            access_token: Valid Strava access token
            page: Page number for pagination
            per_page: Number of activities per page (max 200)
            after_timestamp: Unix timestamp to get activities after this time
            
        Returns:
            List of activity dictionaries
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "page": page,
            "per_page": min(per_page, 200)  # Strava API limit
        }
        
        if after_timestamp:
            params["after"] = after_timestamp
        
        response = requests.get(f"{self.api_base_url}/athlete/activities", headers=headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code != 200:
            raise Exception(f"Failed to get athlete activities: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_activity_zones(self, access_token: str, activity_id: str) -> Dict:
        """
        Get detailed power and heart rate zones for a specific activity.
        
        Args:
            access_token: Valid Strava access token
            activity_id: Strava activity ID
            
        Returns:
            Dictionary containing activity zones data
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        response = requests.get(f"{self.api_base_url}/activities/{activity_id}/zones", headers=headers)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code == 404:
            raise Exception(f"Activity {activity_id} not found or no zones data available")
        elif response.status_code != 200:
            raise Exception(f"Failed to get activity zones: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_activity_streams(self, access_token: str, activity_id: str, keys: str = "time,watts,heartrate,cadence,velocity_smooth") -> Dict:
        """
        Get detailed activity streams for power curve analysis and advanced metrics.
        
        Args:
            access_token: Valid Strava access token
            activity_id: Strava activity ID
            keys: Comma-separated list of stream types to fetch
            
        Returns:
            Dictionary containing detailed activity streams
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "keys": keys,
            "key_by_type": "true"
        }
        
        response = requests.get(f"{self.api_base_url}/activities/{activity_id}/streams", headers=headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code == 404:
            raise Exception(f"Activity {activity_id} not found or no streams data available")
        elif response.status_code != 200:
            raise Exception(f"Failed to get activity streams: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_activity_detailed(self, access_token: str, activity_id: str, include_all_efforts: bool = True) -> Dict:
        """
        Get detailed activity information including segment efforts and advanced metrics.
        
        Args:
            access_token: Valid Strava access token
            activity_id: Strava activity ID
            include_all_efforts: Include all segment efforts and laps
            
        Returns:
            Dictionary containing detailed activity information
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "include_all_efforts": str(include_all_efforts).lower()
        }
        
        response = requests.get(f"{self.api_base_url}/activities/{activity_id}", headers=headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code == 404:
            raise Exception(f"Activity {activity_id} not found")
        elif response.status_code != 200:
            raise Exception(f"Failed to get detailed activity: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_athlete_koms(self, access_token: str, page: int = 1, per_page: int = 30) -> Dict:
        """
        Get athlete's KOM/QOM achievements for performance analysis.
        
        Args:
            access_token: Valid Strava access token
            page: Page number for pagination
            per_page: Number of KOMs per page
            
        Returns:
            List of KOM/QOM achievements
        """
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        params = {
            "page": page,
            "per_page": min(per_page, 200)
        }
        
        response = requests.get(f"{self.api_base_url}/athlete/koms", headers=headers, params=params)
        
        if response.status_code == 401:
            raise Exception("Access token is invalid or expired")
        elif response.status_code != 200:
            raise Exception(f"Failed to get athlete KOMs: {response.status_code} - {response.text}")
        
        return response.json()