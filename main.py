import streamlit as st
from strava_oauth import StravaOAuth
import urllib.parse
import os

def read_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading README.md: {e}"

def handle_oauth_callback():
    """Handle OAuth callback and exchange code for token"""
    query_params = st.query_params
    
    if "code" in query_params:
        authorization_code = query_params["code"]
        try:
            # Initialize OAuth client
            oauth_client = StravaOAuth()
            
            # Exchange code for token
            redirect_uri = get_redirect_uri()
            token_data = oauth_client.exchange_code_for_token(authorization_code, redirect_uri)
            
            # Store tokens in session state
            st.session_state["access_token"] = token_data["access_token"]
            st.session_state["refresh_token"] = token_data["refresh_token"]
            st.session_state["expires_at"] = token_data["expires_at"]
            st.session_state["authenticated"] = True
            
            # Clear query parameters
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Error during authentication: {e}")
            st.session_state["authenticated"] = False
    
    elif "error" in query_params:
        st.error(f"Authentication error: {query_params['error']}")
        st.session_state["authenticated"] = False

def get_redirect_uri():
    """Get the redirect URI for OAuth"""
    # Check if we're running locally for development
    if os.environ.get("STREAMLIT_ENV") == "development":
        return "http://localhost:8501"
    
    # For production, use the actual deployed URL
    # This should match exactly what's configured in Strava API settings
    return "https://kompass-dev.streamlit.app"

def is_authenticated():
    """Check if user is authenticated"""
    return st.session_state.get("authenticated", False) and st.session_state.get("access_token")

def logout():
    """Clear authentication state"""
    for key in ["access_token", "refresh_token", "expires_at", "authenticated"]:
        if key in st.session_state:
            del st.session_state[key]

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

st.title("KOMpass README Viewer")
readme_content = read_readme()
st.markdown(readme_content)

# Handle OAuth callback
handle_oauth_callback()

# Authentication Section
st.header("Strava Authentication")

if is_authenticated():
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success("✅ Connected to Strava!")
    with col2:
        if st.button("Logout"):
            logout()
            st.rerun()
    
    # Strava Athlete Info Section
    st.header("Your Strava Information")
    try:
        # Initialize OAuth client and get athlete info
        oauth_client = StravaOAuth()
        access_token = st.session_state["access_token"]
        athlete = oauth_client.get_athlete(access_token)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
            st.write(f"**Username:** {athlete.get('username', 'N/A')}")
            st.write(f"**Country:** {athlete.get('country', 'N/A')}")
        with col2:
            st.write(f"**Sex:** {athlete.get('sex', 'N/A')}")
            if athlete.get('profile'):
                st.write(f"**Profile:** [View on Strava]({athlete.get('profile')})")
            
            # Display profile picture if available
            if athlete.get('profile_medium'):
                st.image(athlete.get('profile_medium'), width=100)
        
        # Display some activity stats
        if 'follower_count' in athlete:
            st.write(f"**Followers:** {athlete.get('follower_count', 0)}")
        if 'friend_count' in athlete:
            st.write(f"**Following:** {athlete.get('friend_count', 0)}")
            
    except Exception as e:
        st.error(f"Error fetching athlete info: {e}")
        if st.button("Try logging in again"):
            logout()
            st.rerun()

else:
    st.info("Connect your Strava account to view your athlete information.")
    
    try:
        # OAuth login button
        oauth_client = StravaOAuth()
        redirect_uri = get_redirect_uri()
        auth_url = oauth_client.get_authorization_url(redirect_uri)
        
        st.markdown(f"""
        <a href="{auth_url}" target="_self">
            <button style="
                background-color: #fc4c02;
                color: white;
                padding: 10px 20px;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            ">
                🚴 Connect with Strava
            </button>
        </a>
        """, unsafe_allow_html=True)
        
        st.info("👆 Click the button above to authorize KOMpass to access your Strava data.")
        
    except Exception as e:
        st.error(f"OAuth configuration error: {e}")
        st.info("Please check your Strava API configuration.")
    
    # Instructions
    with st.expander("ℹ️ What happens when you connect?"):
        st.write("""
        1. You'll be redirected to Strava's authorization page
        2. You'll need to log in to Strava (if not already logged in)
        3. You'll be asked to authorize KOMpass to access your data
        4. After authorization, you'll be redirected back here
        5. Your athlete information will be displayed
        
        **We only request permission to read your basic profile and activity data.**
        """)

# Show setup instructions if client ID is not configured
import os
if not os.environ.get("STRAVA_CLIENT_ID") or os.environ.get("STRAVA_CLIENT_ID") == "your_client_id_here":
    with st.expander("⚙️ Setup Instructions for Developers"):
        st.warning("Strava Client ID not configured!")
        st.write("""
        To enable Strava OAuth, you need to:
        
        1. Create a Strava API application at https://www.strava.com/settings/api
        2. Set the Authorization Callback Domain to match your app's domain
        3. Set the following environment variables:
           - `STRAVA_CLIENT_ID`: Your Strava application's Client ID
           - `STRAVA_CLIENT_SECRET`: Your Strava application's Client Secret
        
        For local development, you can create a `.env` file with these values.
        """)
