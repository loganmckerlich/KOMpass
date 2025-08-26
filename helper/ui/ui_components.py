"""
UI Components for KOMpass application.
Contains reusable UI functions and page rendering logic.
Optimized with Streamlit caching and fragmentation for performance.
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import time
from streamlit_folium import st_folium
import hashlib

from ..processing.route_processor import RouteProcessor
from ..processing.weather_analyzer import WeatherAnalyzer
from ..auth.auth_manager import get_auth_manager
from ..config.config import get_config
from ..config.logging_config import get_logger, log_function_entry, log_function_exit, log_error, log_execution_time
from ..utils.units import UnitConverter

logger = get_logger(__name__)


class UIComponents:
    """Handles UI component rendering and user interactions."""
    
    def __init__(self):
        """Initialize UI components."""
        log_function_entry(logger, "__init__")
        self.config = get_config()
        self.auth_manager = get_auth_manager()
        self.route_processor = RouteProcessor(data_dir=self.config.app.data_directory)
        self.weather_analyzer = WeatherAnalyzer()
        log_function_exit(logger, "__init__")
    
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
            # Check if custom CSS is enabled for conditional styling
            enable_custom_css = getattr(st.session_state, 'enable_custom_css', True)
            
            if enable_custom_css:
                st.markdown("""
                <div class="main-header">
                    <h1>KOMpass</h1>
                    <p>Your intelligent cycling route analysis companion</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Simple header without custom styling
                st.title("🧭 KOMpass")
                st.markdown("*Your intelligent cycling route analysis companion*")
        
        with header_col3:
            # CSS toggle in header (not sidebar)
            st.markdown("##### ⚙️")
            enable_custom_css = st.toggle(
                "Custom Styling", 
                value=False,
                key="enable_custom_css",
                help="Enable Strava-inspired custom styling. Disable to use default Streamlit styling."
            )
            
            # Note: CSS preference is automatically stored in session state by the toggle widget
        
        # Minimal authentication in sidebar
        with st.sidebar:
            st.markdown("### 🔐 Auth")
            self.auth_manager.render_authentication_ui()
    
    def _load_custom_css(self):
        """Load custom CSS for Strava-inspired styling."""
        # Check if custom CSS is enabled
        enable_custom_css = getattr(st.session_state, 'enable_custom_css', False)
        
        if not enable_custom_css:
            # Skip loading custom CSS if disabled by user
            return
            
        try:
            with open("assets/style.css", "r") as f:
                css = f.read()
            st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        except FileNotFoundError:
            # Fallback inline CSS if file not found
            st.markdown("""
            <style>
            :root {
                --strava-orange: #FC4C02;
                --strava-dark: #2D2D2D;
                --strava-white: #FFFFFF;
            }
            .stApp { font-family: 'Inter', sans-serif; }
            .main-header {
                background: linear-gradient(90deg, var(--strava-orange) 0%, #E34D00 100%);
                color: var(--strava-white);
                padding: 1.5rem 2rem;
                border-radius: 0 0 20px 20px;
                margin-bottom: 2rem;
                box-shadow: 0 4px 20px rgba(252, 76, 2, 0.3);
            }
            .main-header h1 { margin: 0; font-weight: 700; font-size: 2.5rem; }
            .main-header p { margin: 0.5rem 0 0 0; opacity: 0.9; }
            </style>
            """, unsafe_allow_html=True)
    
    @st.cache_data(ttl=3600)  # Cache README for 1 hour
    def render_readme_section(_self) -> str:
        """Render README content section.
        Cached to avoid repeated file I/O.
        
        Note: Uses leading underscore on self to exclude from caching key
        """
        log_function_entry(logger, "render_readme_section")
        
        try:
            readme_path = "README.md"
            with open(readme_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            logger.debug(f"Successfully read README from {readme_path}")
            log_function_exit(logger, "render_readme_section", "Success")
            return content
            
        except Exception as e:
            log_error(logger, e, "Error reading README.md")
            return f"Error reading README.md: {e}"
    
    def render_navigation_sidebar(self) -> str:
        """Render streamlined navigation sidebar."""
        st.markdown("### 🧭 Navigate")
        
        page_options = {
            "🏠 Dashboard": "Home",
            "📈 Upload Route": "Route Upload", 
            "💾 My Routes": "Saved Routes",
            "🏃‍♂️ Rider Fitness": "Rider Fitness"
        }
        
        selected_display = st.selectbox("Page Navigation", list(page_options.keys()), label_visibility="collapsed")
        selected_page = page_options[selected_display]
        
        # Settings section
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        
        # Unit toggle (CSS toggle moved to header)
        st.markdown("### ⚖️ Units")
        use_imperial = st.toggle(
            "Imperial (mi/ft)", 
            key="use_imperial_units",
            help="Switch between metric and imperial units"
        )
        
        # Store unit preference in session state
        st.session_state.use_imperial = use_imperial
        
        logger.debug(f"User selected page: {selected_page}, Imperial units: {use_imperial}")
        return selected_page
    
    def render_home_page(self):
        """Render the modern, user-friendly home page."""
        log_function_entry(logger, "render_home_page")
        
        # Welcome section
        st.markdown("""
        <div class="welcome-section">
            <h2>Welcome to KOMpass! 🚴‍♂️</h2>
            <p>Your intelligent cycling companion for route analysis, performance insights, and weather forecasting. 
            Upload your routes and discover detailed analytics to improve your rides.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick stats/features overview
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <h3>Route Analysis</h3>
                <p>Advanced metrics including elevation, gradients, and performance insights</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🌤️</div>
                <h3>Weather Forecast</h3>
                <p>Plan your rides with detailed weather conditions and forecasting</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🏆</div>
                <h3>KOM Hunter</h3>
                <p>Identify segments and optimize your training for those elusive KOMs</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick actions
        st.markdown("### 🚀 Quick Actions")
        st.markdown("""
        <div class="feature-card">
            <p>Use the navigation sidebar to:</p>
            <ul>
                <li><strong>📈 Upload Route</strong> - Analyze new GPX files</li>
                <li><strong>💾 My Routes</strong> - View saved routes</li>
                <li><strong>🔗 Connect Strava</strong> - Set up authentication</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Getting started guide
        with st.expander("🎯 Getting Started", expanded=False):
            st.markdown("""
            ### Ready to analyze your cycling routes?
            
            **1. Upload a Route** 📁  
            Upload GPX files from Strava, Garmin Connect, RideWithGPS, or any cycling app
            
            **2. View Analysis** 📊  
            Get detailed insights on elevation, gradients, traffic stops, and route complexity
            
            **3. Weather Check** 🌤️  
            Plan your ride with weather forecasting for your route
            
            **4. Save & Compare** 💾  
            Save routes for future reference and compare performance metrics
            """)
        
        # Show system info only for authenticated users (much smaller)
        if self.auth_manager.is_authenticated():
            with st.expander("⚙️ System Status", expanded=False):
                status = self.config.validate_configuration()
                for key, is_valid in status.items():
                    icon = "✅" if is_valid else "❌"
                    st.write(f"{icon} {key.replace('_', ' ').title()}")
        
        log_function_exit(logger, "render_home_page")
    
    @log_execution_time()
    def render_route_upload_page(self):
        """Render the route upload and analysis page."""
        log_function_entry(logger, "render_route_upload_page")
        
        st.markdown("""
        <div class="welcome-section">
            <h2>📈 Upload & Analyze Route</h2>
            <p>Upload your GPX files or select from your recent Strava rides for detailed analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show both options simultaneously
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📁 Upload GPX File")
            # File upload widget - GPX only
            uploaded_file = st.file_uploader(
                "Choose a GPX file",
                type=['gpx'],
                help=f"Upload a GPX file containing your route data (max {self.config.app.max_file_size_mb}MB)"
            )
            
            if uploaded_file is not None:
                self._process_uploaded_file(uploaded_file)
            else:
                st.info("📂 Select a GPX file above to begin route analysis.")
        
        with col2:
            st.markdown("### 🚴 Select from Recent Strava Rides")
            self._render_strava_routes_section()
        
        log_function_exit(logger, "render_route_upload_page")
    
    def _process_uploaded_file(self, uploaded_file):
        """Process uploaded GPX file and render analysis.
        Uses session state to cache processed data and avoid reprocessing.
        """
        log_function_entry(logger, "_process_uploaded_file", filename=uploaded_file.name)
        
        try:
            # Check file size
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > self.config.app.max_file_size_mb:
                st.error(f"❌ File too large ({file_size_mb:.1f}MB). Maximum size is {self.config.app.max_file_size_mb}MB.")
                return
            
            # Create hash of file content for caching
            file_content_bytes = uploaded_file.getvalue()
            file_hash = hashlib.md5(file_content_bytes).hexdigest()
            
            # Check if we have cached data for this file
            cache_key = f"route_data_{file_hash}"
            stats_key = f"route_stats_{file_hash}"
            
            if cache_key in st.session_state and stats_key in st.session_state:
                # Use cached data
                route_data = st.session_state[cache_key]
                stats = st.session_state[stats_key]
                st.success(f"✅ File '{uploaded_file.name}' loaded from cache! ({file_size_mb:.1f}MB)")
                logger.info(f"Using cached data for file: {uploaded_file.name}")
            else:
                # Process the file
                st.success(f"✅ File '{uploaded_file.name}' uploaded successfully! ({file_size_mb:.1f}MB)")
                
                # Process the route with progress indicators
                with st.spinner("Processing route data..."):
                    start_time = time.time()
                    # Create hash for caching
                    file_content_hash = hashlib.md5(file_content_bytes).hexdigest()
                    route_data = self.route_processor.parse_route_file(file_content_hash, file_content_bytes, uploaded_file.name)
                    
                    # Calculate statistics with all advanced analysis enabled
                    route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                    stats = self.route_processor.calculate_route_statistics(
                        route_data_hash,
                        route_data, 
                        include_traffic_analysis=False  # Traffic analysis remains optional for performance
                    )
                    processing_time = time.time() - start_time
                
                # Cache the processed data in session state
                st.session_state[cache_key] = route_data
                st.session_state[stats_key] = stats
                
                logger.info(f"Route processing completed in {processing_time:.2f}s")
            
            # Render route analysis
            self._render_route_analysis(route_data, stats, uploaded_file.name)
            
            log_function_exit(logger, "_process_uploaded_file", "Success")
            
        except Exception as e:
            log_error(logger, e, f"Error processing file: {uploaded_file.name}")
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please ensure you've uploaded a valid GPX file.")
    
    def _render_strava_routes_section(self):
        """Render section for selecting and analyzing recent Strava rides."""
        log_function_entry(logger, "_render_strava_routes_section")
        
        # Check authentication status
        if not self.auth_manager.is_authenticated():
            st.info("🔐 Please connect your Strava account to access your recent rides.")
            st.markdown("👈 Use the **Authentication** section in the sidebar to connect.")
            log_function_exit(logger, "_render_strava_routes_section", "Not authenticated")
            return
        
        # Get recent activities
        if "recent_strava_activities" not in st.session_state or st.button("🔄 Refresh Recent Rides"):
            with st.spinner("Fetching your recent rides from Strava..."):
                try:
                    access_token = st.session_state.get("access_token")
                    
                    # Fetch recent activities with limit of 10 to get 5 rides
                    activities = self.auth_manager.oauth_client.get_athlete_activities(
                        access_token, 
                        page=1, 
                        per_page=10  # Get more than 5 to filter for rides only
                    )
                    
                    # Filter for cycling activities only and limit to 5
                    ride_activities = [
                        activity for activity in activities 
                        if activity.get('type', '').lower() in ['ride', 'virtualride', 'ebikeride']
                    ][:5]  # Take only first 5 rides
                    
                    st.session_state["recent_strava_activities"] = ride_activities
                    logger.info(f"Fetched {len(ride_activities)} recent rides")
                    
                except Exception as e:
                    log_error(logger, e, "Error fetching recent Strava activities")
                    st.error(f"❌ Error fetching recent rides: {str(e)}")
                    st.info("💡 Try refreshing your authentication or check your Strava connection.")
                    log_function_exit(logger, "_render_strava_routes_section", "Error fetching activities")
                    return
        else:
            ride_activities = st.session_state.get("recent_strava_activities", [])
        
        # Display recent rides
        if not ride_activities:
            st.info("📭 No recent rides found. Go cycling and come back!")
            log_function_exit(logger, "_render_strava_routes_section", "No rides found")
            return
        
        st.success(f"✅ Found {len(ride_activities)} recent rides from Strava!")
        
        # Create dropdown selection instead of expanders
        st.markdown("**Select a ride to analyze:**")
        
        # Create options for selectbox
        ride_options = []
        for i, activity in enumerate(ride_activities):
            # Get unit preference for display
            use_imperial = getattr(st.session_state, 'use_imperial', False)
            
            # Extract activity data
            name = activity.get('name', 'Unnamed Ride')
            distance_m = activity.get('distance', 0)
            distance_km = distance_m / 1000
            elevation_gain = activity.get('total_elevation_gain', 0)
            activity_date = activity.get('start_date_local', '').split('T')[0] if activity.get('start_date_local') else 'Unknown date'
            
            # Format units for display
            distance_str = UnitConverter.format_distance(distance_km, use_imperial)
            elevation_str = UnitConverter.format_elevation(elevation_gain, use_imperial)
            
            # Create display text for the option
            display_text = f"{name} - {distance_str}, {elevation_str} ({activity_date})"
            ride_options.append(display_text)
        
        # Add a default "Select a ride" option
        ride_options.insert(0, "-- Select a ride to analyze --")
        
        # Create selectbox for ride selection
        selected_option = st.selectbox(
            "Choose a ride:",
            ride_options,
            key="strava_ride_selector"
        )
        
        # Process the selected ride if a valid selection is made
        if selected_option != "-- Select a ride to analyze --":
            # Find the selected ride by index (subtract 1 for the default option)
            selected_index = ride_options.index(selected_option) - 1
            if 0 <= selected_index < len(ride_activities):
                selected_activity = ride_activities[selected_index]
                
                # Show activity details before analysis
                self._render_selected_activity_details(selected_activity)
                
                # Auto-process the selected activity
                if st.button("📊 Analyze This Ride", key="analyze_selected_strava"):
                    self._process_strava_activity(selected_activity)
        
        log_function_exit(logger, "_render_strava_routes_section", "Success")
    
    def _render_selected_activity_details(self, activity: Dict):
        """Render details of the selected Strava activity."""
        # Get unit preference
        use_imperial = getattr(st.session_state, 'use_imperial', False)
        
        # Extract activity data
        activity_id = activity.get('id')
        name = activity.get('name', 'Unnamed Ride')
        distance_m = activity.get('distance', 0)
        distance_km = distance_m / 1000
        elevation_gain = activity.get('total_elevation_gain', 0)
        activity_date = activity.get('start_date_local', '').split('T')[0] if activity.get('start_date_local') else 'Unknown date'
        moving_time = activity.get('moving_time', 0)
        
        # Format units
        distance_str = UnitConverter.format_distance(distance_km, use_imperial)
        elevation_str = UnitConverter.format_elevation(elevation_gain, use_imperial)
        
        # Format duration
        hours = moving_time // 3600
        minutes = (moving_time % 3600) // 60
        duration_str = f"{hours:02d}:{minutes:02d}" if hours > 0 else f"{minutes} min"
        
        # Display activity details in a compact format
        st.markdown(f"**Selected: {name}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Distance:** {distance_str}")
            st.write(f"**Date:** {activity_date}")
        
        with col2:
            st.write(f"**Elevation:** {elevation_str}")
            st.write(f"**Duration:** {duration_str}")
        
        with col3:
            st.write(f"**Type:** {activity.get('type', 'Ride')}")
            if activity.get('average_speed'):
                avg_speed_ms = activity['average_speed']
                avg_speed_kmh = avg_speed_ms * 3.6
                speed_str = f"{avg_speed_kmh:.1f} km/h"
                if use_imperial:
                    avg_speed_mph = avg_speed_kmh * 0.621371
                    speed_str = f"{avg_speed_mph:.1f} mph"
                st.write(f"**Avg Speed:** {speed_str}")
    
    def _render_strava_activity_item(self, activity: Dict, index: int):
        """Render a single Strava activity item for selection.
        
        NOTE: This method is now deprecated in favor of dropdown selection.
        Keeping for backward compatibility but should not be used.
        """
        # This method is kept for compatibility but is no longer used
        # since we switched to dropdown selection
        pass
    
    def _process_strava_activity(self, activity: Dict):
        """Process and analyze a selected Strava activity."""
        log_function_entry(logger, "_process_strava_activity", activity_id=activity.get('id'))
        
        activity_id = activity.get('id')
        activity_name = activity.get('name', 'Strava Ride')
        
        # Create cache key for this Strava activity
        cache_key = f"strava_route_data_{activity_id}"
        stats_key = f"strava_route_stats_{activity_id}"
        
        # Check if we have cached data for this activity
        if cache_key in st.session_state and stats_key in st.session_state:
            # Use cached data
            route_data = st.session_state[cache_key]
            stats = st.session_state[stats_key]
            st.success(f"✅ Strava ride '{activity_name}' loaded from cache!")
            logger.info(f"Using cached data for Strava activity: {activity_id}")
            
            # Render analysis using the same function as uploaded files
            self._render_route_analysis(route_data, stats, f"Strava: {activity_name}")
            log_function_exit(logger, "_process_strava_activity", "Success - from cache")
            return

        with st.spinner(f"Fetching GPS data for '{activity_name}'..."):
            try:
                access_token = st.session_state.get("access_token")
                
                # Get activity streams (GPS data)
                streams = self.auth_manager.oauth_client.get_activity_streams(
                    access_token, 
                    str(activity_id),
                    keys="latlng,elevation,time"  # Get GPS coordinates, elevation, and time
                )
                
                # Check if we have GPS data
                if not streams or 'latlng' not in streams:
                    st.error("❌ This activity doesn't contain GPS data. It might be an indoor ride or the GPS wasn't enabled.")
                    return
                
                # Convert Strava streams to route format
                route_data = self._convert_strava_streams_to_route(streams, activity)
                
                # Calculate route statistics using the same processor as uploaded files
                with st.spinner("Processing route data..."):
                    start_time = time.time()
                    route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                    stats = self.route_processor.calculate_route_statistics(
                        route_data_hash,
                        route_data, 
                        include_traffic_analysis=False  # Traffic analysis remains optional for performance
                    )
                    processing_time = time.time() - start_time
                
                # Cache the processed data in session state (same as uploaded files)
                st.session_state[cache_key] = route_data
                st.session_state[stats_key] = stats
                
                logger.info(f"Strava activity processing completed in {processing_time:.2f}s")
                
                # Render analysis using the same function as uploaded files
                st.success(f"✅ Successfully loaded GPS data for '{activity_name}'!")
                self._render_route_analysis(route_data, stats, f"Strava: {activity_name}")
                
                log_function_exit(logger, "_process_strava_activity", "Success")
                
            except Exception as e:
                log_error(logger, e, f"Error processing Strava activity: {activity_id}")
                st.error(f"❌ Error analyzing ride: {str(e)}")
                
                # Provide helpful suggestions
                if "not found" in str(e).lower():
                    st.info("💡 This activity might be private or no longer available.")
                elif "streams" in str(e).lower():
                    st.info("💡 This activity doesn't have GPS data or it's not accessible.")
                else:
                    st.info("💡 Try selecting a different ride or check your Strava connection.")
    
    def _convert_strava_streams_to_route(self, streams: Dict, activity: Dict) -> Dict:
        """Convert Strava activity streams to KOMpass route format."""
        log_function_entry(logger, "_convert_strava_streams_to_route")
        
        # Extract stream data
        latlng_data = streams.get('latlng', {}).get('data', [])
        elevation_data = streams.get('elevation', {}).get('data', [])
        time_data = streams.get('time', {}).get('data', [])
        
        if not latlng_data:
            raise ValueError("No GPS coordinates found in activity streams")
        
        # Create route points
        route_points = []
        for i, latlng in enumerate(latlng_data):
            if len(latlng) >= 2:  # Ensure we have lat/lng
                point = {
                    'lat': latlng[0],
                    'lon': latlng[1],
                    'elevation': elevation_data[i] if i < len(elevation_data) else None,
                    'time': time_data[i] if i < len(time_data) else None
                }
                route_points.append(point)
        
        # Create route data structure compatible with KOMpass
        route_data = {
            'tracks': [{
                'name': activity.get('name', 'Strava Activity'),
                'segments': [route_points]
            }],
            'routes': [],
            'waypoints': [],
            'metadata': {
                'name': activity.get('name', 'Strava Activity'),
                'description': f"Strava activity from {activity.get('start_date_local', 'unknown date')}",
                'time': activity.get('start_date_local'),
                'source': 'Strava',
                'activity_id': activity.get('id'),
                'activity_type': activity.get('type'),
                'strava_data': {
                    'distance': activity.get('distance'),
                    'moving_time': activity.get('moving_time'),
                    'total_elevation_gain': activity.get('total_elevation_gain'),
                    'average_speed': activity.get('average_speed')
                }
            }
        }
        
        logger.info(f"Converted Strava activity to route data: {len(route_points)} points")
        log_function_exit(logger, "_convert_strava_streams_to_route", "Success")
        
        return route_data
    
    def _render_route_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """Render comprehensive route analysis."""
        log_function_entry(logger, "_render_route_analysis", filename=filename)
        
        # Basic route statistics (always shown)
        self._render_basic_stats(stats)
        
        # Essential gradient analysis (fast, always included)
        if stats.get('gradient_analysis'):
            self._render_gradient_analysis(stats['gradient_analysis'])
        
        # Show key summary stats only
        st.subheader("📋 Route Summary")
        col1, col2, col3 = st.columns(3)
        
        gradient_analysis = stats.get('gradient_analysis', {})
        with col1:
            terrain_type = self._get_simple_terrain_type(gradient_analysis)
            st.metric("Terrain Type", terrain_type)
            if gradient_analysis.get('average_gradient_percent'):
                st.metric("Avg Gradient", f"{gradient_analysis.get('average_gradient_percent', 0)}%")
        
        with col2:
            if gradient_analysis.get('steep_climbs_percent'):
                st.metric("Steep Sections", f"{gradient_analysis.get('steep_climbs_percent', 0)}%")
            if gradient_analysis.get('max_gradient_percent'):
                st.metric("Max Gradient", f"{gradient_analysis.get('max_gradient_percent', 0)}%")
        
        with col3:
            # Calculate a simple difficulty score
            difficulty = self._calculate_simple_difficulty(stats, gradient_analysis)
            st.metric("Difficulty Rating", difficulty)
            if stats.get('total_points'):
                point_density = stats['total_points'] / max(stats.get('total_distance_km', 1), 0.1)
                st.metric("Route Detail", f"{point_density:.0f} pts/km")
        
        # Add hill detection and route complexity explanations
        with st.expander("🔍 Analysis Methodology", expanded=False):
            self._render_analysis_methodology()
        
        # Elevation profile graph
        if route_data and self._has_elevation_data(route_data):
            st.subheader("📊 Elevation Profile")
            self._render_elevation_graph(route_data, stats)
        
        # Advanced analysis options (expandable)
        with st.expander("🔬 Advanced Analysis", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Option to enable traffic analysis
                if st.button("🚦 Analyze Traffic Stops", help="Analyze potential traffic lights and road crossings (may take 10-30 seconds)"):
                    self._perform_traffic_analysis(route_data, stats, filename)
            
            with col2:
                # Option to generate detailed dataframe
                if st.button("📊 Generate Detailed Analysis", help="Create comprehensive dataframe with all route data"):
                    self._generate_detailed_dataframe(route_data, stats)
        
        # Show detailed metrics if they exist
        if stats.get('climb_analysis') and stats['climb_analysis'].get('climb_count', 0) > 0:
            with st.expander("🚴‍♂️ Detailed Climbing Analysis", expanded=False):
                self._render_climb_analysis(stats['climb_analysis'])
        
        if stats.get('complexity_analysis'):
            with st.expander("🛣️ Route Complexity Analysis", expanded=False):
                self._render_complexity_analysis(stats['complexity_analysis'], stats.get('ml_features', {}))
        
        if stats.get('terrain_analysis'):
            with st.expander("🏔️ Terrain Analysis", expanded=False):
                self._render_terrain_analysis(stats['terrain_analysis'], {})
        
        if stats.get('traffic_analysis', {}).get('analysis_available'):
            with st.expander("🚦 Traffic Analysis Results", expanded=True):
                self._render_traffic_analysis(stats['traffic_analysis'])
        
        # ML features are now hidden as requested - data still collected for backend ML use
        # if stats.get('ml_features'):
        #     with st.expander("🤖 ML Features & Advanced Metrics", expanded=False):
        #         self._render_ml_features(stats['ml_features'])
        
        # Automatically generate and cache comprehensive dataframe for ML use
        try:
            route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
            df = self.route_processor.create_analysis_dataframe(route_data_hash, route_data, stats)
            if not df.empty:
                # Cache the dataframe for ML use
                route_name = route_data.get('metadata', {}).get('name', filename)
                cache_key = f"analysis_dataframe_{hash(str(route_data))}"
                st.session_state[cache_key] = df
                st.session_state['latest_analysis_dataframe'] = df  # Always keep latest
                logger.info(f"Cached comprehensive dataframe for route: {route_name}")
        except Exception as e:
            logger.warning(f"Could not cache dataframe: {e}")

        # Weather analysis section
        self._render_weather_analysis_section(route_data, stats)
        
        # Route metadata
        self._render_route_metadata(route_data)
        
        # Route visualization
        self._render_route_visualization(route_data, stats)
        
        # Save route option
        self._render_save_route_section(route_data, stats)
        
        log_function_exit(logger, "_render_route_analysis")
    
    def _get_simple_terrain_type(self, gradient_analysis: Dict) -> str:
        """Get a simple terrain classification."""
        if not gradient_analysis:
            return "Unknown"
        
        steep_pct = gradient_analysis.get('steep_climbs_percent', 0)
        moderate_pct = gradient_analysis.get('moderate_climbs_percent', 0)
        
        if steep_pct > 20:
            return "Mountainous"
        elif moderate_pct + steep_pct > 30:
            return "Hilly"
        elif moderate_pct + steep_pct > 10:
            return "Rolling"
        else:
            return "Flat"
    
    def _calculate_simple_difficulty(self, stats: Dict, gradient_analysis: Dict) -> str:
        """Calculate a simple difficulty rating."""
        if not gradient_analysis:
            return "Unknown"
        
        distance_km = stats.get('total_distance_km', 0)
        elevation_gain = stats.get('total_elevation_gain_m', 0)
        steep_pct = gradient_analysis.get('steep_climbs_percent', 0)
        
        # Simple difficulty calculation
        difficulty_score = 0
        if distance_km > 50:
            difficulty_score += 2
        elif distance_km > 20:
            difficulty_score += 1
        
        if elevation_gain > 1000:
            difficulty_score += 2
        elif elevation_gain > 500:
            difficulty_score += 1
        
        if steep_pct > 15:
            difficulty_score += 2
        elif steep_pct > 5:
            difficulty_score += 1
        
        if difficulty_score <= 1:
            return "Easy"
        elif difficulty_score <= 3:
            return "Moderate"
        elif difficulty_score <= 5:
            return "Hard"
        else:
            return "Very Hard"
    
    def _perform_traffic_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """Perform traffic analysis asynchronously."""
        with st.spinner("Analyzing traffic stops... This may take 10-30 seconds."):
            try:
                # Re-calculate with traffic analysis enabled
                route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                full_stats = self.route_processor.calculate_route_statistics(
                    route_data_hash,
                    route_data, 
                    include_traffic_analysis=True
                )
                
                # Update the session state with new stats
                file_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                stats_key = f"route_stats_{file_hash}"
                st.session_state[stats_key] = full_stats
                
                # Show traffic results
                if full_stats.get('traffic_analysis', {}).get('analysis_available'):
                    st.success("✅ Traffic analysis completed!")
                    self._render_traffic_analysis(full_stats['traffic_analysis'])
                else:
                    reason = full_stats.get('traffic_analysis', {}).get('reason', 'Unknown error')
                    st.warning(f"⚠️ Traffic analysis unavailable: {reason}")
                    
            except Exception as e:
                st.error(f"❌ Error during traffic analysis: {str(e)}")
    
    def _generate_detailed_dataframe(self, route_data: Dict, stats: Dict):
        """Generate and display detailed analysis dataframe."""
        with st.spinner("Creating detailed analysis dataframe..."):
            try:
                # Create the dataframe
                route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                df = self.route_processor.create_analysis_dataframe(route_data_hash, route_data, stats)
                
                if not df.empty:
                    # Cache the dataframe for ML use
                    route_name = route_data.get('metadata', {}).get('name', 'route')
                    cache_key = f"analysis_dataframe_{route_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    st.session_state[cache_key] = df
                    st.session_state['latest_analysis_dataframe'] = df  # Always keep latest
                    
                    st.success(f"✅ Detailed analysis dataframe created and cached for ML use!")
                    
                    # Show dataframe summary
                    st.subheader("📊 Route Data Overview")
                    st.write(f"**Points:** {len(df)} | **Columns:** {len(df.columns)}")
                    
                    # Show summary statistics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Distance Statistics:**")
                        st.write(f"• Total: {df['cumulative_distance_m'].max()/1000:.2f} km")
                        st.write(f"• Avg segment: {df['distance_from_previous_m'].mean():.1f} m")
                    
                    with col2:
                        st.write("**Elevation Statistics:**")
                        if 'elevation_m' in df.columns and df['elevation_m'].notna().any():
                            st.write(f"• Range: {df['elevation_m'].min():.0f} - {df['elevation_m'].max():.0f} m")
                            st.write(f"• Avg gradient: {df['gradient_percent'].mean():.1f}%")
                    
                    # Show sample of the dataframe
                    st.subheader("📋 Data Sample")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Download option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Full Dataset as CSV",
                        data=csv,
                        file_name=f"route_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
                    # Show metadata if available
                    if hasattr(df, 'attrs') and df.attrs:
                        with st.expander("📝 Analysis Metadata", expanded=False):
                            st.json(df.attrs)
                            
                    # Info about caching for ML
                    st.info("💡 **ML Ready**: This comprehensive dataset is now cached and ready for machine learning analysis.")
                else:
                    st.warning("⚠️ No data available to create dataframe")
                    
            except Exception as e:
                st.error(f"❌ Error creating dataframe: {str(e)}")
    
    @st.fragment  # Independent fragment for basic stats
    def _render_basic_stats(self, stats: Dict):
        """Render basic route statistics as an independent fragment."""
        st.subheader("📊 Basic Route Statistics")
        
        # Get unit preference
        use_imperial = getattr(st.session_state, 'use_imperial', False)
        
        # Convert stats if needed
        converted_stats = UnitConverter.convert_route_stats(stats, use_imperial)
        units = converted_stats.get('_units', {'distance': 'km', 'elevation': 'm'})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if use_imperial and 'total_distance_mi' in converted_stats:
                st.metric("Distance", f"{converted_stats['total_distance_mi']:.2f} {units['distance']}")
            else:
                st.metric("Distance", f"{stats['total_distance_km']:.2f} {units['distance']}")
            st.metric("Total Points", stats['total_points'])
        
        with col2:
            if stats['total_elevation_gain_m'] > 0:
                if use_imperial and 'total_elevation_gain_ft' in converted_stats:
                    st.metric("Elevation Gain", f"{converted_stats['total_elevation_gain_ft']:.0f} {units['elevation']}")
                else:
                    st.metric("Elevation Gain", f"{stats['total_elevation_gain_m']:.0f} {units['elevation']}")
            if stats['max_elevation_m'] is not None:
                if use_imperial and 'max_elevation_ft' in converted_stats:
                    st.metric("Max Elevation", f"{converted_stats['max_elevation_ft']:.0f} {units['elevation']}")
                else:
                    st.metric("Max Elevation", f"{stats['max_elevation_m']:.0f} {units['elevation']}")
        
        with col3:
            if stats['total_elevation_loss_m'] > 0:
                if use_imperial and 'total_elevation_loss_ft' in converted_stats:
                    st.metric("Elevation Loss", f"{converted_stats['total_elevation_loss_ft']:.0f} {units['elevation']}")
                else:
                    st.metric("Elevation Loss", f"{stats['total_elevation_loss_m']:.0f} {units['elevation']}")
            if stats['min_elevation_m'] is not None:
                if use_imperial and 'min_elevation_ft' in converted_stats:
                    st.metric("Min Elevation", f"{converted_stats['min_elevation_ft']:.0f} {units['elevation']}")
                else:
                    st.metric("Min Elevation", f"{stats['min_elevation_m']:.0f} {units['elevation']}")
    
    @st.fragment  # Independent fragment for gradient analysis
    def _render_gradient_analysis(self, gradient: Dict):
        """Render gradient analysis section as an independent fragment."""
        st.subheader("⛰️ Gradient Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Gradient", f"{gradient.get('average_gradient_percent', 0)}%")
            st.metric("Max Gradient", f"{gradient.get('max_gradient_percent', 0)}%")
        
        with col2:
            st.metric("Steep Climbs", f"{gradient.get('steep_climbs_percent', 0)}%")
            st.metric("Moderate Climbs", f"{gradient.get('moderate_climbs_percent', 0)}%")
        
        with col3:
            st.metric("Flat Sections", f"{gradient.get('flat_sections_percent', 0)}%")
            st.metric("Descents", f"{gradient.get('descents_percent', 0)}%")
        
        with col4:
            st.metric("Min Gradient", f"{gradient.get('min_gradient_percent', 0)}%")
            st.metric("Gradient Std Dev", f"{gradient.get('gradient_std_dev', 0)}%")
    
    @st.fragment  # Independent fragment for climb analysis
    def _render_climb_analysis(self, climb: Dict):
        """Render climbing analysis section as an independent fragment."""
        st.subheader("🚴‍♂️ Climbing Analysis")
        
        # Get unit preference
        use_imperial = getattr(st.session_state, 'use_imperial', False)
        units = UnitConverter.convert_route_stats({'climb_analysis': climb}, use_imperial)
        climb_converted = units.get('climb_analysis', climb)
        unit_labels = units.get('_units', {'distance': 'km', 'elevation': 'm'})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Number of Climbs", climb.get('climb_count', 0))
            if use_imperial and 'total_climb_distance_mi' in climb_converted:
                st.metric("Total Climb Distance", f"{climb_converted['total_climb_distance_mi']:.2f} {unit_labels['distance']}")
            else:
                st.metric("Total Climb Distance", f"{climb.get('total_climb_distance_km', 0):.2f} {unit_labels['distance']}")
        
        with col2:
            if use_imperial and 'average_climb_length_ft' in climb_converted:
                st.metric("Avg Climb Length", f"{climb_converted['average_climb_length_ft']:.0f} {unit_labels['elevation']}")
            else:
                st.metric("Avg Climb Length", f"{climb.get('average_climb_length_m', 0):.0f} {unit_labels['elevation']}")
            st.metric("Avg Climb Gradient", f"{climb.get('average_climb_gradient', 0)}%")
        
        with col3:
            st.metric("Max Climb Gradient", f"{climb.get('max_climb_gradient', 0)}%")
            st.metric("Climb Difficulty Score", f"{climb.get('climb_difficulty_score', 0)}")
    
    @st.fragment  # Independent fragment for complexity analysis
    def _render_complexity_analysis(self, complexity: Dict, ml_features: Dict):
        """Render route complexity analysis as an independent fragment."""
        st.subheader("🛣️ Route Complexity")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Significant Turns", complexity.get('significant_turns_count', 0))
            st.metric("Moderate Turns", complexity.get('moderate_turns_count', 0))
        
        with col2:
            st.metric("Avg Direction Change", f"{complexity.get('average_direction_change_deg', 0)}°")
            st.metric("Route Straightness", f"{complexity.get('route_straightness_index', 0):.3f}")
        
        with col3:
            st.metric("Complexity Score", f"{complexity.get('complexity_score', 0)}")
            if ml_features.get('route_compactness'):
                st.metric("Route Compactness", f"{ml_features.get('route_compactness', 0)}")
    
    def _has_elevation_data(self, route_data: Dict) -> bool:
        """Check if route data contains elevation information."""
        try:
            for track in route_data.get('tracks', []):
                for segment in track.get('segments', []):
                    for point in segment:
                        if point.get('elevation') is not None:
                            return True
            return False
        except:
            return False
    
    def _render_elevation_graph(self, route_data: Dict, stats: Dict):
        """Render elevation profile graph using Streamlit's native charting."""
        import pandas as pd
        
        try:
            # Extract elevation data with cumulative distance
            elevation_data = []
            cumulative_distance = 0.0
            prev_point = None
            
            for track in route_data.get('tracks', []):
                for segment in track.get('segments', []):
                    for point in segment:
                        elevation = point.get('elevation')
                        if elevation is not None:
                            # Calculate distance from previous point
                            if prev_point is not None:
                                from ..processing.route_processor import haversine_distance
                                distance_km = haversine_distance(
                                    prev_point['lat'], prev_point['lon'],
                                    point['lat'], point['lon']
                                )
                                cumulative_distance += distance_km
                            
                            elevation_data.append({
                                'Distance (km)': cumulative_distance,
                                'Elevation (m)': elevation
                            })
                            prev_point = point
            
            if not elevation_data:
                st.info("📊 No elevation data available for graphing.")
                return
            
            # Create DataFrame
            df = pd.DataFrame(elevation_data)
            
            # Use unit converter for proper display
            use_imperial = getattr(st.session_state, 'use_imperial', False)
            if use_imperial:
                df['Distance (mi)'] = df['Distance (km)'] * 0.621371
                df['Elevation (ft)'] = df['Elevation (m)'] * 3.28084
                st.line_chart(df.set_index('Distance (mi)')['Elevation (ft)'], height=300)
            else:
                st.line_chart(df.set_index('Distance (km)')['Elevation (m)'], height=300)
            
            # Add elevation statistics below the graph
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                min_elev = df['Elevation (m)'].min()
                if use_imperial:
                    st.metric("Min Elevation", f"{min_elev * 3.28084:.0f} ft")
                else:
                    st.metric("Min Elevation", f"{min_elev:.0f} m")
            
            with col2:
                max_elev = df['Elevation (m)'].max()
                if use_imperial:
                    st.metric("Max Elevation", f"{max_elev * 3.28084:.0f} ft")
                else:
                    st.metric("Max Elevation", f"{max_elev:.0f} m")
            
            with col3:
                elev_gain = max_elev - min_elev
                if use_imperial:
                    st.metric("Elevation Range", f"{elev_gain * 3.28084:.0f} ft")
                else:
                    st.metric("Elevation Range", f"{elev_gain:.0f} m")
            
            with col4:
                total_distance = df['Distance (km)'].max()
                if use_imperial:
                    st.metric("Total Distance", f"{total_distance * 0.621371:.2f} mi")
                else:
                    st.metric("Total Distance", f"{total_distance:.2f} km")
                    
        except Exception as e:
            logger.error(f"Error rendering elevation graph: {e}")
            st.error("❌ Error creating elevation graph. Please try again.")

    def _render_analysis_methodology(self):
        """Render information about analysis methodology and metrics."""
        st.subheader("📚 How We Analyze Your Route")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏔️ Hill Detection")
            st.markdown("""
            **What counts as a hill:**
            - **Start of climb**: Gradient > 3% for at least 10m
            - **Continue climb**: Gradient > 1% 
            - **End of climb**: Gradient ≤ 1% or route ends
            - **Minimum climb**: Only hills with >10m elevation gain are counted
            
            **Gradient Categories:**
            - 🟢 **Flat**: 0-3% gradient
            - 🟡 **Rolling**: 3-6% gradient  
            - 🟠 **Moderate**: 6-10% gradient
            - 🔴 **Steep**: >10% gradient
            """)
            
        with col2:
            st.markdown("#### 🛣️ Route Complexity Metrics")
            st.markdown("""
            **Straightness Index:**
            - Ratio of direct distance to actual route distance
            - 1.0 = perfectly straight, lower = more winding
            
            **Average Turn Angle:**
            - Mean absolute bearing change between segments
            - Higher values = more turns and direction changes
            
            **Route Compactness:**
            - Route distance vs. bounding box diagonal
            - Indicates how much the route explores an area
            
            **Difficulty Index:**
            - Combines gradient percentages and complexity
            - Scale: 0-1 (higher = more challenging)
            """)
    
    @st.fragment  # Independent fragment for terrain analysis
    def _render_terrain_analysis(self, terrain: Dict, power: Dict):
        """Render terrain analysis without power assumptions as an independent fragment."""
        st.subheader("🏔️ Terrain Classification")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Terrain Type", terrain.get('terrain_type', 'Unknown'))
        
        with col2:
            terrain_dist = terrain.get('terrain_distribution', {})
            st.metric("Flat Sections", f"{terrain_dist.get('flat_percent', 0):.1f}%")
            st.metric("Rolling Hills", f"{terrain_dist.get('rolling_percent', 0):.1f}%")
        
        with col3:
            st.metric("Moderate Climbs", f"{terrain_dist.get('moderate_climbs_percent', 0):.1f}%")
            st.metric("Steep Climbs", f"{terrain_dist.get('steep_climbs_percent', 0):.1f}%")
    
    @st.fragment  # Independent fragment for traffic analysis
    def _render_traffic_analysis(self, traffic: Dict):
        """Render traffic stop analysis as an independent fragment."""
        st.subheader("🚦 Traffic Stop Analysis")
        
        if traffic.get('analysis_available'):
            # Get unit preference
            use_imperial = getattr(st.session_state, 'use_imperial', False)
            units = UnitConverter.convert_route_stats({'traffic_analysis': traffic}, use_imperial)
            traffic_converted = units.get('traffic_analysis', traffic)
            unit_labels = units.get('_units', {'distance': 'km'})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Traffic Lights", traffic.get('traffic_lights_detected', 0))
                st.metric("Major Road Crossings", traffic.get('major_road_crossings', 0))
            
            with col2:
                st.metric("Total Potential Stops", traffic.get('total_potential_stops', 0))
                if use_imperial and 'stop_density_per_mi' in traffic_converted:
                    st.metric("Stop Density", f"{traffic_converted['stop_density_per_mi']:.2f} stops/{unit_labels['distance']}")
                else:
                    st.metric("Stop Density", f"{traffic.get('stop_density_per_km', 0):.2f} stops/{unit_labels['distance']}")
            
            with col3:
                if use_imperial and 'average_distance_between_stops_mi' in traffic_converted:
                    st.metric("Avg Distance Between Stops", f"{traffic_converted['average_distance_between_stops_mi']:.2f} {unit_labels['distance']}")
                else:
                    st.metric("Avg Distance Between Stops", f"{traffic.get('average_distance_between_stops_km', 0):.2f} {unit_labels['distance']}")
                st.metric("Est. Time Penalty", f"{traffic.get('estimated_time_penalty_minutes', 0):.1f} min")
            
            # Additional traffic info
            if traffic.get('infrastructure_summary'):
                summary = traffic['infrastructure_summary']
                st.info(f"🚦 Found {summary.get('total_traffic_lights_in_area', 0)} traffic lights and "
                       f"{summary.get('total_major_roads_in_area', 0)} major roads in route area. "
                       f"Identified {summary.get('route_intersections_found', 0)} potential stops on your route.")
        else:
            reason = traffic.get('reason', 'Unknown error')
            st.warning(f"⚠️ Traffic analysis unavailable: {reason}")
            if 'Unable to calculate' in reason:
                st.info("💡 Traffic stop analysis requires an internet connection to query OpenStreetMap data.")
    
    def _render_ml_features(self, ml_features: Dict):
        """Render ML features summary."""
        st.subheader("🤖 ML Training Features")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Route Density", f"{ml_features.get('route_density_points_per_km', 0)} pts/km")
            st.metric("Difficulty Index", f"{ml_features.get('difficulty_index', 0):.3f}")
        
        with col2:
            st.metric("Route Compactness", f"{ml_features.get('route_compactness', 0)}")
            st.metric("Elevation Range", f"{ml_features.get('elevation_range_m', 0)} m")
        
        with col3:
            if ml_features.get('stop_density_per_km') is not None:
                st.metric("Stop Density", f"{ml_features.get('stop_density_per_km', 0)} stops/km")
            if ml_features.get('traffic_complexity_factor') is not None:
                st.metric("Traffic Complexity", f"{ml_features.get('traffic_complexity_factor', 0):.3f}")
        
        with col4:
            if ml_features.get('estimated_stop_time_penalty_min') is not None:
                st.metric("Stop Time Penalty", f"{ml_features.get('estimated_stop_time_penalty_min', 0)} min")
            st.metric("Elevation Variation", f"{ml_features.get('elevation_variation_index', 0)} m/km")
    
    @st.fragment  # Independent fragment for weather analysis input
    def _render_weather_analysis_section(self, route_data: Dict, stats: Dict):
        """Render weather analysis section as an independent fragment."""
        st.subheader("🌤️ Weather Analysis & Planning")
        
        # Weather input controls
        col1, col2 = st.columns(2)
        
        with col1:
            departure_date = st.date_input(
                "Planned Departure Date",
                value=datetime.now().date(),
                min_value=datetime.now().date(),
                max_value=datetime.now().date() + timedelta(days=self.config.weather.max_forecast_days),
                help=f"Weather forecasts are available up to {self.config.weather.max_forecast_days} days in advance"
            )
        
        with col2:
            departure_time = st.time_input(
                "Planned Departure Time",
                value=datetime.now().time().replace(minute=0, second=0, microsecond=0),
                help="Enter your planned start time"
            )
        
        departure_datetime = datetime.combine(departure_date, departure_time)
        
        # Weather analysis button
        if st.button("🌤️ Analyze Weather Conditions"):
            self._process_weather_analysis(route_data, departure_datetime)
        else:
            st.info("📅 Select your departure date and time above, then click 'Analyze Weather Conditions' to get detailed weather forecasts for your ride.")
    
    @log_execution_time()
    def _process_weather_analysis(self, route_data: Dict, departure_datetime: datetime):
        """Process weather analysis for the route."""
        log_function_entry(logger, "_process_weather_analysis", departure=departure_datetime.isoformat())
        
        with st.spinner("Analyzing weather conditions along your route..."):
            try:
                # Collect all route points
                all_points = []
                for track in route_data.get('tracks', []):
                    for segment in track.get('segments', []):
                        all_points.extend(segment)
                for route in route_data.get('routes', []):
                    all_points.extend(route.get('points', []))
                
                if not all_points:
                    st.error("❌ Unable to analyze weather - no route points found")
                    return
                
                # Get comprehensive weather analysis
                route_points_hash = hashlib.md5(str([(p['lat'], p['lon']) for p in all_points]).encode()).hexdigest()
                weather_analysis = self.weather_analyzer.get_comprehensive_weather_analysis(
                    route_points_hash, all_points, departure_datetime, 2.0  # Default 2-hour duration estimate
                )
                
                if weather_analysis.get('analysis_available'):
                    self._render_weather_results(weather_analysis)
                else:
                    error_reason = weather_analysis.get('reason', 'Unknown error')
                    st.warning(f"⚠️ Weather analysis unavailable: {error_reason}")
                    
                    if "API" in error_reason or "request" in error_reason.lower():
                        st.info("💡 Weather analysis requires an internet connection to access forecast data.")
                
                log_function_exit(logger, "_process_weather_analysis", "Success")
                
            except Exception as e:
                log_error(logger, e, "Error processing weather analysis")
                st.error(f"❌ Error analyzing weather: {str(e)}")
    
    def _render_weather_results(self, weather_analysis: Dict):
        """Render weather analysis results."""
        st.success("✅ Weather analysis completed!")
        
        # Display key weather metrics
        col1, col2, col3, col4 = st.columns(4)
        
        # Wind analysis
        wind_data = weather_analysis.get('wind_analysis', {})
        if wind_data.get('analysis_available'):
            with col1:
                st.metric(
                    "Avg Wind Impact", 
                    f"{wind_data.get('avg_headwind_component_kmh', 0)} km/h",
                    help="Positive = headwind, Negative = tailwind"
                )
                st.metric("Max Headwind", f"{wind_data.get('max_headwind_kmh', 0)} km/h")
        
        # Rain analysis
        rain_data = weather_analysis.get('precipitation_analysis', {})
        if rain_data.get('analysis_available'):
            with col2:
                st.metric("Max Rain Chance", f"{rain_data.get('max_precipitation_probability', 0)}%")
                st.metric("Expected Rain", f"{rain_data.get('expected_total_precipitation_mm', 0)} mm")
        
        # Temperature analysis
        temp_data = weather_analysis.get('temperature_analysis', {})
        if temp_data.get('analysis_available'):
            with col3:
                st.metric(
                    "Temperature Range", 
                    f"{temp_data.get('min_temperature_c', 0)}° - {temp_data.get('max_temperature_c', 0)}°C"
                )
                st.metric("Heat Stress Periods", f"{temp_data.get('high_heat_periods', 0)}")
        
        # Weather recommendations
        recommendations = weather_analysis.get('recommendations', [])
        if recommendations:
            st.subheader("🎯 Weather Recommendations")
            for rec in recommendations:
                if "warning" in rec.lower() or "extreme" in rec.lower() or "high chance" in rec.lower():
                    st.warning(rec)
                elif "good" in rec.lower() or "favorable" in rec.lower():
                    st.success(rec)
                else:
                    st.info(rec)
        
        # Detailed weather breakdown in expander
        with st.expander("📊 Detailed Weather Analysis"):
            self._render_detailed_weather_breakdown(wind_data, rain_data, temp_data)
    
    def _render_detailed_weather_breakdown(self, wind_data: Dict, rain_data: Dict, temp_data: Dict):
        """Render detailed weather breakdown."""
        # Wind details
        if wind_data.get('analysis_available'):
            st.write("**🌪️ Wind Conditions**")
            wind_summary = wind_data.get('wind_impact_summary', '')
            if wind_summary:
                st.write(f"• {wind_summary}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"• Strong headwind sections: {wind_data.get('strong_headwind_sections', 0)}")
            with col2:
                st.write(f"• Tailwind sections: {wind_data.get('tailwind_sections', 0)}")
            with col3:
                st.write(f"• Max tailwind: {wind_data.get('max_tailwind_kmh', 0)} km/h")
        
        # Rain details
        if rain_data.get('analysis_available'):
            st.write("**🌧️ Precipitation Conditions**")
            rain_summary = rain_data.get('rain_risk_summary', '')
            if rain_summary:
                st.write(f"• {rain_summary}")
            st.write(f"• High rain risk periods: {rain_data.get('high_rain_risk_periods', 0)}")
        
        # Temperature details
        if temp_data.get('analysis_available'):
            st.write("**🌡️ Temperature Conditions**")
            heat_summary = temp_data.get('heat_stress_summary', '')
            if heat_summary:
                st.write(f"• {heat_summary}")
            st.write(f"• Average temperature: {temp_data.get('avg_temperature_c', 0)}°C")
            st.write(f"• Temperature variation: {temp_data.get('temperature_range_c', 0)}°C")
    
    @st.fragment  # Independent fragment for route metadata
    def _render_route_metadata(self, route_data: Dict):
        """Render route metadata section as an independent fragment."""
        if route_data.get('metadata'):
            st.subheader("📋 Route Information")
            metadata = route_data['metadata']
            
            if metadata.get('name'):
                st.write(f"**Name:** {metadata['name']}")
            if metadata.get('description'):
                st.write(f"**Description:** {metadata['description']}")
            if metadata.get('time'):
                st.write(f"**Created:** {metadata['time']}")
    
    @st.fragment  # Independent fragment for route visualization
    @log_execution_time()
    def _render_route_visualization(self, route_data: Dict, stats: Dict):
        """Render route map visualization as an independent fragment."""
        st.subheader("🗺️ Route Visualization")
        
        # Create hash for caching the visualization
        route_hash = hashlib.md5(str(route_data).encode()).hexdigest()
        map_cache_key = f"route_map_{route_hash}"
        
        # Check if we have a cached map
        if map_cache_key in st.session_state:
            route_map = st.session_state[map_cache_key]
            logger.info("Using cached route map")
        else:
            with st.spinner("Generating map..."):
                try:
                    route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                    route_map = self.route_processor.create_route_map(route_data_hash, route_data, stats)
                    # Cache the map in session state
                    st.session_state[map_cache_key] = route_map
                    logger.info("Route map generated and cached successfully")
                except Exception as e:
                    log_error(logger, e, "Error generating route map")
                    st.error(f"❌ Error generating map: {str(e)}")
                    return
        
        # Add custom CSS to prevent map flickering with feature group support
        st.markdown("""
        <style>
        /* Folium map container stabilization */
        .stApp iframe[title="streamlit_folium.st_folium"] {
            border: none !important;
            transition: none !important;
            animation: none !important;
            transform: none !important;
            will-change: auto !important;
            contain: layout style paint !important;
        }
        
        /* Prevent container reflows during map initialization */
        div[data-testid="stVerticalBlock"] > div:has(iframe[title="streamlit_folium.st_folium"]) {
            min-height: 500px;
            position: relative;
            overflow: hidden;
            contain: layout !important;
        }
        
        /* Stabilize map wrapper with better containment */
        .stApp .element-container:has(iframe[title="streamlit_folium.st_folium"]) {
            transition: none !important;
            animation: none !important;
            contain: layout style !important;
            isolation: isolate !important;
        }
        
        /* Optimize iframe rendering for feature groups */
        .stApp iframe {
            backface-visibility: hidden;
            perspective: 1000px;
            transform: translateZ(0);
            contain: strict !important;
            will-change: auto !important;
        }
        
        /* Prevent Leaflet layer flashing during feature group updates */
        .leaflet-container {
            background: #f8f9fa !important;
        }
        
        .leaflet-layer {
            will-change: auto !important;
            transform: translateZ(0) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display the map with enhanced stability parameters
        st_folium(
            route_map, 
            height=500, 
            use_container_width=True, 
            key="main_route_map",
            # Additional parameters for stability
            returned_objects=["last_object_clicked"],  # Minimize returned data
            debug=False  # Disable debug mode for cleaner output
        )
    
    @st.fragment  # Independent fragment for save route section
    def _render_save_route_section(self, route_data: Dict, stats: Dict):
        """Render save route section as an independent fragment."""
        st.subheader("💾 Save Route")
        
        if st.button("Save Route for Future Analysis"):
            with st.spinner("Saving route..."):
                try:
                    saved_path = self.route_processor.save_route(route_data, stats)
                    st.success("✅ Route saved successfully!")
                    st.info(f"Saved to: {saved_path}")
                    logger.info(f"Route saved to: {saved_path}")
                except Exception as e:
                    log_error(logger, e, "Error saving route")
                    st.error(f"❌ Error saving route: {str(e)}")
    
    def render_saved_routes_page(self):
        """Render the saved routes page with cached route list."""
        log_function_entry(logger, "render_saved_routes_page")
        
        st.markdown("""
        <div class="welcome-section">
            <h2>💾 My Routes</h2>
            <p>View and analyze your previously uploaded cycling routes</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Use session state to cache saved routes list
        if "saved_routes_list" not in st.session_state or st.button("🔄 Refresh Routes"):
            try:
                saved_routes = self.route_processor.load_saved_routes()
                st.session_state["saved_routes_list"] = saved_routes
                logger.info(f"Loaded {len(saved_routes)} saved routes")
            except Exception as e:
                log_error(logger, e, "Error loading saved routes")
                st.error(f"❌ Error loading saved routes: {str(e)}")
                return
        else:
            saved_routes = st.session_state["saved_routes_list"]
        
        if not saved_routes:
            st.info("📭 No saved routes found. Upload some routes first!")
            log_function_exit(logger, "render_saved_routes_page", "No saved routes")
            return
        
        st.write(f"Found {len(saved_routes)} saved route(s):")
        
        # Display saved routes
        for i, route_info in enumerate(saved_routes):
            self._render_saved_route_item(route_info, i)
        
        logger.info(f"Displayed {len(saved_routes)} saved routes")
        log_function_exit(logger, "render_saved_routes_page", "Success")
    
    def render_rider_fitness_page(self):
        """Render the rider fitness page with comprehensive fitness data."""
        log_function_entry(logger, "render_rider_fitness_page")
        
        st.markdown("""
        <div class="welcome-section">
            <h2>🏃‍♂️ Rider Fitness Dashboard</h2>
            <p>Comprehensive fitness data and analysis from your Strava profile</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Check if user is authenticated
        if not self.auth_manager.is_authenticated():
            st.warning("⚠️ Please authenticate with Strava to view your fitness data.")
            st.info("💡 Use the Authentication section in the sidebar to connect your Strava account.")
            
            # Show sample/placeholder content
            st.markdown("### 📊 Sample Fitness Dashboard")
            st.info("This is what your fitness dashboard will look like once you connect your Strava account:")
            
            # Sample metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Weekly Distance", "125 km", "12 km")
            with col2:
                st.metric("Avg Power", "250 W", "5 W")
            with col3:
                st.metric("Training Load", "280 TSS", "-15 TSS")
            with col4:
                st.metric("Fitness (CTL)", "45", "2")
            
            # Sample chart placeholder
            st.markdown("### 📈 Training Trends")
            st.info("Charts showing your power trends, training load, and fitness progression will appear here.")
            
            log_function_exit(logger, "render_rider_fitness_page", "Not authenticated")
            return
        
        # User is authenticated, show actual fitness data
        try:
            # Call the auth manager's rider fitness data rendering method
            self.auth_manager._render_rider_fitness_data()
            
        except Exception as e:
            log_error(logger, e, "Error rendering rider fitness data")
            st.error(f"❌ Error loading fitness data: {str(e)}")
            st.info("💡 Try refreshing the page or check your Strava connection.")
        
        log_function_exit(logger, "render_rider_fitness_page", "Success")
    
    
    def _render_saved_route_item(self, route_info: Dict, index: int):
        """Render a single saved route item."""
        # Get unit preference
        use_imperial = getattr(st.session_state, 'use_imperial', False)
        
        # Format distance and elevation with appropriate units
        distance_str = UnitConverter.format_distance(route_info['distance_km'], use_imperial)
        elevation_str = UnitConverter.format_elevation(route_info['elevation_gain_m'], use_imperial)
        
        with st.expander(f"📍 {route_info['name']} - {distance_str}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Distance:** {distance_str}")
                st.write(f"**Elevation Gain:** {elevation_str}")
                st.write(f"**Processed:** {route_info['processed_at'][:10]}")
            
            with col2:
                st.write(f"**File:** {route_info['filename']}")
            
            # Load and display button
            if st.button("View Route Map", key=f"view_{index}"):
                try:
                    # Load the full route data
                    saved_data = self.route_processor.load_route_data(route_info['filepath'])
                    route_data = saved_data['route_data']
                    stats = saved_data['statistics']
                    
                    # Create and display map
                    st.subheader(f"🗺️ {route_info['name']}")
                    with st.spinner("Loading map..."):
                        route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
                        route_map = self.route_processor.create_route_map(route_data_hash, route_data, stats)
                        
                        # Add custom CSS to prevent map flickering
                        st.markdown("""
                        <style>
                        /* Folium map container stabilization */
                        .stApp iframe[title="streamlit_folium.st_folium"] {
                            border: none !important;
                            transition: none !important;
                            animation: none !important;
                            transform: none !important;
                        }
                        
                        /* Prevent container reflows during map initialization */
                        div[data-testid="stVerticalBlock"] > div:has(iframe[title="streamlit_folium.st_folium"]) {
                            min-height: 400px;
                            position: relative;
                            overflow: hidden;
                        }
                        
                        /* Stabilize map wrapper */
                        .stApp .element-container:has(iframe[title="streamlit_folium.st_folium"]) {
                            transition: none !important;
                            animation: none !important;
                        }
                        
                        /* Remove any potential flickering animations */
                        .stApp iframe {
                            backface-visibility: hidden;
                            perspective: 1000px;
                            transform: translateZ(0);
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st_folium(route_map, height=400, use_container_width=True, key=f"saved_route_map_{index}")
                    
                    logger.info(f"Displayed map for saved route: {route_info['name']}")
                        
                except Exception as e:
                    log_error(logger, e, f"Error loading route: {route_info['filename']}")
                    st.error(f"Error loading route: {str(e)}")


# Global UI components instance cached as resource
@st.cache_resource  # Cache UI components instance as they are expensive to initialize
def get_ui_components() -> UIComponents:
    """Get the global UI components instance."""
    return UIComponents()


if __name__ == "__main__":
    # Test UI components
    from logging_config import setup_logging
    
    setup_logging("DEBUG")
    
    ui = get_ui_components()
    
    print("=== UI Components Test ===")
    print(f"UI components initialized successfully")
    print(f"Route processor available: {ui.route_processor is not None}")
    print(f"Weather analyzer available: {ui.weather_analyzer is not None}")
    
    print("\n✅ UI components test completed")