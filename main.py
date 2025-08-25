import streamlit as st
import os
import requests
from strava_connect import get_authorization_url, exchange_code_for_tokens, get_athlete

def read_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading README.md: {e}"

# Initialize session state
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'refresh_token' not in st.session_state:
    st.session_state.refresh_token = None
if 'athlete_data' not in st.session_state:
    st.session_state.athlete_data = None

# Get redirect URI - dynamically determine based on environment
def get_redirect_uri():
    """
    Determine the correct redirect URI based on the deployment environment.
    Returns localhost for local development, kompass-dev.streamlit.app for Streamlit Cloud.
    """
    # Allow explicit override via environment variable
    override_uri = os.environ.get('STRAVA_REDIRECT_URI')
    if override_uri:
        return override_uri
    
    # Auto-detect based on common environment characteristics
    # Method 1: Check for Streamlit Cloud indicators
    is_cloud = any([
        # Check if we're running on a typical cloud deployment
        os.environ.get('USER') == 'appuser',  # Streamlit Cloud default user
        '/app' in os.environ.get('HOME', ''),  # Streamlit Cloud default home
        'DYNO' in os.environ,  # Heroku-style deployment
        'RENDER' in os.environ,  # Render deployment
        'STREAMLIT_CLOUD' in os.environ,  # Explicit cloud indicator
    ])
    
    if is_cloud:
        return "https://kompass-dev.streamlit.app"
    
    # Default to localhost for local development
    return "http://localhost:8501"

REDIRECT_URI = get_redirect_uri()

st.title("KOMpass - Strava API App")

# Check if we have authorization code in URL parameters
query_params = st.query_params
if 'code' in query_params and not st.session_state.access_token:
    code = query_params['code']
    try:
        # Exchange code for tokens
        token_response = exchange_code_for_tokens(code, REDIRECT_URI)
        st.session_state.access_token = token_response['access_token']
        st.session_state.refresh_token = token_response['refresh_token']
        
        # Clear the code from URL to prevent reuse
        st.query_params.clear()
        st.rerun()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            st.error("❌ **403 Forbidden Error**")
            st.error("This error typically occurs when:")
            st.markdown("""
            - **Redirect URI mismatch**: Your Strava app's redirect URI doesn't match `http://localhost:8501`
            - **Invalid client credentials**: Check your `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET`
            - **App not approved**: Your Strava application might need approval
            - **Scope issues**: The requested permissions might not be allowed
            
            **To fix this:**
            1. Go to https://www.strava.com/settings/api
            2. Edit your application
            3. Set the "Authorization Callback Domain" to: `localhost`
            4. Ensure your app is approved for the requested scopes
            """)
        else:
            st.error(f"HTTP Error {e.response.status_code}: {e}")
        st.error("Please check your Strava app configuration and try again.")
    except Exception as e:
        st.error(f"Error exchanging code for tokens: {e}")
        st.error("Please check your Strava app configuration and try again.")

# Handle error parameter from OAuth callback
if 'error' in query_params:
    error = query_params.get('error')
    error_description = query_params.get('error_description', '')
    st.error(f"❌ OAuth Error: {error}")
    if error_description:
        st.error(f"Description: {error_description}")
    
    if error == 'access_denied':
        st.info("You denied access to the application. Click 'Connect with Strava' to try again.")

# Check if user is authenticated
if st.session_state.access_token:
    st.success("✅ Connected to Strava!")
    
    # Fetch athlete data if we don't have it
    if not st.session_state.athlete_data:
        try:
            st.session_state.athlete_data = get_athlete(st.session_state.access_token)
        except Exception as e:
            st.error(f"Error fetching athlete info: {e}")
            # Clear tokens if they're invalid
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.session_state.athlete_data = None
            st.rerun()
    
    # Display athlete information
    if st.session_state.athlete_data:
        athlete = st.session_state.athlete_data
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Athlete Information")
            st.write(f"**Name:** {athlete.get('firstname', 'N/A')} {athlete.get('lastname', 'N/A')}")
            st.write(f"**Username:** {athlete.get('username', 'N/A')}")
            st.write(f"**Country:** {athlete.get('country', 'N/A')}")
            st.write(f"**Sex:** {athlete.get('sex', 'N/A')}")
            
        with col2:
            if athlete.get('profile_medium'):
                st.image(athlete['profile_medium'], caption="Profile Picture", width=150)
        
        # Logout button
        if st.button("Disconnect from Strava"):
            st.session_state.access_token = None
            st.session_state.refresh_token = None
            st.session_state.athlete_data = None
            st.rerun()
    
else:
    # User not authenticated - show login
    st.info("Connect your Strava account to get started with KOMpass!")
    
    # Check if required environment variables are set
    client_id = os.environ.get("STRAVA_CLIENT_ID")
    if not client_id:
        st.error("❌ STRAVA_CLIENT_ID environment variable is not set. Please configure it in your app settings.")
        st.stop()
    
    # Generate authorization URL
    auth_url = get_authorization_url(
        redirect_uri=REDIRECT_URI,
        scope="read,activity:read_all"  # Adjust scopes as needed
    )
    
    st.markdown(f"[🔗 Connect with Strava]({auth_url})", unsafe_allow_html=True)
    
    # Instructions for redirect URI
    st.markdown("---")
    st.subheader("Setup Instructions")
    
    # Show current environment and redirect URI
    environment = "Streamlit Cloud" if "streamlit.app" in REDIRECT_URI else "Local Development"
    st.info(f"🌐 **Current Environment:** {environment}")
    st.info(f"🔗 **Current Redirect URI:** `{REDIRECT_URI}`")
    
    st.markdown(f"""
    **Environment Variable Override:**
    - Set `STRAVA_REDIRECT_URI` to explicitly specify the redirect URI (overrides auto-detection)
    
    **For local development:**
    1. Go to [Strava API Settings](https://www.strava.com/settings/api)
    2. Create a new app or edit your existing app
    3. Set the **Authorization Callback Domain** to: `localhost`
    4. Set these environment variables:
       - `STRAVA_CLIENT_ID` (from your Strava app)
       - `STRAVA_CLIENT_SECRET` (from your Strava app)
       - `STRAVA_REDIRECT_URI=http://localhost:8501` (optional, will auto-detect)
    
    **For production deployment (Streamlit Cloud):**
    1. Go to [Strava API Settings](https://www.strava.com/settings/api)
    2. Edit your existing app
    3. Set the **Authorization Callback Domain** to: `kompass-dev.streamlit.app`
    4. Set the environment variables in your Streamlit app settings:
       - `STRAVA_CLIENT_ID` (from your Strava app)
       - `STRAVA_CLIENT_SECRET` (from your Strava app)
       - `STRAVA_REDIRECT_URI=https://kompass-dev.streamlit.app` (optional, will auto-detect)
    
    **Common 403 Error Solutions:**
    - Ensure the redirect URI in your Strava app matches the current environment
    - Make sure your Strava app is approved
    - Check that your client ID and secret are correct
    - For Streamlit Cloud: ensure the domain is set to `kompass-dev.streamlit.app`
    - For local development: ensure the domain is set to `localhost`
    - Use `STRAVA_REDIRECT_URI` environment variable to override auto-detection if needed
    """)

# Show README content
st.markdown("---")
st.subheader("About KOMpass")
readme_content = read_readme()
st.markdown(readme_content)