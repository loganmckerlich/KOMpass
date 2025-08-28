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
                    
                    # Store only essential rider fitness metrics to minimize session state usage
                    if rider_data and isinstance(rider_data, dict):
                        essential_metrics = self._extract_essential_fitness_metrics(rider_data)
                        st.session_state["rider_fitness_data"] = essential_metrics
                        logger.info("Successfully fetched and cached essential rider fitness data")
                    else:
                        st.session_state["rider_fitness_data"] = None
                        
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
    
    def get_oauth_client(self):
        """Get the OAuth client instance."""
        return self.oauth_client
    
    def get_access_token(self) -> Optional[str]:
        """Get the current access token from session state."""
        return st.session_state.get("access_token")
    
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
    
    def _extract_essential_fitness_metrics(self, rider_data: Dict) -> Dict:
        """Extract only essential fitness metrics to minimize session state usage."""
        essential_metrics = {}
        
        try:
            # Keep high-level summary data only
            if 'summary' in rider_data:
                essential_metrics['summary'] = rider_data['summary']
                
            # Keep recent performance trends (limit to last 10 activities)
            if 'recent_activities' in rider_data:
                recent = rider_data['recent_activities']
                if isinstance(recent, list) and len(recent) > 10:
                    essential_metrics['recent_activities'] = recent[-10:]
                else:
                    essential_metrics['recent_activities'] = recent
                    
            # Keep current fitness metrics only
            if 'current_fitness' in rider_data:
                essential_metrics['current_fitness'] = rider_data['current_fitness']
                
            # Keep weekly stats summary (not detailed daily data)
            if 'weekly_stats' in rider_data:
                weekly = rider_data['weekly_stats']
                if isinstance(weekly, dict):
                    essential_metrics['weekly_stats'] = {
                        'distance': weekly.get('distance'),
                        'elevation': weekly.get('elevation'),
                        'time': weekly.get('time'),
                        'activities': weekly.get('activities')
                    }
                    
            # Keep power/heart rate zones summary only (not detailed data)
            if 'power_zones' in rider_data:
                power_zones = rider_data['power_zones']
                if isinstance(power_zones, dict):
                    essential_metrics['power_zones'] = {
                        'ftp': power_zones.get('ftp'),
                        'zones': power_zones.get('zones', [])[:7]  # Standard 7 zones only
                    }
                    
            logger.debug(f"Extracted essential metrics from rider data: {len(essential_metrics)} categories")
            
        except Exception as e:
            logger.warning(f"Error extracting essential fitness metrics: {e}")
            # Return minimal data if extraction fails
            essential_metrics = {'summary': {'error': 'Data extraction failed'}}
            
        return essential_metrics

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
            self._render_unconfigured_ui()
            log_function_exit(logger, "render_authentication_ui")
            return
        
        if self.is_authenticated():
            self._render_authenticated_ui()
        else:
            self._render_login_ui()
        
        log_function_exit(logger, "render_authentication_ui")



    def _render_unconfigured_ui(self):
        """Render UI when Strava OAuth is not configured."""
        # Show a friendly placeholder button that looks like a sign-in button
        st.markdown("""
        <div style="
            background: linear-gradient(90deg, #FC4C02 0%, #FF6B35 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            padding: 0.5rem 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(252, 76, 2, 0.2);
            margin: 0.5rem 0;
            opacity: 0.7;
        ">
            🚴 Connect with Strava
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 Strava integration requires API credentials to be configured.")
        
        # Instructions for setup
        with st.expander("ℹ️ How to enable Strava integration"):
            st.markdown("""
            **To enable Strava integration:**
            
            1. Go to [Strava API Settings](https://www.strava.com/settings/api)
            2. Create a new application or use an existing one
            3. Copy your Client ID and Client Secret
            4. Set the following environment variables:
               - `STRAVA_CLIENT_ID=your_client_id`
               - `STRAVA_CLIENT_SECRET=your_client_secret`
            5. Set the Authorization Callback Domain to match your app's domain
            
            **Benefits of connecting Strava:**
            - Access your recent activities
            - Enhanced performance analysis
            - Personalized insights based on your cycling data
            """)

    def _render_authenticated_ui(self):
        """Render minimal UI for authenticated users."""
        athlete_info = self.get_athlete_info()
        
        if athlete_info:
            athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
            st.success(f"✅ Connected as **{athlete_name or 'Unknown Athlete'}**")
            
            # Simple logout button
            if st.button("🚪 Logout", type="secondary", use_container_width=True):
                self.logout()
                st.rerun()
            
            # Link to fitness page
            st.info("💡 Visit the **Rider Fitness** page to view your comprehensive fitness data and analytics.")
        
        else:
            st.warning("⚠️ Authenticated but unable to fetch athlete information")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 Retry", type="secondary"):
                    self._fetch_athlete_info()
                    st.rerun()
            
            with col2:
                if st.button("🚪 Logout", type="secondary"):
                    self.logout()
                    st.rerun()
    
    def _render_rider_fitness_data(self):
        """Render comprehensive rider fitness data with advanced metrics."""
        try:
            rider_data = self.get_rider_fitness_data()
            
            if rider_data:
                with st.expander("🏃‍♂️ Rider Fitness Data", expanded=True):
                    st.info("📊 Comprehensive fitness data collected from your Strava profile")
                    
                    # Create tabs for different metric categories
                    tab1, tab2, tab3, tab4, tab5 = st.tabs([
                        "⚡ Power & Performance", 
                        "🎯 Zone Analysis", 
                        "📈 Advanced Metrics", 
                        "🏁 Distance Performance",
                        "🤖 ML Features"
                    ])
                    
                    with tab1:
                        # Power Analysis
                        if rider_data.get("power_analysis"):
                            st.subheader("⚡ Power Analysis")
                            power_analysis = rider_data["power_analysis"]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Recent Performance (30 days)**")
                                if power_analysis.get("recent_power_metrics"):
                                    recent_power = power_analysis["recent_power_metrics"]
                                    st.metric(
                                        "Avg Power", 
                                        f"{recent_power.get('avg_power_last_30_days', 0):.0f}W" if recent_power.get('avg_power_last_30_days') else "N/A"
                                    )
                                    st.metric(
                                        "Max Power", 
                                        f"{recent_power.get('max_power_last_30_days', 0):.0f}W" if recent_power.get('max_power_last_30_days') else "N/A"
                                    )
                                    
                                    trend = recent_power.get('power_trend', {})
                                    trend_icon = "📈" if trend.get('trend_direction') == "improving" else "📉"
                                    st.metric(
                                        f"Power Trend {trend_icon}",
                                        f"{trend.get('trend_direction', 'Unknown').title()}"
                                    )
                            
                            with col2:
                                st.markdown("**Lifetime Statistics**")
                                if power_analysis.get("lifetime_stats"):
                                    lifetime = power_analysis["lifetime_stats"]
                                    st.metric("Total Rides", f"{lifetime.get('total_rides', 0):,}")
                                    st.metric("Total Distance", f"{lifetime.get('total_distance_km', 0):.0f} km")
                                    st.metric("Total Elevation", f"{lifetime.get('total_elevation_gain_m', 0):,.0f} m")
                        
                        # Critical Power Curve
                        if rider_data.get("advanced_metrics", {}).get("critical_power_curve"):
                            st.subheader("🔥 Critical Power Analysis")
                            cp_curve = rider_data["advanced_metrics"]["critical_power_curve"]
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                if cp_curve.get("critical_power_watts"):
                                    st.metric("Critical Power", f"{cp_curve['critical_power_watts']:.0f}W")
                            
                            with col2:
                                if cp_curve.get("w_prime_joules"):
                                    st.metric("W' (Anaerobic Capacity)", f"{cp_curve['w_prime_joules']:.0f}J")
                            
                            with col3:
                                classification = cp_curve.get("performance_classification", "Unknown")
                                st.metric("Performance Level", classification)
                        
                        # VO2 Max Estimation
                        if rider_data.get("advanced_metrics", {}).get("vo2_max_estimation"):
                            st.subheader("🫁 VO2 Max Estimation")
                            vo2_data = rider_data["advanced_metrics"]["vo2_max_estimation"]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if vo2_data.get("vo2_max_average"):
                                    st.metric("Estimated VO2 Max", f"{vo2_data['vo2_max_average']:.1f} ml/kg/min")
                            
                            with col2:
                                classification = vo2_data.get("vo2_classification", "Unknown")
                                st.metric("VO2 Classification", classification)
                    
                    with tab2:
                        # Zone Speed Predictions (Logan's key requirement!)
                        if rider_data.get("power_zone_analysis", {}).get("zone_speed_predictions"):
                            st.subheader("🚀 Zone Speed Predictions")
                            st.info("⏱️ Estimated ride times at different power zones - perfect for planning efforts!")
                            
                            speed_preds = rider_data["power_zone_analysis"]["zone_speed_predictions"]
                            
                            # Display zone predictions in a nice format
                            for zone_key, zone_data in speed_preds.items():
                                if zone_key.startswith("zone_") and isinstance(zone_data, dict):
                                    with st.expander(f"🎯 {zone_data.get('zone_name', zone_key)} - {zone_data.get('power_range_watts', 'N/A')}"):
                                        
                                        col1, col2 = st.columns(2)
                                        
                                        with col1:
                                            st.metric("Predicted Speed", f"{zone_data.get('predicted_speed_kmh', 0):.1f} km/h")
                                            st.metric("Confidence", zone_data.get('confidence_level', 'Unknown'))
                                        
                                        with col2:
                                            st.metric("Mid Power", f"{zone_data.get('mid_power_watts', 0):.0f}W")
                                            st.metric("Calibration Rides", f"{zone_data.get('calibration_rides', 0)}")
                                        
                                        # Distance time predictions
                                        if zone_data.get("distance_time_predictions"):
                                            st.markdown("**Estimated Ride Times:**")
                                            time_preds = zone_data["distance_time_predictions"]
                                            
                                            pred_cols = st.columns(min(3, len(time_preds)))
                                            for i, (distance, pred_data) in enumerate(time_preds.items()):
                                                if i < len(pred_cols):
                                                    with pred_cols[i]:
                                                        st.metric(
                                                            distance, 
                                                            pred_data.get('estimated_time_formatted', 'N/A')
                                                        )
                            
                            # Model quality info
                            if speed_preds.get("model_info"):
                                model_info = speed_preds["model_info"]
                                st.caption(f"📊 Based on {model_info.get('total_calibration_rides', 0)} calibration rides. "
                                         f"Data quality: {model_info.get('data_quality', 'Unknown')}")
                    
                    with tab3:
                        # Advanced Metrics
                        if rider_data.get("advanced_metrics"):
                            advanced = rider_data["advanced_metrics"]
                            
                            # Power Profile Classification
                            if advanced.get("power_profile"):
                                st.subheader("🏆 Power Profile Classification")
                                profile = advanced["power_profile"]
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    classification = profile.get("classification", "Unknown")
                                    st.metric("Rider Type", classification)
                                
                                with col2:
                                    if profile.get("sprint_to_ftp_ratio"):
                                        st.metric("Sprint:FTP Ratio", f"{profile['sprint_to_ftp_ratio']:.2f}")
                                
                                if profile.get("strengths"):
                                    st.markdown("**Key Strengths:**")
                                    for strength in profile["strengths"]:
                                        st.markdown(f"• {strength}")
                            
                            # Training Stress Analysis
                            if advanced.get("training_stress"):
                                st.subheader("📊 Training Stress Analysis")
                                stress = advanced["training_stress"]
                                
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    if stress.get("current_ctl"):
                                        st.metric("CTL (Chronic Load)", f"{stress['current_ctl']:.0f}")
                                
                                with col2:
                                    if stress.get("current_atl"):
                                        st.metric("ATL (Acute Load)", f"{stress['current_atl']:.0f}")
                                
                                with col3:
                                    if stress.get("current_tsb"):
                                        tsb = stress["current_tsb"]
                                        color = "🟢" if tsb > 10 else "🟡" if tsb > -10 else "🔴"
                                        st.metric(f"TSB {color}", f"{tsb:.0f}")
                                
                                if stress.get("tsb_interpretation"):
                                    st.info(f"💡 {stress['tsb_interpretation']}")
                    
                    with tab4:
                        # Distance-Specific Performance
                        if rider_data.get("performance_profile"):
                            st.subheader("🏁 Distance-Specific Performance")
                            distance_perf = rider_data["performance_profile"]
                            
                            # Performance comparison
                            if distance_perf.get("performance_comparison"):
                                comparison = distance_perf["performance_comparison"]
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    if comparison.get("strongest_distance"):
                                        strongest = comparison["strongest_distance"].replace("_", " ").title()
                                        st.metric("Strongest Distance", strongest)
                                
                                with col2:
                                    if comparison.get("power_decay_percentage"):
                                        decay = comparison["power_decay_percentage"]
                                        st.metric("Power Decay", f"{decay:.1f}%")
                                
                                if comparison.get("endurance_profile"):
                                    st.info(f"🏃‍♂️ **Endurance Profile:** {comparison['endurance_profile']}")
                    
                    with tab5:
                        # ML Features Preview
                        st.subheader("🤖 ML Features Preview")
                        features = self.get_rider_ml_features()
                        
                        if features:
                            st.info(f"🎯 Generated {len(features)} features for machine learning applications")
                            
                            # Show key features
                            key_features = [
                                "recent_avg_power", "critical_power_watts", "estimated_vo2_max",
                                "power_performance_score", "endurance_performance_score", "overall_performance_index"
                            ]
                            
                            feature_cols = st.columns(3)
                            for i, feature_name in enumerate(key_features):
                                if feature_name in features and features[feature_name] is not None:
                                    with feature_cols[i % 3]:
                                        value = features[feature_name]
                                        if isinstance(value, float):
                                            st.metric(feature_name.replace('_', ' ').title(), f"{value:.1f}")
                                        else:
                                            st.metric(feature_name.replace('_', ' ').title(), f"{value}")
                        else:
                            st.warning("⚠️ ML features not available")
                    
                    # Data freshness
                    fetch_time = rider_data.get("fetch_timestamp")
                    if fetch_time:
                        st.caption(f"📅 Data last updated: {fetch_time}")
            
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


# Global authentication manager instance cached as resource
@st.cache_resource  # Cache auth manager instance as it's expensive to initialize  
def get_auth_manager() -> AuthenticationManager:
    """Get the global authentication manager instance."""
    return AuthenticationManager()


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
