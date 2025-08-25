"""
Authentication manager for Strava OAuth integration.
Handles OAuth flow, token management, and user session state.
"""

import streamlit as st
from typing import Dict, Optional, Any
from strava_oauth import StravaOAuth
from config import get_config
from logging_config import get_logger, log_function_entry, log_function_exit, log_error

logger = get_logger(__name__)


class AuthenticationManager:
    """Manages Strava authentication state and OAuth flow."""
    
    def __init__(self):
        """Initialize authentication manager."""
        log_function_entry(logger, "__init__")
        self.config = get_config()
        self.oauth_client = None
        
        # Initialize OAuth client if Strava is configured
        if self.config.is_strava_configured():
            try:
                self.oauth_client = StravaOAuth()
                logger.info("StravaOAuth client initialized successfully")
            except Exception as e:
                log_error(logger, e, "Failed to initialize StravaOAuth client")
                self.oauth_client = None
        else:
            logger.warning("Strava not configured - OAuth client not initialized")
        
        log_function_exit(logger, "__init__")
    
    def initialize_session_state(self):
        """Initialize authentication-related session state variables."""
        log_function_entry(logger, "initialize_session_state")
        
        if "authenticated" not in st.session_state:
            st.session_state["authenticated"] = False
            logger.debug("Initialized authenticated state to False")
        
        if "access_token" not in st.session_state:
            st.session_state["access_token"] = None
            logger.debug("Initialized access_token to None")
        
        if "refresh_token" not in st.session_state:
            st.session_state["refresh_token"] = None
            logger.debug("Initialized refresh_token to None")
        
        if "expires_at" not in st.session_state:
            st.session_state["expires_at"] = None
            logger.debug("Initialized expires_at to None")
        
        if "athlete_info" not in st.session_state:
            st.session_state["athlete_info"] = None
            logger.debug("Initialized athlete_info to None")
        
        log_function_exit(logger, "initialize_session_state")
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        authenticated = (
            st.session_state.get("authenticated", False) and 
            st.session_state.get("access_token") is not None
        )
        
        if authenticated:
            logger.debug("User is authenticated")
        else:
            logger.debug("User is not authenticated")
        
        return authenticated
    
    def is_oauth_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        configured = self.oauth_client is not None and self.config.is_strava_configured()
        
        if not configured:
            logger.warning("OAuth is not properly configured")
        
        return configured
    
    def get_authorization_url(self) -> Optional[str]:
        """Get Strava authorization URL."""
        log_function_entry(logger, "get_authorization_url")
        
        if not self.is_oauth_configured():
            logger.error("Cannot get authorization URL - OAuth not configured")
            return None
        
        try:
            redirect_uri = self.config.strava.get_redirect_uri()
            auth_url = self.oauth_client.get_authorization_url(redirect_uri)
            
            logger.info(f"Generated authorization URL with redirect URI: {redirect_uri}")
            log_function_exit(logger, "get_authorization_url", "URL generated")
            
            return auth_url
            
        except Exception as e:
            log_error(logger, e, "Failed to generate authorization URL")
            return None
    
    def handle_oauth_callback(self):
        """Handle OAuth callback and exchange code for token."""
        log_function_entry(logger, "handle_oauth_callback")
        
        query_params = st.query_params
        logger.debug(f"Processing query params: {list(query_params.keys())}")
        
        if "code" in query_params:
            authorization_code = query_params["code"]
            logger.info("Received authorization code from Strava")
            
            try:
                if not self.is_oauth_configured():
                    raise Exception("OAuth not properly configured")
                
                # Exchange code for token
                redirect_uri = self.config.strava.get_redirect_uri()
                token_data = self.oauth_client.exchange_code_for_token(authorization_code, redirect_uri)
                
                logger.info("Successfully exchanged authorization code for tokens")
                
                # Store tokens in session state
                st.session_state["access_token"] = token_data["access_token"]
                st.session_state["refresh_token"] = token_data["refresh_token"]
                st.session_state["expires_at"] = token_data["expires_at"]
                st.session_state["authenticated"] = True
                
                # Get athlete info immediately
                self._fetch_athlete_info()
                
                # Clear query parameters
                st.query_params.clear()
                st.rerun()
                
                logger.info("OAuth callback handled successfully")
                
            except Exception as e:
                log_error(logger, e, "Error during OAuth token exchange")
                st.error(f"Authentication error: {e}")
                self.logout()
        
        elif "error" in query_params:
            error = query_params.get("error", "Unknown error")
            logger.warning(f"OAuth error received: {error}")
            st.error(f"Authentication error: {error}")
            self.logout()
        
        log_function_exit(logger, "handle_oauth_callback")
    
    def _fetch_athlete_info(self):
        """Fetch and cache athlete information."""
        log_function_entry(logger, "_fetch_athlete_info")
        
        if not self.is_authenticated() or not self.is_oauth_configured():
            logger.warning("Cannot fetch athlete info - not authenticated or OAuth not configured")
            return
        
        try:
            access_token = st.session_state["access_token"]
            athlete_info = self.oauth_client.get_athlete(access_token)
            
            st.session_state["athlete_info"] = athlete_info
            
            athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
            logger.info(f"Fetched athlete info for: {athlete_name or 'Unknown Athlete'}")
            
            log_function_exit(logger, "_fetch_athlete_info", "Success")
            
        except Exception as e:
            log_error(logger, e, "Failed to fetch athlete information")
            # Don't logout on athlete info failure, but clear cached info
            st.session_state["athlete_info"] = None
    
    def get_athlete_info(self) -> Optional[Dict[str, Any]]:
        """Get cached athlete information."""
        if not self.is_authenticated():
            return None
        
        athlete_info = st.session_state.get("athlete_info")
        
        # If no cached info, try to fetch it
        if athlete_info is None:
            self._fetch_athlete_info()
            athlete_info = st.session_state.get("athlete_info")
        
        return athlete_info
    
    def refresh_access_token(self) -> bool:
        """Refresh expired access token."""
        log_function_entry(logger, "refresh_access_token")
        
        if not self.is_oauth_configured():
            logger.error("Cannot refresh token - OAuth not configured")
            return False
        
        refresh_token = st.session_state.get("refresh_token")
        if not refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            token_data = self.oauth_client.refresh_access_token(refresh_token)
            
            # Update session state with new tokens
            st.session_state["access_token"] = token_data["access_token"]
            st.session_state["refresh_token"] = token_data["refresh_token"]
            st.session_state["expires_at"] = token_data["expires_at"]
            
            logger.info("Access token refreshed successfully")
            log_function_exit(logger, "refresh_access_token", "Success")
            return True
            
        except Exception as e:
            log_error(logger, e, "Failed to refresh access token")
            self.logout()
            return False
    
    def logout(self):
        """Clear authentication state and log out user."""
        log_function_entry(logger, "logout")
        
        # Clear all authentication-related session state
        auth_keys = ["access_token", "refresh_token", "expires_at", "authenticated", "athlete_info"]
        
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        logger.info("User logged out - session state cleared")
        log_function_exit(logger, "logout")
    
    def render_authentication_ui(self):
        """Render authentication UI components."""
        log_function_entry(logger, "render_authentication_ui")
        
        if not self.is_oauth_configured():
            st.error("⚠️ Strava API not configured")
            st.info("Please check your Strava API configuration in environment variables.")
            
            with st.expander("🔧 Configuration Help"):
                st.markdown("""
                **Required Environment Variables:**
                - `STRAVA_CLIENT_ID`: Your Strava application client ID
                - `STRAVA_CLIENT_SECRET`: Your Strava application client secret
                
                **Optional Environment Variables:**
                - `STRAVA_REDIRECT_URI_DEV`: Development redirect URI (default: http://localhost:8501)
                - `STRAVA_REDIRECT_URI_PROD`: Production redirect URI (default: https://kompass-dev.streamlit.app)
                """)
            return
        
        if self.is_authenticated():
            self._render_authenticated_ui()
        else:
            self._render_login_ui()
        
        log_function_exit(logger, "render_authentication_ui")
    
    def _render_authenticated_ui(self):
        """Render UI for authenticated users."""
        athlete_info = self.get_athlete_info()
        
        if athlete_info:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
                st.success(f"✅ Connected to Strava as **{athlete_name or 'Unknown Athlete'}**")
            
            with col2:
                if st.button("🚪 Logout", type="secondary"):
                    self.logout()
                    st.rerun()
            
            # Display athlete details in expander
            with st.expander("👤 Athlete Information"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Username:** {athlete_info.get('username', 'N/A')}")
                    st.write(f"**Country:** {athlete_info.get('country', 'N/A')}")
                    st.write(f"**Sex:** {athlete_info.get('sex', 'N/A')}")
                
                with col2:
                    if athlete_info.get('profile'):
                        st.markdown(f"**Profile:** [View on Strava]({athlete_info.get('profile')})")
                    
                    if athlete_info.get('follower_count') is not None:
                        st.write(f"**Followers:** {athlete_info.get('follower_count', 0)}")
                    
                    if athlete_info.get('friend_count') is not None:
                        st.write(f"**Following:** {athlete_info.get('friend_count', 0)}")
                
                # Display profile picture if available
                if athlete_info.get('profile_medium'):
                    st.image(athlete_info.get('profile_medium'), width=100, caption="Profile Picture")
        
        else:
            st.warning("⚠️ Authenticated but unable to fetch athlete information")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("🔄 Retry Athlete Info"):
                    self._fetch_athlete_info()
                    st.rerun()
            
            with col2:
                if st.button("🚪 Logout", type="secondary"):
                    self.logout()
                    st.rerun()
    
    def _render_login_ui(self):
        """Render UI for login."""
        auth_url = self.get_authorization_url()
        
        if auth_url:
            st.markdown(f"""
            <a href="{auth_url}" target="_self">
                <button style="
                    background-color: #fc4c02;
                    color: white;
                    padding: 12px 24px;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: background-color 0.3s;
                ">
                    🚴 Connect with Strava
                </button>
            </a>
            """, unsafe_allow_html=True)
            
            st.info("👆 Click the button above to authorize KOMpass to access your Strava data.")
            
            # Instructions
            with st.expander("ℹ️ What happens when you connect?"):
                st.markdown("""
                1. You'll be redirected to Strava's authorization page
                2. You'll need to log in to Strava (if not already logged in)
                3. You'll be asked to authorize KOMpass to access your data
                4. After authorization, you'll be redirected back here
                5. Your athlete information will be displayed
                
                **We only request permission to read your basic profile and activity data.**
                
                **Data Privacy:** Your data stays secure and is only used within this application.
                """)
        
        else:
            st.error("❌ Unable to generate authorization URL")
            st.info("Please check the application configuration.")


# Global authentication manager instance
auth_manager = AuthenticationManager()


def get_auth_manager() -> AuthenticationManager:
    """Get the global authentication manager instance."""
    return auth_manager


if __name__ == "__main__":
    # Test the authentication manager
    from logging_config import setup_logging
    
    setup_logging("DEBUG")
    
    auth = get_auth_manager()
    
    print("=== Authentication Manager Test ===")
    print(f"OAuth configured: {auth.is_oauth_configured()}")
    print(f"Currently authenticated: {auth.is_authenticated()}")
    
    if auth.is_oauth_configured():
        auth_url = auth.get_authorization_url()
        print(f"Auth URL available: {auth_url is not None}")
    
    print("\n✅ Authentication manager test completed")