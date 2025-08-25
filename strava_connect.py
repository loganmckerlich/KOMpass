import os
import json
from stravalib.client import Client
from stravalib.exc import AccessUnauthorized
from logging_config import get_logger, log_error, log_function_entry, log_function_exit

logger = get_logger(__name__)

# Strava App Configuration
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "your_client_id_here")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")

# For backward compatibility - legacy environment variables
STRAVA_ACCESS_TOKEN = os.environ.get("STRAVA_ACCESS_TOKEN")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")

# Log configuration status on module load
if STRAVA_CLIENT_ID and STRAVA_CLIENT_ID != "your_client_id_here":
    logger.info("Strava client ID found in environment")
else:
    logger.warning("Strava client ID not found in environment variables")

if STRAVA_CLIENT_SECRET:
    logger.info("Strava client secret found in environment")
else:
    logger.warning("Strava client secret not found in environment variables")

def get_authorization_url(redirect_uri, state=None):
    """Generate Strava OAuth authorization URL using Swagger client"""
    log_function_entry(logger, "get_authorization_url", redirect_uri=redirect_uri, state=state)
    
    client_id_str = os.environ.get("STRAVA_CLIENT_ID", "your_client_id_here")
    
    if not client_id_str or client_id_str == "your_client_id_here":
        error_msg = "STRAVA_CLIENT_ID environment variable is required"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        client_id = int(client_id_str)
    except (ValueError, TypeError) as e:
        error_msg = "STRAVA_CLIENT_ID must be a valid integer"
        log_error(logger, e, error_msg)
        raise ValueError(error_msg)
    
    try:
        client = Client()
        # Set scopes for read access and activity reading
        scopes = ["read", "activity:read_all"]
        
        auth_url = client.authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            approval_prompt="force",
            scope=scopes,
            state=state
        )
        
        logger.info(f"Generated authorization URL for client ID: {client_id}")
        log_function_exit(logger, "get_authorization_url", "Success")
        return auth_url
        
    except Exception as e:
        log_error(logger, e, "Failed to generate authorization URL")
        raise

def exchange_code_for_token(authorization_code, redirect_uri):
    """Exchange authorization code for access token using Swagger client"""
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    if not client_secret:
        raise ValueError("STRAVA_CLIENT_SECRET environment variable is required")
    
    client_id_str = os.environ.get("STRAVA_CLIENT_ID", "your_client_id_here")
    if not client_id_str or client_id_str == "your_client_id_here":
        raise ValueError("STRAVA_CLIENT_ID environment variable is required")
    
    try:
        client_id = int(client_id_str)
    except (ValueError, TypeError):
        raise ValueError("STRAVA_CLIENT_ID must be a valid integer")
    
    client = Client()
    
    try:
        access_info = client.exchange_code_for_token(
            client_id=client_id,
            client_secret=client_secret,
            code=authorization_code
        )
        
        # Convert to dict format for compatibility
        return {
            "access_token": access_info.access_token,
            "refresh_token": access_info.refresh_token,
            "expires_at": access_info.expires_at
        }
    except Exception as e:
        raise Exception(f"Failed to exchange code for token: {e}")

def refresh_access_token(refresh_token):
    """Refresh an expired access token using Swagger client"""
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
    if not client_secret:
        raise ValueError("STRAVA_CLIENT_SECRET environment variable is required")
    
    client_id_str = os.environ.get("STRAVA_CLIENT_ID", "your_client_id_here")
    if not client_id_str or client_id_str == "your_client_id_here":
        raise ValueError("STRAVA_CLIENT_ID environment variable is required")
    
    try:
        client_id = int(client_id_str)
    except (ValueError, TypeError):
        raise ValueError("STRAVA_CLIENT_ID must be a valid integer")
    
    client = Client()
    
    try:
        access_info = client.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token
        )
        
        # Convert to dict format for compatibility
        return {
            "access_token": access_info.access_token,
            "refresh_token": access_info.refresh_token,
            "expires_at": access_info.expires_at
        }
    except Exception as e:
        raise Exception(f"Failed to refresh access token: {e}")

def get_athlete(access_token=None):
    """Get athlete information using Swagger client"""
    log_function_entry(logger, "get_athlete", access_token=bool(access_token))
    
    # Get legacy token dynamically to support runtime environment changes
    legacy_token = os.environ.get("STRAVA_ACCESS_TOKEN")
    token = access_token or legacy_token
    if not token:
        error_msg = "No access token available"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        client = Client(access_token=token)
        athlete = client.get_athlete()
        
        # Convert the athlete object to dict for compatibility
        # The stravalib models have to_dict() method or we can access attributes
        athlete_data = {
            'id': athlete.id,
            'username': getattr(athlete, 'username', None),
            'firstname': getattr(athlete, 'firstname', ''),
            'lastname': getattr(athlete, 'lastname', ''),
            'city': getattr(athlete, 'city', ''),
            'state': getattr(athlete, 'state', ''),
            'country': getattr(athlete, 'country', ''),
            'sex': getattr(athlete, 'sex', ''),
            'profile': getattr(athlete, 'profile', ''),
            'profile_medium': getattr(athlete, 'profile_medium', ''),
            'follower_count': getattr(athlete, 'follower_count', 0),
            'friend_count': getattr(athlete, 'friend_count', 0),
        }
        
        athlete_name = f"{athlete_data.get('firstname', '')} {athlete_data.get('lastname', '')}".strip()
        logger.info(f"Successfully retrieved athlete data for: {athlete_name or 'Unknown Athlete'}")
        log_function_exit(logger, "get_athlete", "Success")
        
        return athlete_data
        
    except AccessUnauthorized as e:
        error_msg = "Access token is invalid or expired"
        log_error(logger, e, error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        log_error(logger, e, "Failed to get athlete information")
        raise Exception(f"Failed to get athlete information: {e}")

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
