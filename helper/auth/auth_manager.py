"""
Authentication manager for Strava OAuth integration.
Handles OAuth flow, token management, and user session state.
"""

import os
import streamlit as st
from typing import Dict, Optional, Any
from .strava_oauth import StravaOAuth
from ..config.config import get_config
from ..config.logging_config import get_logger, log_function_entry, log_function_exit, log_error
from ..processing.rider_data_processor import RiderDataProcessor

logger = get_logger(__name__)


class AuthenticationManager:
    """Manages Strava authentication state and OAuth flow."""
    
    def __init__(self):
        """Initialize authentication manager."""
        log_function_entry(logger, "__init__")
        self.config = get_config()
        self.oauth_client = None
        self.rider_data_processor = None
        
        # Initialize OAuth client if Strava is configured
        if self.config.is_strava_configured():
            try:
                self.oauth_client = StravaOAuth()
                self.rider_data_processor = RiderDataProcessor(self.oauth_client)
                logger.info("StravaOAuth client and rider data processor initialized successfully")
            except Exception as e:
                log_error(logger, e, "Failed to initialize StravaOAuth client or rider data processor")
                self.oauth_client = None
                self.rider_data_processor = None
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
        
        if "rider_fitness_data" not in st.session_state:
            st.session_state["rider_fitness_data"] = None
            logger.debug("Initialized rider_fitness_data to None")
        
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
        """Fetch and cache athlete information and comprehensive rider data."""
        log_function_entry(logger, "_fetch_athlete_info")
        
        if not self.is_authenticated() or not self.is_oauth_configured():
            logger.warning("Cannot fetch athlete info - not authenticated or OAuth not configured")
            return
        
        try:
            access_token = st.session_state["access_token"]
            
            # Fetch basic athlete info (existing functionality)
            athlete_info = self.oauth_client.get_athlete(access_token)
            st.session_state["athlete_info"] = athlete_info
            
            athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
            logger.info(f"Fetched athlete info for: {athlete_name or 'Unknown Athlete'}")
            
            # Fetch comprehensive rider fitness data (new functionality)
            if self.rider_data_processor:
                logger.info("Fetching comprehensive rider fitness data")
                try:
                    rider_data = self.rider_data_processor.fetch_comprehensive_rider_data(access_token)
                    st.session_state["rider_fitness_data"] = rider_data
                    logger.info("Successfully fetched and cached comprehensive rider fitness data")
                except Exception as e:
                    log_error(logger, e, "Failed to fetch comprehensive rider data")
                    # Don't fail the whole authentication if rider data fails
                    st.session_state["rider_fitness_data"] = None
            else:
                logger.warning("Rider data processor not available - skipping comprehensive data fetch")
            
            log_function_exit(logger, "_fetch_athlete_info", "Success")
            
        except Exception as e:
            log_error(logger, e, "Failed to fetch athlete information")
            # Don't logout on athlete info failure, but clear cached info
            st.session_state["athlete_info"] = None
            st.session_state["rider_fitness_data"] = None
    
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
    
    def get_rider_fitness_data(self) -> Optional[Dict[str, Any]]:
        """Get cached comprehensive rider fitness data."""
        if not self.is_authenticated():
            return None
        
        rider_data = st.session_state.get("rider_fitness_data")
        
        # If no cached data, try to fetch it
        if rider_data is None:
            self._fetch_athlete_info()  # This will fetch both athlete info and rider data
            rider_data = st.session_state.get("rider_fitness_data")
        
        return rider_data
    
    def get_rider_ml_features(self) -> Optional[Dict[str, Any]]:
        """Get engineered features for ML applications."""
        if not self.is_authenticated() or not self.rider_data_processor:
            return None
        
        rider_data = self.get_rider_fitness_data()
        if not rider_data:
            return None
        
        try:
            features = self.rider_data_processor.get_feature_engineering_data(rider_data)
            logger.info(f"Generated {len(features)} ML features for rider")
            return features
        except Exception as e:
            log_error(logger, e, "Failed to generate ML features")
            return None
    
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
        auth_keys = ["access_token", "refresh_token", "expires_at", "authenticated", "athlete_info", "rider_fitness_data"]
        
        for key in auth_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        logger.info("User logged out - session state cleared")
        log_function_exit(logger, "logout")
    
    def render_authentication_ui(self):
        """Render the appropriate authentication UI based on current state."""
        log_function_entry(logger, "render_authentication_ui")
        
        if not self.is_oauth_configured():
            st.error("❌ Strava OAuth not configured")
            st.info("Please configure your Strava credentials to use authentication features.")
            log_function_exit(logger, "render_authentication_ui")
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
            
            # Display rider fitness data
            self._render_rider_fitness_data()
        
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
    
    def _render_rider_fitness_data(self):
        """Render comprehensive rider fitness data."""
        try:
            rider_data = self.get_rider_fitness_data()
            
            if rider_data:
                with st.expander("🏃‍♂️ Rider Fitness Data", expanded=True):
                    st.info("📊 Comprehensive fitness data collected from your Strava profile")
                    
                    # Power Analysis
                    if rider_data.get("power_analysis"):
                        st.subheader("⚡ Power Analysis")
                        power_analysis = rider_data["power_analysis"]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if power_analysis.get("recent_power_metrics"):
                                recent_power = power_analysis["recent_power_metrics"]
                                st.metric(
                                    "Avg Power (30 days)", 
                                    f"{recent_power.get('avg_power_last_30_days', 0):.0f}W" if recent_power.get('avg_power_last_30_days') else "N/A"
                                )
                                st.metric(
                                    "Max Power (30 days)", 
                                    f"{recent_power.get('max_power_last_30_days', 0):.0f}W" if recent_power.get('max_power_last_30_days') else "N/A"
                                )
                        
                        with col2:
                            if power_analysis.get("lifetime_stats"):
                                lifetime = power_analysis["lifetime_stats"]
                                st.metric("Total Rides", f"{lifetime.get('total_rides', 0):,}")
                                st.metric("Total Distance", f"{lifetime.get('total_distance_km', 0):.0f} km")
                    
                    # Fitness Metrics
                    if rider_data.get("fitness_metrics"):
                        st.subheader("💪 Fitness Metrics")
                        fitness = rider_data["fitness_metrics"]
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            freq = fitness.get("activity_frequency", {})
                            st.metric(
                                "Activities/Week", 
                                f"{freq.get('activities_per_week', 0):.1f}" if freq.get('activities_per_week') else "N/A"
                            )
                        
                        with col2:
                            st.metric(
                                "Training Consistency", 
                                f"{fitness.get('training_consistency', 0):.1%}"
                            )
                        
                        with col3:
                            st.metric(
                                "Total Activities", 
                                f"{fitness.get('total_activities', 0)}"
                            )
                    
                    # Training Load
                    if rider_data.get("training_load"):
                        st.subheader("📈 Training Load")
                        load = rider_data["training_load"]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            weekly_hours = load.get("weekly_training_hours", {})
                            st.metric(
                                "Avg Weekly Hours", 
                                f"{weekly_hours.get('avg_weekly_hours', 0):.1f}h" if weekly_hours.get('avg_weekly_hours') else "N/A"
                            )
                        
                        with col2:
                            tsb = load.get("training_stress_balance", {})
                            st.metric(
                                "Training Stress Balance", 
                                f"{tsb.get('training_stress_balance', 0):.1f}" if tsb.get('training_stress_balance') else "N/A"
                            )
                    
                    # ML Features Preview
                    ml_features = self.get_rider_ml_features()
                    if ml_features:
                        with st.expander("🤖 ML Features (Preview)"):
                            st.write("Features engineered for machine learning applications:")
                            
                            # Display key features in a nice format
                            feature_cols = st.columns(2)
                            col_idx = 0
                            
                            for feature_name, value in ml_features.items():
                                if value is not None:
                                    with feature_cols[col_idx % 2]:
                                        if isinstance(value, float):
                                            st.write(f"**{feature_name.replace('_', ' ').title()}:** {value:.2f}")
                                        else:
                                            st.write(f"**{feature_name.replace('_', ' ').title()}:** {value}")
                                    col_idx += 1
                    
                    # Data freshness
                    fetch_time = rider_data.get("fetch_timestamp")
                    if fetch_time:
                        st.caption(f"Data last updated: {fetch_time}")
            
            else:
                with st.expander("🏃‍♂️ Rider Fitness Data"):
                    st.warning("⚠️ Rider fitness data not yet available")
                    if st.button("🔄 Fetch Rider Data"):
                        # Force refresh of rider data
                        st.session_state["rider_fitness_data"] = None
                        self._fetch_athlete_info()
                        st.rerun()
                    st.info("📝 This feature fetches comprehensive fitness data from your Strava profile including power metrics, training load, and fitness trends.")
        
        except Exception as e:
            log_error(logger, e, "Error rendering rider fitness data")
            with st.expander("🏃‍♂️ Rider Fitness Data"):
                st.error("❌ Error loading rider fitness data")
                st.exception(e)
    
    def _render_login_ui(self):
        """Render UI for login."""
        auth_url = self.get_authorization_url()
        
        if auth_url:
            # Use st.link_button instead of custom HTML button
            st.link_button(
                "🚴 Connect with Strava",
                auth_url,
                help="Authorize KOMpass to access your Strava data",
                type="primary"
            )
            
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
            
            # Debug information for troubleshooting
            with st.expander("🔧 OAuth Configuration Debug Info"):
                redirect_uri = self.config.strava.get_redirect_uri()
                st.markdown(f"""
                **Current Configuration:**
                - Redirect URI: `{redirect_uri}`
                - Client ID: `{self.config.strava.client_id[:8] if len(self.config.strava.client_id) > 8 else self.config.strava.client_id}...`
                - Environment: `{os.environ.get('STREAMLIT_ENV', 'production')}`
                
                **If you're getting 403 errors:**
                1. Go to [Strava API Settings](https://www.strava.com/settings/api)
                2. Set "Authorization Callback Domain" to:
                   - For localhost: `localhost`
                   - For production: `kompass-dev.streamlit.app`
                3. Make sure the domain matches exactly (no http/https prefix, no trailing slash)
                4. The domain must match the redirect URI being used above
                
                **Common Issues:**
                - Domain mismatch between Strava settings and redirect URI
                - Missing or incorrect environment variables
                - Using wrong Client ID or Client Secret
                """)
                
        else:
            st.error("❌ Unable to generate authorization URL")
            st.info("Please check the application configuration.")
            
            # Show configuration help
            with st.expander("🔧 Configuration Help"):
                st.markdown("""
                **Required Environment Variables:**
                - `STRAVA_CLIENT_ID`: Your Strava application's Client ID
                - `STRAVA_CLIENT_SECRET`: Your Strava application's Client Secret
                
                **Optional Environment Variables:**
                - `STREAMLIT_ENV=development`: Set for local development
                - `STRAVA_REDIRECT_URI_LOCAL`: Override local redirect URI
                - `STRAVA_REDIRECT_URI_PROD`: Override production redirect URI
                
                **Get your Strava API credentials:**
                1. Go to [Strava API Settings](https://www.strava.com/settings/api)
                2. Create a new application or use an existing one
                3. Copy the Client ID and Client Secret
                4. Set the Authorization Callback Domain appropriately
                """)


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
