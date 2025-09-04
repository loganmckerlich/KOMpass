"""
UI Components Orchestrator - Main UI coordinator using modular components.

This module coordinates all UI operations using specialized components:
- Header and layout management
- Authentication gate for unauthenticated users
- Route upload handling
- Route analysis display
- ML predictions page
- User stats page

Note: This module has been refactored to use smaller, focused components.
"""

import streamlit as st
from typing import Dict, Any

from .header_layout import HeaderAndLayout
from .auth_gate import AuthenticationGate
from .route_upload import RouteUpload
from .route_analysis import RouteAnalysis
from .ml_page import MLPage
from .user_stats import UserStatsPage
from ...config.logging_config import get_logger


logger = get_logger(__name__)


class UIComponents:
    """Main orchestrator for UI components using modular architecture."""
    
    def __init__(self):
        """Initialize UI components orchestrator."""
        logger.info("Initializing refactored UIComponents")
        
        # Initialize component modules
        self.header_layout = HeaderAndLayout()
        self.auth_gate = AuthenticationGate()
        self.route_upload = RouteUpload()
        self.route_analysis = RouteAnalysis()
        self.ml_page = MLPage()
        self.user_stats = UserStatsPage()
    
    def render_app_header(self):
        """Render application header."""
        return self.header_layout.render_app_header()
    
    def render_navigation_sidebar(self) -> str:
        """Render navigation sidebar and return selected page."""
        return self.header_layout.render_navigation_sidebar()
    
    def render_readme_section(self) -> str:
        """Render README section."""
        return self.header_layout.render_readme_section()
    
    def render_authentication_gate(self):
        """Render authentication gate for unauthenticated users."""
        return self.auth_gate.render_authentication_gate()
    
    def render_route_upload_page(self):
        """Render route upload page."""
        return self.route_upload.render_route_upload_page()
    
    def render_ml_page(self):
        """Render ML page."""
        return self.ml_page.render_ml_page()
    
    def render_user_stats_page(self):
        """Render user stats page."""
        return self.user_stats.render_user_stats_page()
    
    def render_route_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """Render route analysis."""
        return self.route_analysis.render_route_analysis(route_data, stats, filename)
    
    # Legacy method delegation for backwards compatibility
    def __getattr__(self, name):
        """Delegate method calls to appropriate component modules."""
        
        # Header and layout methods
        if hasattr(self.header_layout, name):
            return getattr(self.header_layout, name)
        
        # Authentication gate methods
        if hasattr(self.auth_gate, name):
            return getattr(self.auth_gate, name)
        
        # Route upload methods
        if hasattr(self.route_upload, name):
            return getattr(self.route_upload, name)
        
        # Route analysis methods
        if hasattr(self.route_analysis, name):
            return getattr(self.route_analysis, name)
        
        # ML page methods
        if hasattr(self.ml_page, name):
            return getattr(self.ml_page, name)
        
        # User stats methods
        if hasattr(self.user_stats, name):
            return getattr(self.user_stats, name)
        
        # If method not found, raise AttributeError
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")