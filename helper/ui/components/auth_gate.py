"""
Authentication Gate Component - Blocks access until user is authenticated.

This component ensures users must authenticate with Strava before accessing
any application features. It provides a focused authentication experience.
"""

import streamlit as st
from typing import Dict, Any

from ...config.config import get_config
from ...auth.auth_manager import get_auth_manager
from ...config.logging_config import get_logger


logger = get_logger(__name__)


class AuthenticationGate:
    """Handles the authentication gate that blocks access until user logs in."""
    
    def __init__(self):
        """Initialize authentication gate."""
        self.config = get_config()
        self.auth_manager = get_auth_manager()
    
    def render_authentication_gate(self):
        """
        Render the authentication gate page.
        
        This is the only page accessible to unauthenticated users.
        """
        logger.info("Rendering authentication gate for unauthenticated user")
        
        # Load custom CSS (simpler version for auth page)
        self._load_auth_css()
        
        # Center the authentication content
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # App header
            st.markdown("""
            <div class="auth-header">
                <h1>🧭 KOMpass</h1>
                <p>Your intelligent cycling route analysis companion</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Authentication required message
            st.markdown("""
            <div class="auth-message">
                <h2>🚴‍♂️ Get Started with Strava</h2>
                <p>KOMpass uses your Strava data to provide personalized speed predictions and route analysis.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Benefits section
            with st.container():
                st.markdown("### 🎯 What You'll Get")
                
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown("""
                    **🤖 AI Speed Predictions**  
                    Get personalized speed forecasts for any route based on your fitness data
                    
                    **📊 Performance Analysis**  
                    View your FTP, power curves, and cycling metrics
                    """)
                
                with col_right:
                    st.markdown("""
                    **🗺️ Route Intelligence**  
                    Upload GPX files or use your Strava routes for analysis
                    
                    **⚡ Automatic Training**  
                    Your recent activities train the model automatically
                    """)
            
            st.markdown("---")
            
            # Authentication section
            if not self.auth_manager.is_oauth_configured():
                st.error("⚠️ Strava integration is not configured. Please contact the administrator.")
                
                with st.expander("ℹ️ How to enable Strava integration"):
                    st.markdown("""
                    To enable Strava integration, the application needs to be configured with:
                    - **STRAVA_CLIENT_ID**: Your Strava application client ID
                    - **STRAVA_CLIENT_SECRET**: Your Strava application client secret
                    
                    These should be set as environment variables.
                    """)
            else:
                # Show authentication button
                self._render_auth_button()
        
        # Footer
        st.markdown("---")
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("""
                <div style="text-align: center; color: #6B7280; font-size: 0.875rem;">
                    <p>🔒 Secure OAuth connection • We only access your cycling activities</p>
                    <p>No personal data is stored • Disconnect anytime</p>
                </div>
                """, unsafe_allow_html=True)
    
    def _render_auth_button(self):
        """Render the Strava authentication button."""
        
        # Center the button
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            # Get authorization URL
            auth_url = self.auth_manager.get_authorization_url()
            
            if auth_url:
                # Use st.link_button for proper OAuth redirect (works reliably across browsers)
                st.link_button(
                    "🚴 Connect with Strava",
                    auth_url,
                    help="Connect your Strava account to get started",
                    type="primary"
                )
            else:
                st.error("❌ Failed to generate authorization URL. Please try again.")
    
    def _load_auth_css(self):
        """Load CSS styling for the authentication page."""
        auth_css = """
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Main container styling */
        .stApp {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        /* Auth header styling */
        .auth-header {
            text-align: center;
            padding: 2rem 0;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .auth-header h1 {
            color: #FC4C02;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            font-size: 3rem;
            margin-bottom: 0.5rem;
        }
        
        .auth-header p {
            color: #6B7280;
            font-family: 'Inter', sans-serif;
            font-weight: 400;
            font-size: 1.25rem;
        }
        
        /* Auth message styling */
        .auth-message {
            text-align: center;
            padding: 1.5rem;
            background: rgba(255, 255, 255, 0.9);
            border-radius: 12px;
            margin-bottom: 2rem;
        }
        
        .auth-message h2 {
            color: #374151;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        .auth-message p {
            color: #6B7280;
            font-family: 'Inter', sans-serif;
            font-size: 1.1rem;
        }
        
        /* Button styling */
        .stButton > button {
            background: linear-gradient(90deg, #FC4C02 0%, #FF6B35 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 1.1rem;
            padding: 0.75rem 2rem;
            transition: all 0.3s ease;
            box-shadow: 0 4px 16px rgba(252, 76, 2, 0.3);
            width: 100%;
        }
        
        .stButton > button:hover {
            background: linear-gradient(90deg, #E63402 0%, #FF5722 100%);
            box-shadow: 0 6px 20px rgba(252, 76, 2, 0.4);
            transform: translateY(-2px);
        }
        
        /* Container styling */
        .stContainer {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        
        /* Info styling */
        .stInfo {
            background-color: #EFF6FF;
            border: 1px solid #3B82F6;
            border-radius: 8px;
            color: #1E40AF;
        }
        
        /* Error styling */
        .stError {
            background-color: #FEF2F2;
            border: 1px solid #EF4444;
            border-radius: 8px;
            color: #DC2626;
        }
        </style>
        """
        
        st.markdown(auth_css, unsafe_allow_html=True)