#!/usr/bin/env python3
"""
OAuth Configuration Verification Script

This script helps verify your Strava OAuth configuration and identify potential issues
that could cause the 403 error during authentication.

Usage:
    python verify_oauth_config.py

Make sure to set your environment variables first:
    export STRAVA_CLIENT_ID=your_client_id_here
    export STRAVA_CLIENT_SECRET=your_client_secret_here
    export STREAMLIT_ENV=development  # Optional, for local development
"""

import os
import sys

# Add the root directory to Python path for importing
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from helper.config.config import get_config
from helper.auth.strava_oauth import StravaOAuth

def main():
    print("🔧 KOMpass OAuth Configuration Verification")
    print("=" * 50)
    
    try:
        # Load configuration
        config = get_config()
        
        print("\n📋 Current Configuration:")
        print(f"   Client ID: {config.strava.client_id}")
        print(f"   Client Secret: {'***' + config.strava.client_secret[-4:] if len(config.strava.client_secret) > 4 else '***'}")
        print(f"   Environment: {os.environ.get('STREAMLIT_ENV', 'production')}")
        print(f"   Redirect URI: {config.strava.get_redirect_uri()}")
        
        # Check if Strava is configured
        if not config.is_strava_configured():
            print("\n❌ CONFIGURATION ERROR:")
            print("   Strava OAuth is not properly configured.")
            print("   Please set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables.")
            return False
        
        print("\n✅ Basic configuration looks good!")
        
        # Test OAuth client initialization
        try:
            oauth = StravaOAuth()
            print("✅ OAuth client initialized successfully")
        except Exception as e:
            print(f"❌ OAuth client initialization failed: {e}")
            return False
        
        # Generate a test authorization URL
        try:
            redirect_uri = config.strava.get_redirect_uri()
            auth_url = oauth.get_authorization_url(redirect_uri)
            print(f"✅ Authorization URL generated successfully")
            print(f"   URL length: {len(auth_url)} characters")
        except Exception as e:
            print(f"❌ Failed to generate authorization URL: {e}")
            return False
        
        # Configuration recommendations
        print("\n🎯 Configuration Recommendations:")
        environment = os.environ.get('STREAMLIT_ENV', 'production')
        
        if environment == 'development':
            print("   📍 Development Environment Detected")
            print("   • In Strava API settings, set Authorization Callback Domain to: localhost")
            print("   • Make sure you're running the app on localhost:8501")
        else:
            print("   📍 Production Environment Detected")
            print("   • In Strava API settings, set Authorization Callback Domain to: kompass-dev.streamlit.app")
            print("   • Make sure your app is deployed to the correct domain")
        
        print("\n🔗 Important Links:")
        print("   • Strava API Settings: https://www.strava.com/settings/api")
        print("   • OAuth Troubleshooting Guide: ./OAUTH_TROUBLESHOOTING.md")
        
        print("\n✅ Configuration verification completed successfully!")
        print("   If you're still getting 403 errors, check the troubleshooting guide.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        print("   Please check your environment setup and try again.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)