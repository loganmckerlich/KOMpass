#!/usr/bin/env python3
"""
Test script for Strava OAuth implementation.
This script helps test the OAuth flow components.
"""

import os
from strava_connect import get_authorization_url, exchange_code_for_tokens

def test_oauth_url_generation():
    """Test OAuth URL generation"""
    print("Testing OAuth URL generation...")
    
    # Set test environment variables
    os.environ['STRAVA_CLIENT_ID'] = 'test_client_id'
    
    redirect_uri = 'http://localhost:8501'
    scope = 'read,activity:read_all'
    
    try:
        url = get_authorization_url(redirect_uri, scope)
        print(f"✅ OAuth URL generated successfully:")
        print(f"   {url}")
        print()
        
        # Verify URL components
        expected_components = [
            'https://www.strava.com/oauth/authorize',
            'client_id=test_client_id',
            'redirect_uri=http%3A%2F%2Flocalhost%3A8501',
            'response_type=code',
            'scope=read%2Cactivity%3Aread_all',
            'approval_prompt=auto'
        ]
        
        for component in expected_components:
            if component in url:
                print(f"✅ Found expected component: {component}")
            else:
                print(f"❌ Missing component: {component}")
        
    except Exception as e:
        print(f"❌ Error generating OAuth URL: {e}")

def test_environment_setup():
    """Test environment variable setup"""
    print("\nTesting environment setup...")
    
    client_id = os.environ.get('STRAVA_CLIENT_ID')
    client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
    
    if client_id:
        print(f"✅ STRAVA_CLIENT_ID is set: {client_id[:8]}...")
    else:
        print("❌ STRAVA_CLIENT_ID is not set")
    
    if client_secret:
        print(f"✅ STRAVA_CLIENT_SECRET is set: {client_secret[:8]}...")
    else:
        print("❌ STRAVA_CLIENT_SECRET is not set")

if __name__ == "__main__":
    print("KOMpass Strava OAuth Test")
    print("=" * 40)
    
    test_environment_setup()
    test_oauth_url_generation()
    
    print("\nSetup Instructions:")
    print("1. Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET environment variables")
    print("2. Configure your Strava app's redirect URI to: http://localhost:8501")
    print("3. Run: streamlit run main.py")
    print("4. Click 'Connect with Strava' to test the OAuth flow")