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
from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class HomePage:
    """Handles home page rendering and welcome content."""
    
    def __init__(self):
        """Initialize home page component."""
        self.config = get_config()
    
    def render_home_page(self):
        """Render the main home page with welcome content and feature overview."""
        log_function_entry(logger, "render_home_page")
        
        # Welcome section
        st.markdown("# Welcome to KOMpass! 🚴‍♂️")
        st.markdown("Your intelligent cycling route analysis companion")
        
        # Feature overview with current status
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("## 🎯 What KOMpass Offers")
            
            # Core features (always available)
            st.markdown("### ✅ Core Route Analysis")
            st.markdown("""
            - **📊 Route Metrics**: Distance, elevation, gradient analysis
            - **🏔️ Climb Detection**: Categorized climbs with difficulty ratings
            - **📈 Performance Estimates**: Speed and power predictions
            - **🔄 Route Complexity**: Turn analysis and complexity scoring
            - **🗺️ Interactive Maps**: Visual route representation
            """)
            
            # Optional features with status
            st.markdown("### 🔧 Optional Features")
            
            # Traffic analysis status
            if self.config.app.enable_traffic_analysis:
                st.markdown("- **🚦 Traffic Analysis**: ✅ **Enabled** - Intersection and traffic light detection")
            else:
                st.markdown("- **🚦 Traffic Analysis**: 🚫 **Temporarily Disabled**")
                st.info("Traffic light and intersection analysis is temporarily disabled to ensure route analysis focuses on pure GPS data without external assumptions.")
            
            # Weather analysis status
            if self.config.app.enable_weather_analysis:
                st.markdown("- **🌤️ Weather Analysis**: ✅ **Enabled** - Route-specific weather forecasting")
            else:
                st.markdown("- **🌤️ Weather Analysis**: 🚫 **Temporarily Disabled**")
                st.info("Weather analysis is temporarily disabled to focus on core route data analysis.")
            
            # Strava integration (always available)
            st.markdown("- **📱 Strava Integration**: ✅ **Available** - Connect for enhanced rider data")
        
        with col2:
            st.markdown("## 🚀 Quick Start")
            
            # Quick start guide
            steps = [
                ("1️⃣", "Upload Route", "Go to 'Route Upload' and select your GPX file"),
                ("2️⃣", "View Analysis", "Get comprehensive route insights and metrics"),
                ("3️⃣", "Connect Strava", "Link your account for enhanced features"),
                ("4️⃣", "Explore Data", "Dive deep into elevation, gradients, and performance")
            ]
            
            for emoji, title, description in steps:
                with st.container():
                    st.markdown(f"**{emoji} {title}**")
                    st.caption(description)
                    st.markdown("")
            
            # Call-to-action
            st.markdown("---")
            st.markdown("### 📁 Ready to Start?")
            if st.button("🚀 Upload Your First Route", use_container_width=True):
                st.session_state['nav_to_upload'] = True
                st.rerun()
        
        # Current feature focus
        st.markdown("---")
        st.markdown("## 🎯 Current Focus: Pure Route Analysis")
        
        info_cols = st.columns(3)
        
        with info_cols[0]:
            st.info("""
            **📊 GPS-Based Metrics**
            
            All analysis uses only GPS coordinates and elevation data from your route file - no external assumptions or estimates.
            """)
        
        with info_cols[1]:
            st.success("""
            **🔬 Precise Calculations**
            
            Distance, elevation, gradients, and performance metrics calculated from mathematical analysis of your actual route data.
            """)
        
        with info_cols[2]:
            st.warning("""
            **🛡️ Data Privacy**
            
            With optional features disabled, your route analysis doesn't make any external API calls for traffic or weather data.
            """)
        
        # Recent updates
        st.markdown("---")
        st.markdown("## 📝 Recent Updates")
        
        with st.expander("🔧 Feature Flags Implementation", expanded=False):
            st.markdown("""
            **What's New:**
            - Added configurable feature flags for traffic and weather analysis
            - Improved focus on core GPS-based route analysis
            - Enhanced data privacy with optional external API calls
            - Maintained all core route processing capabilities
            
            **What Remains Enabled:**
            - Full GPS-based route analysis
            - Elevation and gradient calculations
            - Climb detection and categorization
            - Route complexity analysis
            - Interactive mapping
            - Strava integration
            """)
        
        with st.expander("⚡ Performance Optimizations", expanded=False):
            st.markdown("""
            **Improvements:**
            - Faster route processing with streamlined analysis
            - Reduced external dependencies
            - Better session state management
            - Optimized caching strategies
            """)
        
        # Tips and recommendations
        st.markdown("---")
        st.markdown("## 💡 Tips for Best Results")
        
        tip_cols = st.columns(2)
        
        with tip_cols[0]:
            st.markdown("""
            **📂 File Quality**
            - Use high-quality GPX files with regular GPS points
            - Ensure elevation data is included in your file
            - Check that coordinates are accurate
            """)
        
        with tip_cols[1]:
            st.markdown("""
            **🔗 Strava Integration**
            - Connect Strava for rider performance analysis
            - Access your recent activities and power data
            - Get personalized performance predictions
            """)
        
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