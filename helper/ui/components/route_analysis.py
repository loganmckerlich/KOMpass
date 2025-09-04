"""
Route Analysis Component - Handles route analysis display and visualization.

This module provides:
- Route analysis results visualization
- KPI metrics display
- Interactive maps
- Feature flag aware components
"""

import streamlit as st
from typing import Dict, Any, Optional
import folium
from streamlit_folium import st_folium

from ...processing.route_processor import RouteProcessor
from ...processing.weather_analyzer import WeatherAnalyzer
from ...config.config import get_config
from ...config.logging_config import get_logger, log_function_entry, log_function_exit
from ...ml.model_manager import ModelManager
from ...auth.auth_manager import get_auth_manager


logger = get_logger(__name__)


class RouteAnalysis:
    """Handles route analysis display and visualization components."""
    
    def __init__(self):
        """Initialize route analysis component."""
        self.config = get_config()
        self.route_processor = RouteProcessor(data_dir=self.config.app.data_directory)
        self.weather_analyzer = WeatherAnalyzer()
        self.model_manager = ModelManager()
        self.auth_manager = get_auth_manager()
    
    def render_route_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """
        Render comprehensive route analysis with all components.
        
        Args:
            route_data: Processed route data
            stats: Route statistics
            filename: Route filename
        """
        log_function_entry(logger, "render_route_analysis")
        
        # Ensure comprehensive analysis is complete
        comprehensive_data = self._ensure_comprehensive_analysis(route_data, stats, filename)
        
        if not comprehensive_data:
            st.error("❌ Unable to complete route analysis")
            return
        
        # Display route header
        st.markdown(f"# 📊 Route Analysis: {filename}")
        
        # Main analysis tabs
        overview_tab, details_tab, ml_tab, map_tab = st.tabs(["📋 Overview", "📈 Detailed Analysis", "🤖 ML Predictions", "🗺️ Interactive Map"])
        
        with overview_tab:
            self._render_route_overview(comprehensive_data, stats)
        
        with details_tab:
            self._render_detailed_analysis(comprehensive_data, stats)
        
        with ml_tab:
            self._render_ml_predictions(comprehensive_data, stats, filename)
        
        with map_tab:
            self._render_interactive_map(route_data, stats)
        
        log_function_exit(logger, "render_route_analysis")
    
    def _render_route_overview(self, route_data: Dict, stats: Dict):
        """Render route overview with KPIs and summary."""
        st.markdown("## 📊 Route Overview")
        
        # Render KPIs
        self._render_route_kpis(stats, route_data)
        
        # Automatic weather analysis (if enabled)
        if self.config.app.enable_weather_analysis:
            self._perform_automatic_weather_analysis(route_data, stats)
        else:
            st.info("🌤️ Weather analysis is temporarily disabled")
        
        # Traffic analysis (if enabled)
        if self.config.app.enable_traffic_analysis:
            self._perform_traffic_analysis(route_data, stats, route_data.get('filename', 'route'))
        else:
            st.info("🚦 Traffic light and intersection analysis is temporarily disabled")
    
    def _render_detailed_analysis(self, route_data: Dict, stats: Dict):
        """Render detailed analysis components."""
        st.markdown("## 📈 Detailed Analysis")
        
        # Elevation analysis
        if 'elevation_analysis' in route_data:
            self._render_elevation_analysis(route_data['elevation_analysis'])
        
        # Gradient analysis
        if 'gradient_analysis' in route_data:
            self._render_gradient_analysis(route_data['gradient_analysis'])
        
        # Route complexity
        if 'complexity_analysis' in route_data:
            self._render_complexity_analysis(route_data['complexity_analysis'])
    
    def _render_interactive_map(self, route_data: Dict, stats: Dict):
        """Render interactive map with route visualization."""
        st.markdown("## 🗺️ Interactive Route Map")
        
        if 'coordinates' not in route_data or not route_data['coordinates']:
            st.warning("⚠️ No GPS coordinates available for map display")
            return
        
        try:
            coordinates = route_data['coordinates']
            
            # Create map centered on route
            center_lat = sum(coord['lat'] for coord in coordinates) / len(coordinates)
            center_lon = sum(coord['lon'] for coord in coordinates) / len(coordinates)
            
            route_map = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=13,
                tiles='Cartodb Positron'
            )
            
            # Add route polyline
            route_coords = [[coord['lat'], coord['lon']] for coord in coordinates]
            folium.PolyLine(
                route_coords,
                color='#FC4C02',
                weight=4,
                opacity=0.8,
                popup='Route Path'
            ).add_to(route_map)
            
            # Add start and end markers
            if route_coords:
                folium.Marker(
                    route_coords[0],
                    popup='Start',
                    icon=folium.Icon(color='green', icon='play')
                ).add_to(route_map)
                
                folium.Marker(
                    route_coords[-1],
                    popup='Finish',
                    icon=folium.Icon(color='red', icon='stop')
                ).add_to(route_map)
            
            # Display map
            st_folium(route_map, width=700, height=500)
            
        except Exception as e:
            logger.error(f"Error rendering interactive map: {e}")
            st.error("❌ Unable to display interactive map")
    
    def _render_route_kpis(self, stats: Dict, route_data: Dict):
        """Render key performance indicators."""
        log_function_entry(logger, "render_route_kpis")
        
        # Basic metrics row - always use metric units
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            distance = stats.get('total_distance_km', 0)
            distance_formatted = f"{distance:.2f} km" if distance is not None else "N/A"
            st.metric("🚴 Distance", distance_formatted)
        
        with col2:
            elevation_gain = stats.get('total_elevation_gain_m', 0)
            elevation_formatted = f"{elevation_gain:.0f} m" if elevation_gain is not None else "N/A"
            st.metric("⛰️ Elevation Gain", elevation_formatted)
        
        with col3:
            avg_gradient = stats.get('average_gradient', 0)
            st.metric("📈 Avg Gradient", f"{avg_gradient:.1f}%")
        
        with col4:
            max_gradient = stats.get('max_gradient', 0)
            st.metric("🏔️ Max Gradient", f"{max_gradient:.1f}%")
        
        # Main metrics row (4 columns)
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            difficulty = stats.get('difficulty_rating', 'Unknown')
            st.metric("💪 Difficulty", difficulty)
        
        with col6:
            complexity = stats.get('route_complexity_score', 0)
            st.metric("🌀 Complexity", f"{complexity:.1f}/10")
        
        with col7:
            if self.config.app.enable_traffic_analysis:
                traffic_points = stats.get('traffic_points', 0)
                st.metric("🚦 Traffic Points", f"{traffic_points}")
            else:
                st.metric("🚦 Traffic Analysis", "Disabled")
        
        with col8:
            if self.config.app.enable_weather_analysis:
                weather_score = stats.get('weather_favorability', 'Unknown')
                st.metric("🌤️ Weather Score", weather_score)
            else:
                st.metric("🌤️ Weather Analysis", "Disabled")
        
        log_function_exit(logger, "render_route_kpis")
    
    def _render_elevation_analysis(self, elevation_data: Dict):
        """Render elevation analysis section."""
        st.markdown("### ⛰️ Elevation Analysis")
        
        # Check elevation data quality
        data_quality = elevation_data.get('data_quality', {})
        has_elevation_data = data_quality.get('has_elevation_data', True)  # Default to True for backward compatibility
        has_elevation_variation = data_quality.get('has_elevation_variation', True)  # Default to True for backward compatibility
        elevation_data_percentage = data_quality.get('elevation_data_percentage', 100)
        
        # Show elevation data warnings if needed
        if not has_elevation_data:
            st.warning("⚠️ **No elevation data found in this route**")
            st.info("This GPX file doesn't contain elevation information. Elevation metrics will show as 0. To get elevation data, use a GPS device or app that records elevation, or use a service that adds elevation data to GPX files.")
        elif elevation_data_percentage < 50:
            st.warning(f"⚠️ **Limited elevation data**: Only {elevation_data_percentage:.1f}% of route points have elevation data")
            st.info("This may result in inaccurate elevation metrics. Consider using a GPX file with complete elevation data.")
        elif not has_elevation_variation:
            elevation_range = data_quality.get('elevation_range_m', 0)
            if elevation_range == 0:
                st.info("ℹ️ **Flat route detected**: This route has no elevation changes (all points at same elevation)")
            else:
                st.info(f"ℹ️ **Minimal elevation changes**: Route elevation varies by only {elevation_range:.1f}m")
        
        # Always use metric units
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Elevation Statistics:**")
            min_elevation = elevation_data.get('min_elevation', 0)
            max_elevation = elevation_data.get('max_elevation', 0)
            total_ascent = elevation_data.get('total_ascent', 0)
            total_descent = elevation_data.get('total_descent', 0)
            
            # Handle None values for min/max elevation when no data is available
            if min_elevation is None and max_elevation is None:
                st.write("• Min Elevation: N/A (no elevation data)")
                st.write("• Max Elevation: N/A (no elevation data)")
            else:
                min_elev_formatted = f"{min_elevation or 0:.0f} m"
                max_elev_formatted = f"{max_elevation or 0:.0f} m"
                st.write(f"• Min Elevation: {min_elev_formatted}")
                st.write(f"• Max Elevation: {max_elev_formatted}")
            
            ascent_formatted = f"{total_ascent:.0f} m" if total_ascent is not None else "N/A"
            descent_formatted = f"{total_descent:.0f} m" if total_descent is not None else "N/A"
            st.write(f"• Total Ascent: {ascent_formatted}")
            st.write(f"• Total Descent: {descent_formatted}")
        
        with col2:
            if 'climbs' in elevation_data and elevation_data['climbs']:
                st.markdown("**Categorized Climbs:**")
                for climb in elevation_data['climbs'][:5]:  # Show top 5 climbs
                    category = climb.get('category', 'Uncategorized')
                    length = climb.get('length', 0)
                    avg_gradient = climb.get('avg_gradient', 0)
                    st.write(f"• {category}: {length:.1f}km @ {avg_gradient:.1f}%")
            else:
                if not has_elevation_data:
                    st.markdown("**Categorized Climbs:**")
                    st.write("• No climbs detected (no elevation data)")
                else:
                    st.markdown("**Categorized Climbs:**")
                    st.write("• No significant climbs detected")
    
    def _render_gradient_analysis(self, gradient_data: Dict):
        """Render gradient analysis section."""
        st.markdown("### 📈 Gradient Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Gradient Distribution:**")
            if 'gradient_distribution' in gradient_data:
                distribution = gradient_data['gradient_distribution']
                for range_key, percentage in distribution.items():
                    st.write(f"• {range_key}: {percentage:.1f}%")
        
        with col2:
            terrain_type = self._get_simple_terrain_type(gradient_data)
            st.markdown(f"**Terrain Type:** {terrain_type}")
            
            variability = gradient_data.get('gradient_variability', 'Unknown')
            st.markdown(f"**Gradient Variability:** {variability}")
    
    def _render_complexity_analysis(self, complexity_data: Dict):
        """Render route complexity analysis."""
        st.markdown("### 🌀 Route Complexity")
        
        complexity_score = complexity_data.get('complexity_score', 0)
        turn_count = complexity_data.get('significant_turns', 0)
        direction_changes = complexity_data.get('direction_changes', 0)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Complexity Score", f"{complexity_score:.1f}/10")
        
        with col2:
            st.metric("Significant Turns", turn_count)
        
        with col3:
            st.metric("Direction Changes", direction_changes)
    
    def _ensure_comprehensive_analysis(self, route_data: Dict, stats: Dict, filename: str) -> Dict:
        """Ensure all analysis components are complete."""
        # Create elevation_analysis data structure from stats
        if 'elevation_analysis' not in route_data:
            route_data['elevation_analysis'] = {
                'min_elevation': stats.get('min_elevation_m', 0),
                'max_elevation': stats.get('max_elevation_m', 0),
                'total_ascent': stats.get('total_elevation_gain_m', 0),
                'total_descent': stats.get('total_elevation_loss_m', 0),
                'climbs': stats.get('climb_analysis', {}).get('climbs', []),
                'data_quality': stats.get('elevation_data_quality', {
                    'has_elevation_data': False,
                    'points_with_elevation': 0,
                    'total_points': stats.get('total_points', 0),
                    'elevation_data_percentage': 0,
                    'elevation_range_m': 0,
                    'has_elevation_variation': False
                })
            }
        
        # Create gradient_analysis data structure from stats  
        if 'gradient_analysis' not in route_data:
            gradient_stats = stats.get('gradient_analysis', {})
            route_data['gradient_analysis'] = {
                'average_gradient': gradient_stats.get('average_gradient_percent', 0),
                'max_gradient': gradient_stats.get('max_gradient_percent', 0),
                'gradient_distribution': gradient_stats.get('gradient_distribution', {}),
                'gradient_variability': gradient_stats.get('gradient_variability', 'Unknown')
            }
        
        return route_data
    
    def _perform_automatic_weather_analysis(self, route_data: Dict, stats: Dict):
        """Perform automatic weather analysis if enabled."""
        if not self.config.app.enable_weather_analysis:
            return
        
        st.markdown("### 🌤️ Weather Analysis")
        
        # Check if coordinates available for weather analysis
        if 'coordinates' not in route_data or not route_data['coordinates']:
            st.warning("⚠️ No GPS coordinates available for weather analysis")
            return
        
        try:
            # Use all route coordinates for comprehensive weather analysis
            route_points = route_data['coordinates']
            # If timing information is available, pass it; otherwise, pass None
            timing = route_data.get('timestamps', None)
            weather_data = self.weather_analyzer.get_comprehensive_weather_analysis(
                route_points,
                timing
            )
            
            if weather_data:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    temp = weather_data.get('temperature', 'Unknown')
                    st.metric("🌡️ Temperature", f"{temp}°C" if temp != 'Unknown' else temp)
                
                with col2:
                    wind = weather_data.get('wind_speed', 'Unknown')
                    st.metric("💨 Wind Speed", f"{wind} km/h" if wind != 'Unknown' else wind)
                
                with col3:
                    conditions = weather_data.get('conditions', 'Unknown')
                    st.metric("☁️ Conditions", conditions)
            else:
                st.info("ℹ️ Weather data not available for this location")
                
        except Exception as e:
            logger.error(f"Weather analysis error: {e}")
            st.warning("⚠️ Unable to fetch weather data")
    
    def _perform_traffic_analysis(self, route_data: Dict, stats: Dict, filename: str):
        """Perform traffic analysis if enabled."""
        if not self.config.app.enable_traffic_analysis:
            return
        
        st.markdown("### 🚦 Traffic Analysis")
        
        # Simplified traffic analysis display
        traffic_points = stats.get('traffic_points', 0)
        intersections = stats.get('intersections', 0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Traffic Lights", traffic_points)
        
        with col2:
            st.metric("Intersections", intersections)
        
        if traffic_points > 0 or intersections > 0:
            st.info(f"ℹ️ Route contains {traffic_points} traffic lights and {intersections} major intersections")
        else:
            st.success("✅ Route appears to have minimal traffic infrastructure")
    
    def _get_simple_terrain_type(self, gradient_analysis: Dict) -> str:
        """Get simplified terrain type from gradient analysis."""
        avg_gradient = gradient_analysis.get('average_gradient', 0)
        
        if avg_gradient > 3:
            return "Hilly"
        elif avg_gradient > 1:
            return "Rolling"
        else:
            return "Flat"
    
    def _render_ml_predictions(self, route_data: Dict, stats: Dict, filename: str):
        """Render ML-based speed predictions for the route."""
        st.markdown("## 🤖 AI Speed Predictions")
        st.markdown("Get personalized speed predictions for this route based on your fitness profile.")
        
        # Check authentication
        if not self.auth_manager.is_authenticated():
            st.info("🔒 Please log in with Strava to get personalized speed predictions.")
            self._render_demo_predictions(route_data, stats)
            return
        
        # Get rider data
        rider_data = st.session_state.get("rider_fitness_data")
        if not rider_data:
            st.warning("⚠️ No rider fitness data available. Please ensure your Strava data has been loaded.")
            self._render_demo_predictions(route_data, stats)
            return
        
        # Generate predictions
        try:
            with st.spinner("Generating AI predictions..."):
                predictions = self.model_manager.predict_route_speed(rider_data, route_data)
            
            if 'error' in predictions:
                st.error(f"Prediction failed: {predictions['error']}")
                return
            
            # Display predictions
            self._display_route_predictions(predictions, route_data, stats)
            
        except Exception as e:
            logger.error(f"Error generating ML predictions: {e}")
            st.error("Failed to generate predictions. Please try again.")
    
    def _render_demo_predictions(self, route_data: Dict, stats: Dict):
        """Render demo predictions for unauthenticated users."""
        st.markdown("### 🎮 Demo Predictions")
        st.markdown("Sample predictions for a typical rider (FTP: 220W, Weight: 70kg)")
        
        # Create demo rider data
        demo_rider = {
            'performance_features': {'estimated_ftp': 220, 'weighted_power_avg': 200},
            'basic_features': {'weight_kg': 70},
            'training_features': {'hours_per_week': 6},
            'composite_scores': {'overall_fitness_score': 65}
        }
        
        try:
            predictions = self.model_manager.predict_route_speed(demo_rider, route_data)
            self._display_route_predictions(predictions, route_data, stats, is_demo=True)
        except Exception as e:
            logger.error(f"Error generating demo predictions: {e}")
            st.error("Demo predictions unavailable.")
    
    def _display_route_predictions(self, predictions: Dict, route_data: Dict, stats: Dict, is_demo: bool = False):
        """Display speed predictions with route context."""
        
        # Route summary metrics
        st.markdown("### 📊 Route Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            distance = stats.get('distance_km', 0)
            st.metric("Distance", f"{distance:.1f} km")
        
        with col2:
            elevation = stats.get('total_elevation_gain', 0)
            st.metric("Elevation Gain", f"{elevation:.0f} m")
        
        with col3:
            avg_gradient = route_data.get('gradient_analysis', {}).get('average_gradient', 0)
            st.metric("Avg Gradient", f"{avg_gradient:.1f}%")
        
        with col4:
            terrain = self._get_simple_terrain_type(route_data.get('gradient_analysis', {}))
            st.metric("Terrain Type", terrain)
        
        # Speed predictions
        st.markdown("### 🎯 Speed & Time Predictions")
        
        prediction_data = []
        for effort_level, prediction in predictions.items():
            if effort_level.startswith('_'):  # Skip metadata
                continue
            
            speed = prediction.get('speed_kmh', 0)
            confidence = prediction.get('confidence', 0)
            method = prediction.get('method', 'unknown')
            
            # Calculate time
            time_hours = distance / speed if speed > 0 else 0
            time_str = f"{int(time_hours)}:{int((time_hours % 1) * 60):02d}"
            
            # Calculate power estimate (rough)
            ftp_estimate = 220 if is_demo else 200  # Default estimates
            if effort_level == 'zone2':
                power_estimate = int(ftp_estimate * 0.75)
                effort_name = "Zone 2 (Endurance)"
                effort_desc = "Sustainable aerobic pace"
            elif effort_level == 'threshold':
                power_estimate = int(ftp_estimate * 1.0)
                effort_name = "Threshold"
                effort_desc = "Hard sustainable effort"
            else:
                power_estimate = int(ftp_estimate * 0.85)
                effort_name = effort_level.title()
                effort_desc = "Moderate effort"
            
            prediction_data.append({
                'Effort Level': effort_name,
                'Description': effort_desc,
                'Speed': f"{speed:.1f} km/h",
                'Time': time_str,
                'Est. Power': f"{power_estimate}W",
                'Confidence': f"{confidence:.0%}"
            })
        
        if prediction_data:
            import pandas as pd
            pred_df = pd.DataFrame(prediction_data)
            st.dataframe(pred_df, use_container_width=True)
        
        # Additional insights
        st.markdown("### 💡 Insights")
        
        metadata = predictions.get('_metadata', {})
        if metadata.get('model_info', {}).get('has_ml_models', False):
            st.success("✅ Predictions based on trained AI models using your ride history")
        else:
            st.info("ℹ️ Predictions based on physics calculations (train AI models for better accuracy)")
        
        # Training recommendation
        if not is_demo and not metadata.get('model_info', {}).get('has_ml_models', False):
            st.markdown("### 🚀 Improve Predictions")
            st.info("Train personalized AI models using your ride history for more accurate predictions!")
            if st.button("🤖 Go to ML Training", key="ml_training_route"):
                st.session_state['selected_page_index'] = 2  # ML Predictions page
                st.rerun()
        
        if is_demo:
            st.info("🎮 This is a demo prediction. Log in with Strava for personalized predictions based on your actual fitness data.")