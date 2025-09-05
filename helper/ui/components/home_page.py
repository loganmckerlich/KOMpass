"""
Home Page Component - Renders the main application home page.

This module provides:
- Welcome message and feature overview
- Feature status indicators
- Getting started guidance
- Feature flag awareness messaging
"""

import streamlit as st
from typing import Dict, Any

from ...config.config import get_config
from ...auth.auth_manager import get_auth_manager
from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class HomePage:
    """Handles home page rendering and welcome content."""
    
    def __init__(self):
        """Initialize home page component."""
        self.config = get_config()
        self.auth_manager = get_auth_manager()
    
    def render_home_page(self):
        """Render the main home page with welcome content and feature overview."""
        log_function_entry(logger, "render_home_page")
        
        # Welcome section
        st.markdown("# Welcome to KOMpass! 🚴‍♂️")
        st.markdown("Your intelligent cycling route analysis companion")
        
        # Main content columns
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("## 🎯 What KOMpass Offers")
            st.markdown("""
            - **📊 Route Metrics**: Distance, elevation, gradient analysis
            - **🏔️ Climb Detection**: Categorized climbs with difficulty ratings
            - **📈 Performance Estimates**: Speed and power predictions
            - **🗺️ Interactive Maps**: Visual route representation
            - **📱 Strava Integration**: Enhanced analysis with your cycling data
            """)
            
            # Quick start guide
            st.markdown("### 🚀 Quick Start")
            st.markdown("""
            1. **Upload Route**: Go to 'Speed Predictions' and select your GPX file
            2. **View Analysis**: Get comprehensive route insights and metrics
            3. **Connect Strava**: Link your account for enhanced features
            """)
        
        with col2:
            # Strava Integration Section
            st.markdown("### 🔗 Strava Integration")
            
            if self.auth_manager.is_authenticated():
                # Show connected status and rider info
                athlete_info = self.auth_manager.get_athlete_info()
                if athlete_info:
                    athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
                    st.success(f"✅ Connected as **{athlete_name or 'Unknown Athlete'}**")
                else:
                    st.success("✅ Connected to Strava")
                
                st.info("💡 Visit the **Speed Predictions** page to import activities from Strava.")
            else:
                # Show sign-in option
                st.info("Connect your Strava account for enhanced features:")
                st.markdown("- Access your recent activities")
                st.markdown("- Enhanced performance analysis") 
                st.markdown("- Personalized insights")
                
                # Render Strava authentication UI
                self.auth_manager.render_authentication_ui()
            
            # Call-to-action
            st.markdown("---")
            if st.button("🚀 Upload Your First Route", use_container_width=True):
                st.session_state['nav_to_upload'] = True
                st.rerun()
        
        log_function_exit(logger, "render_home_page")
    
    def get_feature_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of current feature status.
        
        Returns:
            Dictionary with feature status information
        """
        return {
            "core_features": {
                "route_analysis": True,
                "elevation_analysis": True,
                "climb_detection": True,
                "performance_estimates": True,
                "mapping": True,
                "strava_integration": True
            },
            "optional_features": {
                "traffic_analysis": self.config.app.enable_traffic_analysis,
                "weather_analysis": self.config.app.enable_weather_analysis
            },
            "data_sources": {
                "gps_data": True,
                "elevation_data": True,
                "external_apis": self.config.app.enable_traffic_analysis or self.config.app.enable_weather_analysis
            }
        }