"""
Header and Layout Components - Handles application header, navigation, and layout.

This module provides:
- Application header with logo and styling controls
- Navigation sidebar
- Custom CSS management
- Layout utilities
"""

import streamlit as st
from typing import Dict, Any

from ...config.config import get_config
from ...auth.auth_manager import get_auth_manager
from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class HeaderAndLayout:
    """Handles application header, navigation, and layout components."""
    
    def __init__(self):
        """Initialize header and layout components."""
        self.config = get_config()
        self.auth_manager = get_auth_manager()
    
    def render_app_header(self):
        """Render the main application header with Strava-inspired styling."""
        # Load custom CSS
        self._load_custom_css()
        
        # Create responsive header with logo, title, and settings
        header_col1, header_col2, header_col3 = st.columns([1, 4, 1])  # Add settings column
        
        with header_col1:
            # App logo with responsive styling
            try:
                st.image(
                    "IMG_1855.png",
                    width=25,  # Smaller logo for better mobile experience
                    use_container_width=False
                )
            except FileNotFoundError:
                # Fallback to CSS-generated logo if image file not found
                st.markdown("""
                <div class="app-logo-container" style="
                    width: 25px; 
                    height: 25px; 
                    background: linear-gradient(45deg, #FC4C02, #FF6B35);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 0.8rem;
                    font-weight: bold;
                    margin: 1rem auto;
                    box-shadow: 0 4px 15px rgba(252, 76, 2, 0.3);
                ">
                    🧭
                </div>
                """, unsafe_allow_html=True)
        
        with header_col2:
            # Custom CSS is always enabled - display header
            st.markdown("""
            <div class="main-header">
                <h1>KOMpass</h1>
                <p>Your intelligent cycling route analysis companion</p>
            </div>
            """, unsafe_allow_html=True)
        
        with header_col3:
            # Units are always metric - no toggle needed
            st.markdown("**Units: Metric**")
            st.caption("km • m • km/h")
    
    def _load_custom_css(self):
        """Load custom CSS for Strava-inspired styling."""
        
        # Custom CSS is always enabled now
        
        # Try to load external CSS file first
        try:
            with open("/home/runner/work/KOMpass/KOMpass/assets/style.css", "r") as f:
                css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        except FileNotFoundError:
            logger.warning("External CSS file not found, using inline CSS")
            # Fallback to inline CSS if external file not found
            pass
        
        # Additional inline CSS for header and components
        
        strava_css = """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Global styling */
        .main-header h1 {
            color: #FC4C02;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 2.5rem;
            margin-bottom: 0.2rem;
            text-shadow: 0 2px 4px rgba(252, 76, 2, 0.1);
        }
        
        .main-header p {
            color: #6B7280;
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            font-size: 1rem;
            margin-top: 0;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background-color: #F8FAFC;
            border-right: 1px solid #E5E7EB;
        }
        
        /* Metric cards styling */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin: 0.5rem 0;
        }
        
        [data-testid="metric-container"] > div > div > div > div {
            color: #374151;
            font-family: 'Inter', sans-serif;
        }
        
        /* Success alerts */
        .stSuccess {
            background-color: #ECFDF5;
            border: 1px solid #10B981;
            border-radius: 8px;
            color: #065F46;
        }
        
        /* Info alerts */
        .stInfo {
            background-color: #EFF6FF;
            border: 1px solid #3B82F6;
            border-radius: 8px;
            color: #1E40AF;
        }
        
        /* Warning alerts */
        .stWarning {
            background-color: #FFFBEB;
            border: 1px solid #F59E0B;
            border-radius: 8px;
            color: #92400E;
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(90deg, #FC4C02 0%, #FF6B35 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(252, 76, 2, 0.2);
        }
        
        .stButton > button:hover {
            background: linear-gradient(90deg, #E63402 0%, #FF5722 100%);
            box-shadow: 0 4px 8px rgba(252, 76, 2, 0.3);
            transform: translateY(-1px);
        }
        
        /* File uploader styling */
        .stFileUploader {
            border: 2px dashed #FC4C02;
            border-radius: 12px;
            background-color: #FEF7F0;
            padding: 2rem;
            text-align: center;
        }
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #F3F4F6;
            border-radius: 8px;
            color: #6B7280;
            font-family: 'Inter', sans-serif;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border: 1px solid #E5E7EB;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #FC4C02;
            color: white;
            border-color: #FC4C02;
        }
        
        /* Progress bar styling */
        .stProgress .st-bo {
            background-color: #FC4C02;
        }
        
        /* Selectbox styling */
        .stSelectbox > div > div > div {
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
        }
        
        /* Map container styling */
        .folium-map {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .main-header h1 {
                font-size: 2rem;
            }
            
            .main-header p {
                font-size: 0.9rem;
            }
            
            [data-testid="metric-container"] {
                padding: 0.75rem;
                margin: 0.25rem 0;
            }
        }
        </style>
        """
        
        st.markdown(strava_css, unsafe_allow_html=True)
    
    def render_navigation_sidebar(self) -> str:
        """
        Render navigation sidebar and return selected page.
        
        Returns:
            Selected page name
        """
        with st.sidebar:
            st.markdown("## 🧭 Navigation")
            
            # Feature flag status indicators
            config = get_config()
            
            # Traffic analysis status
            if config.app.enable_traffic_analysis:
                traffic_status = "🟢 Traffic Analysis: **Enabled**"
            else:
                traffic_status = "🔴 Traffic Analysis: **Disabled**"
            
            # Weather analysis status
            if config.app.enable_weather_analysis:
                weather_status = "🟢 Weather Analysis: **Enabled**"
            else:
                weather_status = "🔴 Weather Analysis: **Disabled**"
            
            # Display status in sidebar
            st.markdown("### Feature Status")
            st.markdown(traffic_status)
            st.markdown(weather_status)
            st.markdown("---")
            
            # Main navigation (streamlined for authenticated users)
            # Initialize selected page index in session state if not exists
            if 'selected_page_index' not in st.session_state:
                st.session_state['selected_page_index'] = 0
            
            selected_page = st.radio(
                "Choose a page:",
                ["🎯 Speed Predictions", "📊 User Stats", "📁 Route Upload"],
                index=st.session_state['selected_page_index'],
                key="page_selector"
            )
            
            # Update session state when radio selection changes
            page_options = ["🎯 Speed Predictions", "📊 User Stats", "📁 Route Upload"]
            if selected_page in page_options:
                st.session_state['selected_page_index'] = page_options.index(selected_page)
            
            st.markdown("---")
            
            # Strava connection section
            st.markdown("### Strava Integration")
            if self.auth_manager.is_authenticated():
                st.success("✅ Connected to Strava")
                if st.button("🔓 Disconnect from Strava"):
                    self.auth_manager.logout()
                    st.rerun()
            else:
                # Render the complete authentication UI with sign-in button
                self.auth_manager.render_authentication_ui()
            
            st.markdown("---")
            
            # App info
            st.markdown("### About")
            st.markdown("""
            **KOMpass** provides comprehensive cycling route analysis with:
            - GPS-based route metrics
            - Elevation and gradient analysis  
            - Route complexity scoring
            - Traffic and weather insights
            - Strava integration
            """)
            
            return selected_page
    
    def render_readme_section(_self) -> str:
        """
        Render README information section.
        
        Returns:
            README content as string
        """
        log_function_entry(logger, "render_readme_section")
        
        readme_content = """
        ## 🧭 KOMpass - Cycling Route Analysis
        
        **KOMpass** is your intelligent cycling route analysis companion that provides comprehensive insights into your cycling routes.
        
        ### ✨ Key Features
        - **Route Analysis**: Upload GPX files for detailed route breakdown
        - **Elevation Profiles**: Comprehensive climb detection and gradient analysis
        - **Performance Metrics**: Distance, speed, and complexity calculations
        - **Traffic Analysis**: Intersection and traffic light detection (when enabled)
        - **Weather Integration**: Route-specific weather forecasting (when enabled)
        - **Strava Integration**: Connect your Strava account for enhanced analysis
        
        ### 🚀 Getting Started
        1. **Upload a Route**: Use the 'Route Upload' page to upload your GPX file
        2. **Connect Strava**: Link your Strava account for additional features
        3. **Analyze**: Get comprehensive insights about your cycling routes
        
        ### 📊 What You'll Get
        - Detailed elevation profiles and climb categorization
        - Route complexity scoring based on turns and terrain
        - Performance predictions and pacing recommendations
        - Traffic awareness for urban routes
        - Weather-informed planning
        """
        
        log_function_exit(logger, "render_readme_section")
        return readme_content