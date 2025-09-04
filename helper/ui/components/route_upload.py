"""
Route Upload Component - Handles route file uploads and Strava activity imports.

This module provides:
- GPX file upload interface
- Strava activity selection and import
- File processing and validation
- Route data conversion
"""

import streamlit as st
import tempfile
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from ...processing.route_processor import RouteProcessor
from ...auth.auth_manager import get_auth_manager
from ...config.config import get_config
from ...config.logging_config import get_logger, log_function_entry, log_function_exit
from ...ml.model_manager import ModelManager


logger = get_logger(__name__)


class RouteUpload:
    """Handles route upload functionality including GPX files and Strava activities."""
    
    def __init__(self):
        """Initialize route upload component."""
        self.config = get_config()
        self.auth_manager = get_auth_manager()
        self.route_processor = RouteProcessor(data_dir=self.config.app.data_directory)
        self.model_manager = ModelManager()
    
    def render_route_upload_page(self):
        """Render the route upload page with file upload and Strava options."""
        log_function_entry(logger, "render_route_upload_page")
        
        # Check if we should show route analysis results
        if st.session_state.get('show_analysis', False) and st.session_state.get('current_route'):
            self._render_route_analysis_results()
            return
        
        st.markdown("# 📁 Route Upload")
        st.markdown("Upload a GPX file or import from Strava to analyze your cycling route")
        
        # Create tabs for different upload methods
        upload_tab, strava_tab = st.tabs(["📄 Upload GPX File", "📱 Import from Strava"])
        
        with upload_tab:
            self._render_file_upload_section()
        
        with strava_tab:
            self._render_strava_import_section()
        
        log_function_exit(logger, "render_route_upload_page")
    
    def _render_file_upload_section(self):
        """Render the file upload section."""
        st.markdown("## Upload GPX File")
        st.markdown("Select a GPX file from your device for route analysis")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a GPX file",
            type=['gpx'],
            help="Upload a GPX file containing your cycling route with GPS coordinates and elevation data"
        )
        
        if uploaded_file is not None:
            # Show file details
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📄 File Name", uploaded_file.name)
            
            with col2:
                file_size = uploaded_file.size / 1024  # Convert to KB
                st.metric("📊 File Size", f"{file_size:.1f} KB")
            
            with col3:
                st.metric("📅 Upload Time", datetime.now().strftime("%H:%M:%S"))
            
            # Process file button
            if st.button("🔍 Analyze Route", type="primary", use_container_width=True):
                with st.spinner("Processing your route..."):
                    result = self._process_uploaded_file(uploaded_file)
                    
                    if result:
                        st.success("✅ Route processed successfully!")
                        st.session_state['current_route'] = result
                        st.session_state['show_analysis'] = True
                        st.rerun()
                    else:
                        st.error("❌ Failed to process the route file. Please check the file format and try again.")
        else:
            # Show upload instructions
            st.info("""
            **📋 Upload Instructions:**
            - Select a GPX file from your cycling computer or mobile app
            - Ensure the file contains GPS coordinates and elevation data
            - File should be from a completed cycling route
            - Maximum file size: 10MB
            """)
    
    def _render_strava_import_section(self):
        """Render the Strava import section."""
        st.markdown("## Import from Strava")
        
        if not self.auth_manager.is_authenticated():
            st.warning("⚠️ Please connect to Strava first to import activities")
            st.markdown("Go to the sidebar to connect your Strava account.")
            return
        
        st.markdown("Select a recent cycling activity from your Strava account")
        
        # Show Strava routes section
        self._render_strava_routes_section()
    
    def _render_strava_routes_section(self):
        """Render Strava activities selection section."""
        log_function_entry(logger, "render_strava_routes_section")
        
        try:
            oauth_client = self.auth_manager.get_oauth_client()
            access_token = self.auth_manager.get_access_token()
            
            if not access_token:
                st.error("❌ Unable to access Strava data. Please reconnect your account.")
                return
            
            # Fetch recent activities
            with st.spinner("Loading your recent Strava activities..."):
                try:
                    activities = oauth_client.get_activities(access_token, per_page=50)
                    
                    # Filter cycling activities
                    cycling_activities = [
                        activity for activity in activities 
                        if activity.get('type') in ['Ride', 'VirtualRide', 'EBikeRide']
                    ]
                    
                except Exception as e:
                    st.error(f"❌ Failed to fetch Strava activities: {str(e)}")
                    logger.error(f"Strava activities fetch error: {e}")
                    return
            
            if not cycling_activities:
                st.info("ℹ️ No cycling activities found in your recent Strava data.")
                return
            
            st.success(f"✅ Found {len(cycling_activities)} cycling activities")
            
            # Display activities in a more compact format
            st.markdown("### 🚴 Recent Cycling Activities")
            
            # Create activity selection
            selected_activity = None
            
            for i, activity in enumerate(cycling_activities):
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        activity_name = activity.get('name', f"Activity {activity.get('id', 'Unknown')}")
                        st.markdown(f"**{activity_name}**")
                        activity_date = activity.get('start_date', '')[:10] if activity.get('start_date') else 'Unknown'
                        st.caption(f"📅 {activity_date}")
                    
                    with col2:
                        distance = activity.get('distance', 0) / 1000  # Convert to km
                        st.metric("Distance", f"{distance:.1f} km")
                    
                    with col3:
                        elevation = activity.get('total_elevation_gain', 0)
                        st.metric("Elevation", f"{elevation:.0f} m")
                    
                    with col4:
                        if st.button("Select", key=f"select_activity_{i}", help=f"Import activity: {activity_name}"):
                            selected_activity = activity
                            break
                    
                    st.markdown("---")
            
            # Process selected activity
            if selected_activity:
                with st.spinner(f"Importing activity: {selected_activity.get('name', 'Unknown')}..."):
                    result = self._process_strava_activity(selected_activity)
                    
                    if result:
                        st.success(f"✅ Successfully imported: {selected_activity.get('name', 'Activity')}")
                        st.session_state['current_route'] = result
                        st.session_state['show_analysis'] = True
                        st.rerun()
                    else:
                        st.error("❌ Failed to import the Strava activity. The activity may not have detailed route data.")
        
        except Exception as e:
            st.error(f"❌ Error loading Strava activities: {str(e)}")
            logger.error(f"Strava routes section error: {e}")
        
        log_function_exit(logger, "render_strava_routes_section")
    
    def _process_uploaded_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Process uploaded GPX file and return route data.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            Processed route data dictionary or None if processing failed
        """
        log_function_entry(logger, "process_uploaded_file")
        
        try:
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.gpx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                # Process the route
                filename = uploaded_file.name
                route_data = self.route_processor.process_route(tmp_file_path)
                
                if route_data:
                    # Add filename to route data
                    route_data['filename'] = filename
                    route_data['upload_timestamp'] = datetime.now().isoformat()
                    
                    logger.info(f"Successfully processed uploaded file: {filename}")
                    log_function_exit(logger, "process_uploaded_file")
                    return route_data
                else:
                    logger.error(f"Route processing returned None for file: {filename}")
                    return None
                    
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except OSError:
                    pass
        
        except Exception as e:
            logger.error(f"Error processing uploaded file: {e}")
            log_function_exit(logger, "process_uploaded_file")
            return None
    
    def _process_strava_activity(self, activity: Dict) -> Optional[Dict[str, Any]]:
        """
        Process Strava activity and convert to route data.
        
        Args:
            activity: Strava activity dictionary
            
        Returns:
            Processed route data or None if processing failed
        """
        log_function_entry(logger, "process_strava_activity")
        
        try:
            oauth_client = self.auth_manager.get_oauth_client()
            access_token = self.auth_manager.get_access_token()
            
            if not access_token:
                logger.error("No access token available for Strava activity processing")
                return None
            
            # Get detailed activity streams
            activity_id = activity.get('id')
            if not activity_id:
                logger.error("No activity ID found in Strava activity")
                return None
            
            # Fetch activity streams (GPS coordinates, elevation, etc.)
            streams = oauth_client.get_activity_streams(
                access_token, 
                activity_id, 
                'latlng,altitude,distance,time'
            )
            
            if not streams:
                logger.error(f"No streams data available for activity {activity_id}")
                return None
            
            # Convert streams to route format
            route_data = self._convert_strava_streams_to_route(streams, activity)
            
            if route_data:
                logger.info(f"Successfully processed Strava activity: {activity_id}")
                log_function_exit(logger, "process_strava_activity")
                return route_data
            else:
                logger.error(f"Failed to convert Strava streams to route data for activity {activity_id}")
                return None
        
        except Exception as e:
            logger.error(f"Error processing Strava activity: {e}")
            log_function_exit(logger, "process_strava_activity")
            return None
    
    def _convert_strava_streams_to_route(self, streams: Dict, activity: Dict) -> Optional[Dict[str, Any]]:
        """
        Convert Strava streams data to route format for processing.
        
        Args:
            streams: Strava streams data
            activity: Strava activity metadata
            
        Returns:
            Route data dictionary or None if conversion failed
        """
        log_function_entry(logger, "convert_strava_streams_to_route")
        
        try:
            # Extract coordinates and elevation
            latlng_stream = streams.get('latlng', {}).get('data', [])
            altitude_stream = streams.get('altitude', {}).get('data', [])
            distance_stream = streams.get('distance', {}).get('data', [])
            time_stream = streams.get('time', {}).get('data', [])
            
            if not latlng_stream:
                logger.error("No GPS coordinates found in Strava streams")
                return None
            
            # Create route points
            route_points = []
            for i, (lat, lon) in enumerate(latlng_stream):
                point = {
                    'latitude': lat,
                    'longitude': lon,
                    'elevation': altitude_stream[i] if i < len(altitude_stream) else 0,
                    'distance': distance_stream[i] if i < len(distance_stream) else 0,
                    'time': time_stream[i] if i < len(time_stream) else 0
                }
                route_points.append(point)
            
            # Create route data structure
            route_data = {
                'points': route_points,
                'metadata': {
                    'name': activity.get('name', f"Strava Activity {activity.get('id')}"),
                    'source': 'strava',
                    'activity_id': activity.get('id'),
                    'start_date': activity.get('start_date'),
                    'distance': activity.get('distance'),
                    'total_elevation_gain': activity.get('total_elevation_gain'),
                    'moving_time': activity.get('moving_time'),
                    'elapsed_time': activity.get('elapsed_time')
                },
                'filename': f"strava_activity_{activity.get('id', 'unknown')}.gpx",
                'import_timestamp': datetime.now().isoformat()
            }
            
            # Process the route using the route processor
            processed_data = self.route_processor.process_route_data(route_data)
            
            log_function_exit(logger, "convert_strava_streams_to_route")
            return processed_data
        
        except Exception as e:
            logger.error(f"Error converting Strava streams to route: {e}")
            log_function_exit(logger, "convert_strava_streams_to_route")
            return None
    
    def _render_route_analysis_results(self):
        """Render the route analysis results page."""
        log_function_entry(logger, "render_route_analysis_results")
        
        # Get route data from session state
        route_data = st.session_state.get('current_route')
        
        if not route_data:
            st.error("❌ No route data found. Please upload a route first.")
            if st.button("🔙 Back to Upload"):
                st.session_state['show_analysis'] = False
                st.rerun()
            return
        
        # Display header with back button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("# 📊 Route Analysis Results")
            filename = route_data.get('filename', 'Unknown Route')
            st.markdown(f"**Route:** {filename}")
        
        with col2:
            if st.button("🔙 Back to Upload", type="secondary"):
                st.session_state['show_analysis'] = False
                st.rerun()
        
        # Extract stats and route data for analysis
        stats = route_data.get('statistics', {})
        actual_route_data = route_data.get('route_data', route_data)
        
        # Use the RouteAnalysis component to render the analysis
        from .route_analysis import RouteAnalysis
        route_analyzer = RouteAnalysis()
        route_analyzer.render_route_analysis(actual_route_data, stats, filename)
        
        # Add ML training suggestion after route analysis
        self._render_ml_training_suggestion()
        
        log_function_exit(logger, "render_route_analysis_results")
    
    def _render_ml_training_suggestion(self):
        """Render ML training suggestion after route analysis."""
        try:
            # Only show for authenticated users
            if not self.auth_manager.is_authenticated():
                return
            
            # Check if user has rider data
            rider_data = st.session_state.get("rider_fitness_data")
            if not rider_data:
                return
            
            # Get user ID for training assessment
            athlete_info = st.session_state.get("athlete_info", {})
            user_id = str(athlete_info.get("id", "unknown"))
            
            if user_id == "unknown":
                return
            
            # Check training need
            training_need = self.model_manager.check_training_need(user_id)
            
            if training_need.get('needs_training', False) and not training_need.get('training_in_progress', False):
                st.markdown("---")
                st.markdown("## 🤖 Improve Your Predictions")
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.info("💡 **Get more accurate speed predictions!** Train personalized AI models using your ride history.")
                    
                    reasons = training_need.get('reasons', [])
                    if reasons:
                        st.write("**Why training is recommended:**")
                        for reason in reasons[:3]:  # Show max 3 reasons
                            st.write(f"• {reason}")
                
                with col2:
                    if st.button("🚀 Train AI Models", type="primary", key="train_from_upload"):
                        # Navigate to ML page
                        st.session_state['selected_page_index'] = 2  # ML Predictions page
                        st.rerun()
                    
                    st.write(f"📊 **Your Data:**")
                    data_count = training_need.get('user_data_count', {})
                    st.write(f"• {data_count.get('route_files', 0)} routes")
                    st.write(f"• {data_count.get('fitness_files', 0)} fitness records")
        
        except Exception as e:
            logger.warning(f"Error rendering ML training suggestion: {e}")
            # Silently fail to avoid disrupting the main route analysis