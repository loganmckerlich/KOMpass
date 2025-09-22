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
        
        # Perform lightweight session state cleanup on startup
        try:
            from helper.utils.session_state_optimizer import get_session_state_optimizer
            optimizer = get_session_state_optimizer()
            
            # Quick cleanup of old analysis dataframes (most common bloat)
            removed_dataframes = optimizer.cleanup_old_analysis_dataframes()
            if removed_dataframes:
                logger.info(f"Startup cleanup: Removed {len(removed_dataframes)} old analysis dataframes")
                
        except Exception as e:
            logger.warning(f"Session state cleanup failed: {e}")
        
        # Initialize session state for authentication
        auth_manager.initialize_session_state()
        
        # Handle OAuth callback if present
        auth_manager.handle_oauth_callback()
        
        # **NEW**: Authentication-first workflow
        # Check if user is authenticated - if not, show only authentication screen
        if not auth_manager.is_authenticated():
            logger.info("User not authenticated - showing authentication gate")
            ui_components.render_authentication_gate()
            return
        
        # User is authenticated - proceed with main application
        logger.info("User authenticated - rendering main application")
        
        # Render main UI
        ui_components.render_app_header()
        
        # Navigation and page rendering (updated for new workflow)
        with st.sidebar:
            selected_page_raw = ui_components.render_navigation_sidebar()
        
        # Clean page name by removing emoji and extra spaces
        # Handle both emoji-prefixed names and plain names
        if ' ' in selected_page_raw and selected_page_raw.startswith(('🎯', '📊', '🚴')):
            selected_page = selected_page_raw.split(' ', 1)[1]
        else:
            selected_page = selected_page_raw
        logger.debug(f"User navigated to page: {selected_page_raw} -> {selected_page}")
        
        # Route to appropriate page (updated workflow)
        if selected_page == "Speed Predictions":
            ui_components.render_ml_page()
        
        elif selected_page == "User Stats":
            ui_components.render_user_stats_page()
        
        else:
            logger.warning(f"Unknown page selected: {selected_page}")
            st.error(f"Unknown page: {selected_page}")
            st.info("Available pages: Speed Predictions, User Stats")
        
        logger.debug("Main application rendering completed")
        
    except Exception as e:
        logger.error(f"Unhandled error in main application: {e}", exc_info=True)
        st.error("An unexpected error occurred. Please check the logs for details.")
        
        # Show error details in development mode
        if config.app.log_level == "DEBUG":
            st.exception(e)


if __name__ == "__main__":
    main()