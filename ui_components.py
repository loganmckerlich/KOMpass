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

from route_processor import RouteProcessor
from weather_analyzer import WeatherAnalyzer
from auth_manager import get_auth_manager
from config import get_config
from logging_config import get_logger, log_function_entry, log_function_exit, log_error, log_execution_time
from units import UnitConverter

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
        """Render the main application header."""
        st.title("KOMpass - Route Analysis & Planning")
        st.markdown("*Analyze cycling routes with advanced metrics, weather forecasting, and performance insights.*")
        
        # Show authentication status in sidebar
        with st.sidebar:
            st.markdown("### 🔐 Authentication")
            self.auth_manager.render_authentication_ui()
    
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
        """Render navigation sidebar and return selected page."""
        st.sidebar.title("📍 Navigation")
        
        page_options = {
            "🏠 Home": "Home",
            "📁 Route Upload": "Route Upload", 
            "🗃️ Saved Routes": "Saved Routes"
        }
        
        selected_display = st.sidebar.selectbox("Choose a page", list(page_options.keys()))
        selected_page = page_options[selected_display]
        
        # Add unit toggle in sidebar
        st.sidebar.markdown("### ⚖️ Units")
        use_imperial = st.sidebar.checkbox(
            "Use Imperial Units (mi/ft)", 
            key="use_imperial_units",
            help="Toggle between metric (km/m) and imperial (mi/ft) units"
        )
        
        # Store unit preference in session state
        st.session_state.use_imperial = use_imperial
        
        logger.debug(f"User selected page: {selected_page}, Imperial units: {use_imperial}")
        return selected_page
    
    def render_home_page(self):
        """Render the home page."""
        log_function_entry(logger, "render_home_page")
        
        st.header("🏠 Welcome to KOMpass")
        
        # Display README content
        readme_content = self.render_readme_section()
        st.markdown(readme_content)
        
        # Display environment info for debugging (if user is authenticated)
        if self.auth_manager.is_authenticated():
            with st.expander("🔧 System Information"):
                env_info = self.config.get_environment_info()
                validation = self.config.validate_configuration()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Environment:**")
                    for key, value in env_info.items():
                        st.write(f"• {key}: {value}")
                
                with col2:
                    st.markdown("**Configuration Status:**")
                    for key, status in validation.items():
                        status_icon = "✅" if status else "❌"
                        st.write(f"{status_icon} {key.replace('_', ' ').title()}")
        
        log_function_exit(logger, "render_home_page")
    
    @log_execution_time()
    def render_route_upload_page(self):
        """Render the route upload and analysis page."""
        log_function_entry(logger, "render_route_upload_page")
        
        st.header("📁 Upload Route File")
        st.markdown("Upload GPX or FIT files from ride tracking apps like RideWithGPS, Strava, Garmin Connect, etc.")
        
        # File upload widget - update supported types
        uploaded_file = st.file_uploader(
            "Choose a GPX or FIT file",
            type=['gpx', 'fit'],
            help=f"Upload a GPX or FIT file containing your route data (max {self.config.app.max_file_size_mb}MB)"
        )
        
        if uploaded_file is not None:
            self._process_uploaded_file(uploaded_file)
        else:
            st.info("📂 Select a GPX or FIT file above to begin route analysis.")
        
        log_function_exit(logger, "render_route_upload_page")
    
    def _process_uploaded_file(self, uploaded_file):
        """Process uploaded GPX or FIT file and render analysis.
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
                    route_data = self.route_processor.parse_route_file(file_content_bytes, uploaded_file.name)
                    stats = self.route_processor.calculate_route_statistics(route_data)
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
            st.info("Please ensure you've uploaded a valid GPX or FIT file.")
    
    def _render_route_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """Render comprehensive route analysis."""
        log_function_entry(logger, "_render_route_analysis", filename=filename)
        
        # Basic route statistics
        self._render_basic_stats(stats)
        
        # Advanced metrics
        if stats.get('gradient_analysis'):
            self._render_gradient_analysis(stats['gradient_analysis'])
        
        if stats.get('climb_analysis') and stats['climb_analysis'].get('climb_count', 0) > 0:
            self._render_climb_analysis(stats['climb_analysis'])
        
        if stats.get('complexity_analysis'):
            self._render_complexity_analysis(stats['complexity_analysis'], stats.get('ml_features', {}))
        
        if stats.get('terrain_analysis'):
            self._render_terrain_analysis(stats['terrain_analysis'], stats.get('power_analysis', {}))
        
        if stats.get('traffic_analysis'):
            self._render_traffic_analysis(stats['traffic_analysis'])
        
        if stats.get('ml_features'):
            self._render_ml_features(stats['ml_features'])
        
        # Weather analysis section
        self._render_weather_analysis_section(route_data, stats)
        
        # Route metadata
        self._render_route_metadata(route_data)
        
        # Route visualization
        self._render_route_visualization(route_data, stats)
        
        # Save route option
        self._render_save_route_section(route_data, stats)
        
        log_function_exit(logger, "_render_route_analysis")
    
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
    
    def _render_complexity_analysis(self, complexity: Dict, ml_features: Dict):
        """Render route complexity analysis."""
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
    
    def _render_terrain_analysis(self, terrain: Dict, power: Dict):
        """Render terrain and power analysis."""
        st.subheader("🏔️ Terrain Classification")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Terrain Type", terrain.get('terrain_type', 'Unknown'))
            if power:
                st.metric("Avg Power", f"{power.get('average_power_watts', 0)} W")
        
        with col2:
            if power:
                st.metric("Est. Energy", f"{power.get('total_energy_kj', 0)} kJ")
                st.metric("Energy/km", f"{power.get('energy_per_km_kj', 0)} kJ/km")
        
        with col3:
            terrain_dist = terrain.get('terrain_distribution', {})
            st.metric("Flat Sections", f"{terrain_dist.get('flat_percent', 0):.1f}%")
            st.metric("Steep Climbs", f"{terrain_dist.get('steep_climbs_percent', 0):.1f}%")
        
        # Power zone distribution
        if power and power.get('power_zones'):
            st.subheader("⚡ Power Zone Distribution")
            zones = power['power_zones']
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Endurance Zone", f"{zones.get('endurance_percent', 0)}%", help="<200W")
            with col2:
                st.metric("Tempo Zone", f"{zones.get('tempo_percent', 0)}%", help="200-300W")
            with col3:
                st.metric("Threshold Zone", f"{zones.get('threshold_percent', 0)}%", help=">300W")
    
    def _render_traffic_analysis(self, traffic: Dict):
        """Render traffic stop analysis."""
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
                weather_analysis = self.weather_analyzer.get_comprehensive_weather_analysis(
                    all_points, departure_datetime, 2.0  # Default 2-hour duration estimate
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
    
    def _render_route_metadata(self, route_data: Dict):
        """Render route metadata section."""
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
                    route_map = self.route_processor.create_route_map(route_data, stats)
                    # Cache the map in session state
                    st.session_state[map_cache_key] = route_map
                    logger.info("Route map generated and cached successfully")
                except Exception as e:
                    log_error(logger, e, "Error generating route map")
                    st.error(f"❌ Error generating map: {str(e)}")
                    return
        
        # Display the map
        st_folium(route_map, height=500, use_container_width=True, key="main_route_map")
    
    def _render_save_route_section(self, route_data: Dict, stats: Dict):
        """Render save route section."""
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
        
        st.header("🗃️ Saved Routes")
        st.markdown("View and analyze your previously uploaded routes.")
        
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
                        route_map = self.route_processor.create_route_map(route_data, stats)
                        st_folium(route_map, height=400, use_container_width=True, key=f"saved_route_map_{index}")
                    
                    logger.info(f"Displayed map for saved route: {route_info['name']}")
                        
                except Exception as e:
                    log_error(logger, e, f"Error loading route: {route_info['filename']}")
                    st.error(f"Error loading route: {str(e)}")


# Global UI components instance
ui_components = UIComponents()


def get_ui_components() -> UIComponents:
    """Get the global UI components instance."""
    return ui_components


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