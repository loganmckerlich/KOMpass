"""
KOMpass - Main Application Entry Point

A streamlined cycling route analysis application that provides:
- Route upload and comprehensive analysis
- Weather forecasting and conditions analysis  
- Strava integration for athlete data
- Performance metrics and terrain classification
- Traffic stop analysis and route complexity metrics

This main module is kept minimal and clean, with heavy lifting delegated to helper modules.
"""

import streamlit as st
from helper.config.logging_config import setup_logging, get_logger
from helper.config.config import get_config
from helper.auth.auth_manager import get_auth_manager
from helper.ui.ui_components import get_ui_components

# Configure page settings
st.set_page_config(
    page_title="KOMpass - Cycling Route Analysis",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize logging
config = get_config()
logger = setup_logging(
    log_level=config.app.log_level,
    log_to_file=config.app.log_to_file
)

# Log application startup
logger.info("KOMpass application starting")
logger.debug(f"Configuration loaded: Strava configured={config.is_strava_configured()}")


def main():
    """Main application entry point."""
    logger.info("Entering main application")
    
    try:
        # Initialize components
        auth_manager = get_auth_manager()
        ui_components = get_ui_components()
        
        # Initialize session state for authentication
        auth_manager.initialize_session_state()
        
        # Handle OAuth callback if present
        auth_manager.handle_oauth_callback()
        
        # Render main UI
        ui_components.render_app_header()
        
        # Navigation and page rendering
        selected_page = ui_components.render_navigation_sidebar()
        logger.debug(f"User navigated to page: {selected_page}")
        
        # Route to appropriate page
        if selected_page == "Home":
            ui_components.render_home_page()
        
        elif selected_page == "Route Upload":
            ui_components.render_route_upload_page()
        
        elif selected_page == "Saved Routes":
            ui_components.render_saved_routes_page()
        
        elif selected_page == "Rider Fitness":
            ui_components.render_rider_fitness_page()
        
        else:
            logger.warning(f"Unknown page selected: {selected_page}")
            st.error(f"Unknown page: {selected_page}")
        
        logger.debug("Main application rendering completed")
        
    except Exception as e:
        logger.error(f"Unhandled error in main application: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please check the logs for details.")
        
        # Show error details in development mode
        if config.app.log_level == "DEBUG":
            st.exception(e)


if __name__ == "__main__":
    main()