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
from ...utils.units import UnitConverter


logger = get_logger(__name__)


class RouteAnalysis:
    """Handles route analysis display and visualization components."""
    
    def __init__(self):
        """Initialize route analysis component."""
        self.config = get_config()
        self.route_processor = RouteProcessor(data_dir=self.config.app.data_directory)
        self.weather_analyzer = WeatherAnalyzer()
        self.unit_converter = UnitConverter()
    
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
        overview_tab, details_tab, map_tab = st.tabs(["📋 Overview", "📈 Detailed Analysis", "🗺️ Interactive Map"])
        
        with overview_tab:
            self._render_route_overview(comprehensive_data, stats)
        
        with details_tab:
            self._render_detailed_analysis(comprehensive_data, stats)
        
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
        
        # Performance predictions
        if 'performance_analysis' in route_data:
            self._render_performance_analysis(route_data['performance_analysis'])
    
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
                tiles='OpenStreetMap'
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
        
        # Basic metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            distance = stats.get('total_distance', 0)
            st.metric("🚴 Distance", f"{distance:.1f} km")
        
        with col2:
            elevation_gain = stats.get('total_elevation_gain', 0)
            st.metric("⛰️ Elevation Gain", f"{elevation_gain:.0f} m")
        
        with col3:
            avg_gradient = stats.get('average_gradient', 0)
            st.metric("📈 Avg Gradient", f"{avg_gradient:.1f}%")
        
        with col4:
            max_gradient = stats.get('max_gradient', 0)
            st.metric("🏔️ Max Gradient", f"{max_gradient:.1f}%")
        
        # Performance metrics row
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            estimated_time = stats.get('estimated_time_minutes', 0)
            hours = int(estimated_time // 60)
            minutes = int(estimated_time % 60)
            st.metric("⏱️ Est. Time", f"{hours:02d}:{minutes:02d}")
        
        with col6:
            avg_speed = stats.get('estimated_average_speed', 0)
            st.metric("🚀 Est. Speed", f"{avg_speed:.1f} km/h")
        
        with col7:
            difficulty = stats.get('difficulty_rating', 'Unknown')
            st.metric("💪 Difficulty", difficulty)
        
        with col8:
            complexity = stats.get('route_complexity_score', 0)
            st.metric("🌀 Complexity", f"{complexity:.1f}/10")
        
        # Feature-specific metrics (based on configuration)
        feature_col1, feature_col2 = st.columns(2)
        
        with feature_col1:
            if self.config.app.enable_traffic_analysis:
                traffic_points = stats.get('traffic_points', 0)
                st.metric("🚦 Traffic Points", f"{traffic_points}")
            else:
                st.metric("🚦 Traffic Analysis", "Disabled")
        
        with feature_col2:
            if self.config.app.enable_weather_analysis:
                weather_score = stats.get('weather_favorability', 'Unknown')
                st.metric("🌤️ Weather Score", weather_score)
            else:
                st.metric("🌤️ Weather Analysis", "Disabled")
        
        log_function_exit(logger, "render_route_kpis")
    
    def _render_elevation_analysis(self, elevation_data: Dict):
        """Render elevation analysis section."""
        st.markdown("### ⛰️ Elevation Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Elevation Statistics:**")
            st.write(f"• Min Elevation: {elevation_data.get('min_elevation', 0):.0f} m")
            st.write(f"• Max Elevation: {elevation_data.get('max_elevation', 0):.0f} m")
            st.write(f"• Total Ascent: {elevation_data.get('total_ascent', 0):.0f} m")
            st.write(f"• Total Descent: {elevation_data.get('total_descent', 0):.0f} m")
        
        with col2:
            if 'climbs' in elevation_data and elevation_data['climbs']:
                st.markdown("**Categorized Climbs:**")
                for climb in elevation_data['climbs'][:5]:  # Show top 5 climbs
                    category = climb.get('category', 'Uncategorized')
                    length = climb.get('length', 0)
                    avg_gradient = climb.get('avg_gradient', 0)
                    st.write(f"• {category}: {length:.1f}km @ {avg_gradient:.1f}%")
            else:
                st.write("No significant climbs detected")
    
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
    
    def _render_performance_analysis(self, performance_data: Dict):
        """Render performance predictions and estimates."""
        st.markdown("### 🚀 Performance Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Speed Estimates:**")
            if 'speed_estimates' in performance_data:
                estimates = performance_data['speed_estimates']
                st.write(f"• Flat sections: {estimates.get('flat', 0):.1f} km/h")
                st.write(f"• Climbing: {estimates.get('climbing', 0):.1f} km/h")
                st.write(f"• Descending: {estimates.get('descending', 0):.1f} km/h")
        
        with col2:
            st.markdown("**Power Estimates:**")
            if 'power_estimates' in performance_data:
                power = performance_data['power_estimates']
                st.write(f"• Average Power: {power.get('average', 0):.0f} W")
                st.write(f"• Normalized Power: {power.get('normalized', 0):.0f} W")
                st.write(f"• Peak Power: {power.get('peak', 0):.0f} W")
    
    def _ensure_comprehensive_analysis(self, route_data: Dict, stats: Dict, filename: str) -> Dict:
        """Ensure all analysis components are complete."""
        # This is a simplified version - would normally ensure all analysis is complete
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