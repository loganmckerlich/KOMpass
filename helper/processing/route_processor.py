"""
Route processing module for KOMpass.
Handles GPX file parsing, route analysis, and data persistence.
Optimized with Streamlit caching for performance.
"""

import gpxpy
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import folium
from math import radians, cos, sin, asin, sqrt, atan2, degrees
import numpy as np
import requests
import time
import streamlit as st
import hashlib
from ..storage.storage_manager import get_storage_manager
from ..utils.progress_tracker import ProgressTracker, create_route_analysis_tracker, create_traffic_analysis_tracker
from ..config.logging_config import get_logger, log_function_entry, log_function_exit, log_performance, log_error
# FIT support removed - GPX only

@st.cache_data(ttl=3600)  # Cache for 1 hour
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in kilometers.
    Cached for performance as this is called frequently.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r


@st.cache_data(ttl=3600)  # Cache for 1 hour
def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing between two points in degrees.
    Cached for performance.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    y = sin(dlon) * cos(lat2)
    x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
    
    bearing = atan2(y, x)
    bearing = degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


@st.cache_data(ttl=3600)  # Cache for 1 hour
def calculate_gradient(distance_m: float, elevation_change_m: float) -> float:
    """
    Calculate gradient as a percentage.
    Cached for performance.
    """
    if distance_m == 0:
        return 0
    return (elevation_change_m / distance_m) * 100


class RouteProcessor:
    """Handles route file processing and analysis."""
    
    def __init__(self, data_dir: str = "saved_routes"):
        """Initialize the route processor.
        
        Args:
            data_dir: Directory to save processed route data (for local fallback)
        """
        self.data_dir = data_dir
        self.storage_manager = get_storage_manager()
        self.logger = get_logger(__name__)
        self._ensure_data_dir()
        
        # Load configuration to respect feature flags
        from ..config.config import get_config
        self.config = get_config()
        
        # Overpass API configuration for OpenStreetMap queries
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.request_delay = 1.0  # Seconds between API requests to be respectful
        
        self.logger.info("RouteProcessor initialized")
        self.logger.debug(f"Data directory: {self.data_dir}")
        self.logger.debug(f"Overpass API URL: {self.overpass_url}")
        self.logger.info(f"Traffic analysis enabled: {self.config.app.enable_traffic_analysis}")
    
    @st.cache_data(ttl=7200)  # Cache for 2 hours
    def _analyze_gradients_and_climbs_combined(_self, points_hash: str, points: List[Dict]) -> Tuple[Dict, Dict]:
        """Optimized combined analysis of gradients and climbs.
        
        This method combines gradient and climb analysis to avoid iterating through
        the route points multiple times, improving performance.
        
        Returns:
            Tuple of (gradient_analysis, climb_analysis) dictionaries
        """
        if len(points) < 2:
            return {}, {}
        
        gradients = []
        segments = []
        climbs = []
        current_climb = None
        
        for i in range(1, len(points)):
            prev_point = points[i-1]
            curr_point = points[i]
            
            if prev_point['elevation'] is not None and curr_point['elevation'] is not None:
                distance_m = haversine_distance(
                    prev_point['lat'], prev_point['lon'],
                    curr_point['lat'], curr_point['lon']
                ) * 1000  # Convert to meters
                
                elevation_change = curr_point['elevation'] - prev_point['elevation']
                gradient = calculate_gradient(distance_m, elevation_change)
                
                # For gradient analysis
                gradients.append(gradient)
                segments.append({
                    'distance_m': distance_m,
                    'elevation_change_m': elevation_change,
                    'gradient_percent': gradient
                })
                
                # For climb analysis
                # Start of climb (gradient > 3%)
                if gradient > 3 and current_climb is None:
                    current_climb = {
                        'start_elevation': prev_point['elevation'],
                        'distance_m': distance_m,
                        'elevation_gain_m': max(0, elevation_change),
                        'max_gradient': gradient,
                        'segments': 1
                    }
                
                # Continue climb
                elif gradient > 1 and current_climb is not None:
                    current_climb['distance_m'] += distance_m
                    current_climb['elevation_gain_m'] += max(0, elevation_change)
                    current_climb['max_gradient'] = max(current_climb['max_gradient'], gradient)
                    current_climb['segments'] += 1
                
                # End of climb
                elif current_climb is not None and (gradient <= 1 or i == len(points) - 1):
                    if current_climb['elevation_gain_m'] > 10:  # Only count significant climbs
                        current_climb['end_elevation'] = curr_point['elevation']
                        current_climb['average_gradient'] = (current_climb['elevation_gain_m'] / current_climb['distance_m']) * 100
                        current_climb['difficulty_score'] = _self._calculate_climb_difficulty(current_climb)
                        climbs.append(current_climb)
                    current_climb = None
        
        # Generate gradient analysis
        gradient_analysis = {}
        if gradients:
            gradients = np.array(gradients)
            gradient_analysis = {
                'average_gradient_percent': round(np.mean(gradients), 2),
                'max_gradient_percent': round(np.max(gradients), 2),
                'min_gradient_percent': round(np.min(gradients), 2),
                'gradient_std_dev': round(np.std(gradients), 2),
                'steep_climbs_percent': round(np.sum(gradients > 8) / len(gradients) * 100, 1),
                'moderate_climbs_percent': round(np.sum((gradients > 3) & (gradients <= 8)) / len(gradients) * 100, 1),
                'flat_sections_percent': round(np.sum(np.abs(gradients) <= 3) / len(gradients) * 100, 1),
                'descents_percent': round(np.sum(gradients < -3) / len(gradients) * 100, 1),
                'segments': segments
            }
        
        # Generate climb analysis
        climb_analysis = {}
        if not climbs:
            climb_analysis = {'climb_count': 0}
        else:
            total_climb_distance = sum(c['distance_m'] for c in climbs)
            total_climb_elevation = sum(c['elevation_gain_m'] for c in climbs)
            
            climb_analysis = {
                'climb_count': len(climbs),
                'total_climb_distance_km': round(total_climb_distance / 1000, 2),
                'total_climb_elevation_m': round(total_climb_elevation, 1),
                'average_climb_length_m': round(total_climb_distance / len(climbs), 0) if climbs else 0,
                'average_climb_gradient': round(sum(c['average_gradient'] for c in climbs) / len(climbs), 2) if climbs else 0,
                'max_climb_gradient': round(max(c['max_gradient'] for c in climbs), 2) if climbs else 0,
                'climb_difficulty_score': round(sum(c['difficulty_score'] for c in climbs), 1),
                'climbs': climbs
            }
        
        return gradient_analysis, climb_analysis
        """Analyze gradient characteristics of the route.
        Cached for performance as gradient analysis is computationally expensive.
        """
        if len(points) < 2:
            return {}
        
        gradients = []
        segments = []
        
        for i in range(1, len(points)):
            prev_point = points[i-1]
            curr_point = points[i]
            
            if prev_point['elevation'] is not None and curr_point['elevation'] is not None:
                distance_m = haversine_distance(
                    prev_point['lat'], prev_point['lon'],
                    curr_point['lat'], curr_point['lon']
                ) * 1000  # Convert to meters
                
                elevation_change = curr_point['elevation'] - prev_point['elevation']
                gradient = calculate_gradient(distance_m, elevation_change)
                
                gradients.append(gradient)
                segments.append({
                    'distance_m': distance_m,
                    'elevation_change_m': elevation_change,
                    'gradient_percent': gradient
                })
        
        if not gradients:
            return {}
        
        gradients = np.array(gradients)
        
        return {
            'average_gradient_percent': round(np.mean(gradients), 2),
            'max_gradient_percent': round(np.max(gradients), 2),
            'min_gradient_percent': round(np.min(gradients), 2),
            'gradient_std_dev': round(np.std(gradients), 2),
            'steep_climbs_percent': round(np.sum(gradients > 8) / len(gradients) * 100, 1),
            'moderate_climbs_percent': round(np.sum((gradients > 3) & (gradients <= 8)) / len(gradients) * 100, 1),
            'flat_sections_percent': round(np.sum(np.abs(gradients) <= 3) / len(gradients) * 100, 1),
            'descents_percent': round(np.sum(gradients < -3) / len(gradients) * 100, 1),
            'segments': segments
        }
    
    @st.cache_data(ttl=7200)  # Cache for 2 hours
    def _analyze_climbs(_self, points_hash: str, points: List[Dict]) -> Dict:
        """Analyze climbing segments and characteristics.
        Cached for performance as climb analysis is computationally expensive.
        """
        if len(points) < 2:
            return {}
        
        climbs = []
        current_climb = None
        
        for i in range(1, len(points)):
            prev_point = points[i-1]
            curr_point = points[i]
            
            if prev_point['elevation'] is not None and curr_point['elevation'] is not None:
                distance_m = haversine_distance(
                    prev_point['lat'], prev_point['lon'],
                    curr_point['lat'], curr_point['lon']
                ) * 1000
                
                elevation_change = curr_point['elevation'] - prev_point['elevation']
                gradient = calculate_gradient(distance_m, elevation_change)
                
                # Start of climb (gradient > 3%)
                if gradient > 3 and current_climb is None:
                    current_climb = {
                        'start_elevation': prev_point['elevation'],
                        'distance_m': distance_m,
                        'elevation_gain_m': max(0, elevation_change),
                        'max_gradient': gradient,
                        'segments': 1
                    }
                
                # Continue climb
                elif gradient > 1 and current_climb is not None:
                    current_climb['distance_m'] += distance_m
                    current_climb['elevation_gain_m'] += max(0, elevation_change)
                    current_climb['max_gradient'] = max(current_climb['max_gradient'], gradient)
                    current_climb['segments'] += 1
                
                # End of climb
                elif current_climb is not None and (gradient <= 1 or i == len(points) - 1):
                    if current_climb['elevation_gain_m'] > 10:  # Only count significant climbs
                        current_climb['end_elevation'] = curr_point['elevation']
                        current_climb['average_gradient'] = (current_climb['elevation_gain_m'] / current_climb['distance_m']) * 100
                        current_climb['difficulty_score'] = _self._calculate_climb_difficulty(current_climb)
                        climbs.append(current_climb)
                    current_climb = None
        
        if not climbs:
            return {'climb_count': 0}
        
        total_climb_distance = sum(c['distance_m'] for c in climbs)
        total_climb_elevation = sum(c['elevation_gain_m'] for c in climbs)
        
        return {
            'climb_count': len(climbs),
            'total_climb_distance_km': round(total_climb_distance / 1000, 2),
            'total_climb_elevation_m': round(total_climb_elevation, 1),
            'average_climb_length_m': round(total_climb_distance / len(climbs), 0) if climbs else 0,
            'average_climb_gradient': round(sum(c['average_gradient'] for c in climbs) / len(climbs), 2) if climbs else 0,
            'max_climb_gradient': round(max(c['max_gradient'] for c in climbs), 2) if climbs else 0,
            'climb_difficulty_score': round(sum(c['difficulty_score'] for c in climbs), 1),
            'climbs': climbs
        }
    
    def _calculate_climb_difficulty(self, climb: Dict) -> float:
        """Calculate climbing difficulty score based on distance and gradient."""
        distance_km = climb['distance_m'] / 1000
        avg_gradient = climb['average_gradient']
        
        # Difficulty = distance * gradient^2 (emphasizes steep sections)
        return distance_km * (avg_gradient ** 2) / 100
    
    @st.cache_data(ttl=7200)  # Cache for 2 hours
    def _analyze_route_complexity(_self, points_hash: str, points: List[Dict]) -> Dict:
        """Analyze route complexity based on direction changes and curvature.
        Cached for performance as complexity analysis involves many calculations.
        """
        if len(points) < 3:
            return {}
        
        bearings = []
        direction_changes = []
        
        for i in range(1, len(points)):
            prev_point = points[i-1]
            curr_point = points[i]
            
            bearing = calculate_bearing(
                prev_point['lat'], prev_point['lon'],
                curr_point['lat'], curr_point['lon']
            )
            bearings.append(bearing)
        
        # Calculate direction changes
        for i in range(1, len(bearings)):
            change = abs(bearings[i] - bearings[i-1])
            # Handle wraparound (e.g., 350° to 10°)
            if change > 180:
                change = 360 - change
            direction_changes.append(change)
        
        if not direction_changes:
            return {}
        
        direction_changes = np.array(direction_changes)
        
        # Count significant turns
        significant_turns = np.sum(direction_changes > 45)
        moderate_turns = np.sum((direction_changes > 15) & (direction_changes <= 45))
        
        return {
            'average_direction_change_deg': round(np.mean(direction_changes), 2),
            'max_direction_change_deg': round(np.max(direction_changes), 2),
            'total_direction_change_deg': round(np.sum(direction_changes), 1),
            'significant_turns_count': int(significant_turns),
            'moderate_turns_count': int(moderate_turns),
            'route_straightness_index': round(1 / (1 + np.mean(direction_changes) / 180), 3),
            'complexity_score': round(np.sum(direction_changes) / len(points), 2)
        }
    
    @st.cache_data(ttl=3600)  # Cache terrain classification for 1 hour
    def _classify_terrain_type(_self, gradient_hash: str, gradient_analysis: Dict) -> Dict:
        """Classify terrain type based on gradient characteristics for ML features.
        Cached for performance as it's called frequently.
        """
        if not gradient_analysis:
            return {}
        
        # Get terrain distribution percentages
        flat_pct = gradient_analysis.get('flat_sections_percent', 0)
        moderate_climbs_pct = gradient_analysis.get('moderate_climbs_percent', 0)
        steep_climbs_pct = gradient_analysis.get('steep_climbs_percent', 0)
        
        # Determine dominant terrain type for ML classification
        if steep_climbs_pct > 20:
            terrain_type = 'mountainous'
        elif moderate_climbs_pct + steep_climbs_pct > 30:
            terrain_type = 'hilly'
        elif moderate_climbs_pct + steep_climbs_pct > 10:
            terrain_type = 'rolling'
        else:
            terrain_type = 'flat'
        
        return {
            'terrain_type': terrain_type,
            'terrain_distribution': {
                'flat_percent': flat_pct,
                'moderate_climbs_percent': moderate_climbs_pct,
                'steep_climbs_percent': steep_climbs_pct,
                'descents_percent': gradient_analysis.get('descents_percent', 0)
            }
        }
    
    def _estimate_power_requirements(self, gradient_analysis: Dict, total_distance_km: float) -> Dict:
        """Estimate power requirements for the route (ML training features)."""
        if not gradient_analysis or 'segments' not in gradient_analysis:
            return {}
        
        segments = gradient_analysis['segments']
        power_segments = []
        
        # Rider assumptions (70kg rider, reasonable fitness) for standardized calculations
        rider_weight_kg = 70
        bike_weight_kg = 10
        total_weight_kg = rider_weight_kg + bike_weight_kg
        
        # Coefficients for power calculation
        cda = 0.32  # Aerodynamic drag coefficient * area (m²)
        crr = 0.005  # Rolling resistance coefficient
        air_density = 1.225  # kg/m³
        efficiency = 0.95  # Drivetrain efficiency
        
        total_energy_kj = 0
        
        # Use standardized speeds for power calculation (not actual speed estimation)
        speed_by_gradient = {
            'steep': 15,    # >8% grade
            'moderate': 20, # 4-8% grade  
            'light': 25,    # 2-4% grade
            'flat': 30      # <2% grade or downhill
        }
        
        for segment in segments:
            distance_km = segment['distance_m'] / 1000
            gradient_decimal = segment['gradient_percent'] / 100
            
            # Categorize gradient for standardized power calculation
            if gradient_decimal > 0.08:
                speed_kmh = speed_by_gradient['steep']
            elif gradient_decimal > 0.04:
                speed_kmh = speed_by_gradient['moderate']
            elif gradient_decimal > 0.02:
                speed_kmh = speed_by_gradient['light']
            else:
                speed_kmh = speed_by_gradient['flat']
            
            speed_ms = speed_kmh / 3.6
            time_hours = distance_km / speed_kmh
            
            # Power components (physics-based calculation for ML features)
            # Gravity power
            gravity_power = total_weight_kg * 9.81 * speed_ms * gradient_decimal
            
            # Rolling resistance power
            rolling_power = total_weight_kg * 9.81 * crr * speed_ms
            
            # Aerodynamic power (assuming no wind for standardized calculation)
            aero_power = 0.5 * cda * air_density * (speed_ms ** 3)
            
            # Total power
            total_power = (gravity_power + rolling_power + aero_power) / efficiency
            total_power = max(100, total_power)  # Minimum sustainable power
            
            # Energy for this segment
            energy_kj = (total_power * time_hours * 3600) / 1000  # Convert to kJ
            total_energy_kj += energy_kj
            
            power_segments.append({
                'distance_km': distance_km,
                'gradient_percent': segment['gradient_percent'],
                'estimated_power_watts': round(total_power, 0),
                'reference_speed_kmh': speed_kmh,  # Renamed to clarify this is reference, not prediction
                'energy_kj': round(energy_kj, 1)
            })
        
        # Calculate power distribution for ML features
        power_values = [s['estimated_power_watts'] for s in power_segments]
        
        return {
            'average_power_watts': round(np.mean(power_values), 0) if power_values else 0,
            'max_power_watts': round(np.max(power_values), 0) if power_values else 0,
            'normalized_power_watts': round(np.power(np.mean(np.power(power_values, 4)), 0.25), 0) if power_values else 0,
            'total_energy_kj': round(total_energy_kj, 0),
            'energy_per_km_kj': round(total_energy_kj / total_distance_km, 1) if total_distance_km > 0 else 0,
            'power_zones': {
                'endurance_percent': round(np.sum(np.array(power_values) < 200) / len(power_values) * 100, 1) if power_values else 0,
                'tempo_percent': round(np.sum((np.array(power_values) >= 200) & (np.array(power_values) < 300)) / len(power_values) * 100, 1) if power_values else 0,
                'threshold_percent': round(np.sum(np.array(power_values) >= 300) / len(power_values) * 100, 1) if power_values else 0
            },
            'note': 'Power calculations use standardized reference speeds for ML feature consistency'
        }
    
    @st.cache_data(ttl=1800)  # Cache API responses for 30 minutes
    def _query_overpass_api(_self, query: str, max_retries: int = 3) -> Dict:
        """Query the Overpass API with rate limiting and error handling.
        Cached to reduce API calls.
        
        Note: Uses leading underscore on self to exclude from caching key
        """
        for attempt in range(max_retries):
            try:
                time.sleep(_self.request_delay)  # Rate limiting
                response = requests.post(
                    _self.overpass_url,
                    data=query,
                    headers={'Content-Type': 'text/plain; charset=utf-8'},
                    timeout=30
                )
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    print(f"Failed to query Overpass API after {max_retries} attempts: {e}")
                    return {'elements': []}
                time.sleep(2 ** attempt)  # Exponential backoff
        return {'elements': []}
    
    @st.cache_data(ttl=1800)  # Cache traffic data for 30 minutes
    def _get_traffic_infrastructure(_self, bounds: Dict, route_points: List[Dict]) -> Dict:
        """Query OpenStreetMap for traffic lights and major roads near the route.
        Cached to reduce API calls.
        
        Note: Uses leading underscore on self to exclude from caching key
        """
        if not bounds:
            return {'traffic_lights': [], 'major_roads': []}
        
        # Expand bounds slightly to catch nearby infrastructure
        lat_margin = 0.002  # ~200m
        lon_margin = 0.002
        
        south = bounds['south'] - lat_margin
        north = bounds['north'] + lat_margin
        west = bounds['west'] - lon_margin
        east = bounds['east'] + lon_margin
        
        # Query for traffic lights
        traffic_light_query = f"""
        [out:json][timeout:25];
        (
          node["highway"="traffic_signals"]({south},{west},{north},{east});
          node["traffic_signals"]({south},{west},{north},{east});
        );
        out geom;
        """
        
        traffic_lights_data = _self._query_overpass_api(traffic_light_query)
        traffic_lights = []
        
        for element in traffic_lights_data.get('elements', []):
            if element.get('type') == 'node':
                traffic_lights.append({
                    'lat': element['lat'],
                    'lon': element['lon'],
                    'tags': element.get('tags', {})
                })
        
        # Query for major roads (primary, secondary, trunk roads)
        major_roads_query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(motorway|trunk|primary|secondary)$"]({south},{west},{north},{east});
        );
        out geom;
        """
        
        major_roads_data = _self._query_overpass_api(major_roads_query)
        major_roads = []
        
        for element in major_roads_data.get('elements', []):
            if element.get('type') == 'way' and 'geometry' in element:
                road_info = {
                    'id': element['id'],
                    'highway_type': element.get('tags', {}).get('highway', 'unknown'),
                    'name': element.get('tags', {}).get('name', 'Unnamed Road'),
                    'geometry': element['geometry']  # List of lat/lon points
                }
                major_roads.append(road_info)
        
        return {
            'traffic_lights': traffic_lights,
            'major_roads': major_roads
        }
    
    def _find_route_intersections(self, route_points: List[Dict], infrastructure: Dict) -> Dict:
        """Find intersections between the route and traffic infrastructure."""
        traffic_lights = infrastructure.get('traffic_lights', [])
        major_roads = infrastructure.get('major_roads', [])
        
        # Find traffic lights near route points - reduce threshold for better accuracy
        nearby_traffic_lights = []
        traffic_light_threshold = 0.020  # Reduced from 25m to 20m for better accuracy
        
        for route_index, route_point in enumerate(route_points):
            # Skip every 5th point for performance while maintaining coverage
            if route_index % 3 != 0:
                continue
                
            for light in traffic_lights:
                distance = haversine_distance(
                    route_point['lat'], route_point['lon'],
                    light['lat'], light['lon']
                )
                
                # If within 20 meters, consider it a potential stop
                if distance <= traffic_light_threshold:
                    nearby_traffic_lights.append({
                        'route_point_index': route_index,  # Use index from enumerate instead of expensive lookup
                        'route_lat': route_point['lat'],
                        'route_lon': route_point['lon'],
                        'light_lat': light['lat'],
                        'light_lon': light['lon'],
                        'distance_m': distance * 1000,
                        'tags': light.get('tags', {})
                    })
        
        # Find major road crossings - reduce threshold and be more selective
        major_road_crossings = []
        crossing_threshold = 0.012  # Reduced from 15m to 12m for better precision
        
        for road in major_roads:
            road_geometry = road.get('geometry', [])
            highway_type = road.get('highway_type', 'unknown')
            
            # Only consider major roads that typically require stops
            if highway_type not in ['motorway', 'trunk', 'primary', 'secondary']:
                continue
            
            for route_index, route_point in enumerate(route_points):
                # Skip every 5th point for performance while maintaining coverage
                if route_index % 3 != 0:
                    continue
                    
                # Check if route point is close to any segment of the major road
                for i in range(len(road_geometry) - 1):
                    road_start = road_geometry[i]
                    road_end = road_geometry[i + 1]
                    
                    # Calculate distance from route point to road segment
                    distance_to_road = self._point_to_line_distance(
                        route_point['lat'], route_point['lon'],
                        road_start['lat'], road_start['lon'],
                        road_end['lat'], road_end['lon']
                    )
                    
                    if distance_to_road <= crossing_threshold:
                        major_road_crossings.append({
                            'route_point_index': route_index,  # Use index from enumerate
                            'route_lat': route_point['lat'],
                            'route_lon': route_point['lon'],
                            'road_name': road.get('name', 'Unnamed Road'),
                            'highway_type': road.get('highway_type', 'unknown'),
                            'distance_to_road_m': distance_to_road * 1000
                        })
                        break  # Only count once per road segment for this route point
        
        return {
            'traffic_light_intersections': nearby_traffic_lights,
            'major_road_crossings': major_road_crossings
        }
    
    def _point_to_line_distance(self, px: float, py: float, 
                               x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate the shortest distance from a point to a line segment in decimal degrees."""
        # Convert to approximate meters for calculation
        A = px - x1
        B = py - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            # Line segment is actually a point
            return haversine_distance(px, py, x1, y1)
        
        param = dot / len_sq
        
        if param < 0:
            xx = x1
            yy = y1
        elif param > 1:
            xx = x2
            yy = y2
        else:
            xx = x1 + param * C
            yy = y1 + param * D
        
        return haversine_distance(px, py, xx, yy)
    
    def _analyze_traffic_stops(self, points: List[Dict], stats: Dict) -> Dict:
        """Analyze potential traffic stops along the route."""
        if len(points) < 2 or not stats.get('bounds'):
            return {'analysis_available': False, 'reason': 'Insufficient route data'}
        
        try:
            # Get traffic infrastructure from OpenStreetMap
            infrastructure = self._get_traffic_infrastructure(stats['bounds'], points)
            
            # Find intersections with route
            intersections = self._find_route_intersections(points, infrastructure)
            
            # Calculate metrics
            total_distance_km = stats.get('total_distance_km', 0)
            traffic_lights_count = len(intersections['traffic_light_intersections'])
            major_crossings_count = len(intersections['major_road_crossings'])
            total_stops = traffic_lights_count + major_crossings_count
            
            # Remove duplicates (same intersection counted multiple times)
            unique_traffic_lights = self._remove_duplicate_stops(
                intersections['traffic_light_intersections'], threshold_m=75  # Increased for traffic lights
            )
            unique_major_crossings = self._remove_duplicate_stops(
                intersections['major_road_crossings'], threshold_m=30  # Reduced for road crossings
            )
            
            unique_total_stops = len(unique_traffic_lights) + len(unique_major_crossings)
            
            # Calculate stop density and spacing
            stop_density = unique_total_stops / max(total_distance_km, 0.1)
            
            # Estimate time penalty (rough estimates)
            # Traffic lights: 0-60 seconds (avg 20s), Major crossings: 0-10 seconds (avg 3s)
            estimated_light_delay_minutes = len(unique_traffic_lights) * 0.33  # 20s avg per light
            estimated_crossing_delay_minutes = len(unique_major_crossings) * 0.05  # 3s avg per crossing
            total_estimated_delay_minutes = estimated_light_delay_minutes + estimated_crossing_delay_minutes
            
            # Calculate average distance between stops
            if unique_total_stops > 1:
                avg_distance_between_stops_km = total_distance_km / unique_total_stops
            else:
                avg_distance_between_stops_km = total_distance_km
            
            return {
                'analysis_available': True,
                'traffic_lights_detected': len(unique_traffic_lights),
                'major_road_crossings': len(unique_major_crossings),
                'total_potential_stops': unique_total_stops,
                'stop_density_per_km': round(stop_density, 2),
                'average_distance_between_stops_km': round(avg_distance_between_stops_km, 2),
                'estimated_time_penalty_minutes': round(total_estimated_delay_minutes, 1),
                'traffic_light_locations': unique_traffic_lights,
                'major_crossing_locations': unique_major_crossings,
                'infrastructure_summary': {
                    'total_traffic_lights_in_area': len(infrastructure['traffic_lights']),
                    'total_major_roads_in_area': len(infrastructure['major_roads']),
                    'route_intersections_found': unique_total_stops
                }
            }
            
        except Exception as e:
            return {
                'analysis_available': False,
                'reason': f'Error during traffic analysis: {str(e)}',
                'estimated_stops': 'Unable to calculate'
            }
    
    def _analyze_traffic_stops_with_progress(self, points: List[Dict], stats: Dict, show_progress: bool = True) -> Dict:
        """Analyze potential traffic stops along the route with progress tracking."""
        self.logger.info("🚦 Starting detailed traffic stop analysis")
        analysis_start_time = time.time()
        
        if len(points) < 2 or not stats.get('bounds'):
            self.logger.warning("Insufficient route data for traffic analysis")
            return {'analysis_available': False, 'reason': 'Insufficient route data'}
        
        # Create traffic analysis progress tracker
        tracker = None
        if show_progress:
            tracker = create_traffic_analysis_tracker()
            tracker.start()
        
        try:
            # Step 1: Bounds check
            if tracker:
                tracker.start_step("bounds_check")
                
            total_distance_km = stats.get('total_distance_km', 0)
            self.logger.debug(f"Traffic analysis bounds: {stats['bounds']}, distance: {total_distance_km}km")
            
            if tracker:
                tracker.complete_step("bounds_check")
                tracker.start_step("fetch_infrastructure")
            
            # Step 2: Get traffic infrastructure from OpenStreetMap
            step_start_time = time.time()
            self.logger.info("🗺️ Fetching traffic infrastructure data from OpenStreetMap")
            infrastructure = self._get_traffic_infrastructure(stats['bounds'], points)
            
            step_duration = time.time() - step_start_time
            log_performance(self.logger, "fetch_traffic_infrastructure", step_duration,
                          f"traffic_lights={len(infrastructure.get('traffic_lights', []))}, roads={len(infrastructure.get('major_roads', []))}")
            self.logger.info(f"✅ Infrastructure fetched: {len(infrastructure.get('traffic_lights', []))} traffic lights, {len(infrastructure.get('major_roads', []))} major roads")
            
            if tracker:
                tracker.complete_step("fetch_infrastructure")
                tracker.start_step("find_intersections")
            
            # Step 3: Find intersections with route
            step_start_time = time.time()
            self.logger.info("🔍 Finding intersections between route and infrastructure")
            intersections = self._find_route_intersections(points, infrastructure)
            
            step_duration = time.time() - step_start_time
            log_performance(self.logger, "find_route_intersections", step_duration)
            self.logger.info(f"✅ Intersections found: {len(intersections['traffic_light_intersections'])} traffic light intersections, {len(intersections['major_road_crossings'])} road crossings")
            
            if tracker:
                tracker.complete_step("find_intersections")
                tracker.start_step("calculate_metrics")
            
            # Step 4: Calculate metrics
            traffic_lights_count = len(intersections['traffic_light_intersections'])
            major_crossings_count = len(intersections['major_road_crossings'])
            total_stops = traffic_lights_count + major_crossings_count
            
            if tracker:
                tracker.complete_step("calculate_metrics")
                tracker.start_step("remove_duplicates")
            
            # Step 5: Remove duplicates (same intersection counted multiple times)
            step_start_time = time.time()
            self.logger.info("🧹 Removing duplicate stops")
            unique_traffic_lights = self._remove_duplicate_stops(
                intersections['traffic_light_intersections'], threshold_m=50  # Reduced from 75m to 50m for better accuracy
            )
            unique_major_crossings = self._remove_duplicate_stops(
                intersections['major_road_crossings'], threshold_m=25  # Reduced from 30m to 25m for better precision
            )
            
            step_duration = time.time() - step_start_time
            unique_total_stops = len(unique_traffic_lights) + len(unique_major_crossings)
            log_performance(self.logger, "remove_duplicate_stops", step_duration,
                          f"original={total_stops}, unique={unique_total_stops}")
            self.logger.info(f"✅ Duplicates removed: {total_stops} → {unique_total_stops} unique stops")
            
            # Calculate stop density and spacing
            stop_density = unique_total_stops / max(total_distance_km, 0.1)
            
            # Estimate time penalty (rough estimates)
            # Traffic lights: 0-60 seconds (avg 20s), Major crossings: 0-10 seconds (avg 3s)
            estimated_light_delay_minutes = len(unique_traffic_lights) * 0.33  # 20s avg per light
            estimated_crossing_delay_minutes = len(unique_major_crossings) * 0.05  # 3s avg per crossing
            total_estimated_delay_minutes = estimated_light_delay_minutes + estimated_crossing_delay_minutes
            
            # Calculate average distance between stops
            if unique_total_stops > 1:
                avg_distance_between_stops_km = total_distance_km / unique_total_stops
            else:
                avg_distance_between_stops_km = total_distance_km
            
            if tracker:
                tracker.complete_step("remove_duplicates")
                tracker.finish()
            
            # Log completion with summary
            total_duration = time.time() - analysis_start_time
            log_performance(self.logger, "traffic_analysis_complete", total_duration,
                          f"stops={unique_total_stops}, density={stop_density:.2f}/km, delay={total_estimated_delay_minutes:.1f}min")
            self.logger.info(f"🎉 Traffic analysis completed: {unique_total_stops} total stops ({len(unique_traffic_lights)} lights, {len(unique_major_crossings)} crossings)")
            
            return {
                'analysis_available': True,
                'traffic_lights_detected': len(unique_traffic_lights),
                'major_road_crossings': len(unique_major_crossings),
                'total_potential_stops': unique_total_stops,
                'stop_density_per_km': round(stop_density, 2),
                'average_distance_between_stops_km': round(avg_distance_between_stops_km, 2),
                'estimated_time_penalty_minutes': round(total_estimated_delay_minutes, 1),
                'traffic_light_locations': unique_traffic_lights,
                'major_crossing_locations': unique_major_crossings,
                'infrastructure_summary': {
                    'total_traffic_lights_in_area': len(infrastructure['traffic_lights']),
                    'total_major_roads_in_area': len(infrastructure['major_roads']),
                    'route_intersections_found': unique_total_stops
                }
            }
            
        except Exception as e:
            total_duration = time.time() - analysis_start_time
            log_error(self.logger, e, "Traffic analysis failed")
            log_performance(self.logger, "traffic_analysis_failed", total_duration)
            self.logger.error("💥 Traffic analysis failed with error")
            
            if tracker:
                tracker.fail_step("traffic_analysis", str(e))
                tracker.finish()
            return {
                'analysis_available': False,
                'reason': f'Error during traffic analysis: {str(e)}',
                'estimated_stops': 'Unable to calculate'
            }
    
    def _remove_duplicate_stops(self, stops: List[Dict], threshold_m: float = 50) -> List[Dict]:
        """Remove duplicate stops that are within threshold distance of each other.
        Optimized with early termination and better distance management.
        """
        if not stops:
            return []
        
        unique_stops = []
        threshold_km = threshold_m / 1000
        
        for stop in stops:
            is_duplicate = False
            
            # Check against existing unique stops with early termination
            for unique_stop in unique_stops:
                distance = haversine_distance(
                    stop['route_lat'], stop['route_lon'],
                    unique_stop['route_lat'], unique_stop['route_lon']
                )
                
                if distance <= threshold_km:
                    is_duplicate = True
                    break  # Early termination - no need to check remaining stops
            
            if not is_duplicate:
                unique_stops.append(stop)
        
        return unique_stops
    
    def _calculate_difficulty_rating(self, stats: Dict) -> str:
        """Calculate a simple difficulty rating based on route metrics."""
        try:
            distance = stats.get('total_distance_km', 0)
            elevation_gain = stats.get('total_elevation_gain_m', 0)
            gradient_analysis = stats.get('gradient_analysis', {})
            
            # Calculate difficulty score based on multiple factors
            score = 0
            
            # Distance factor (longer = harder)
            if distance > 100:
                score += 3
            elif distance > 50:
                score += 2
            elif distance > 20:
                score += 1
            
            # Elevation factor (more climbing = harder)
            elevation_per_km = elevation_gain / max(distance, 1)
            if elevation_per_km > 50:
                score += 3
            elif elevation_per_km > 25:
                score += 2
            elif elevation_per_km > 10:
                score += 1
            
            # Gradient factor (steep sections = harder)
            steep_percent = gradient_analysis.get('steep_climbs_percent', 0)
            if steep_percent > 15:
                score += 2
            elif steep_percent > 5:
                score += 1
            
            # Convert score to rating
            if score >= 6:
                return "Very Hard"
            elif score >= 4:
                return "Hard"
            elif score >= 2:
                return "Moderate"
            else:
                return "Easy"
                
        except Exception:
            return "Unknown"
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    @st.cache_data(ttl=3600)  # Cache parsed GPX data for 1 hour
    def parse_gpx_file(_self, gpx_content: str) -> Dict:
        """Parse GPX file content and extract route data.
        
        Args:
            gpx_content: String content of the GPX file
            
        Returns:
            Dictionary containing parsed route data
            
        Note: Uses leading underscore on self to exclude from caching key
        """
        try:
            gpx = gpxpy.parse(gpx_content)
            
            route_data = {
                'metadata': {},
                'tracks': [],
                'routes': [],
                'waypoints': []
            }
            
            # Extract metadata
            if hasattr(gpx, 'name') and gpx.name:
                route_data['metadata']['name'] = gpx.name
            if hasattr(gpx, 'description') and gpx.description:
                route_data['metadata']['description'] = gpx.description
            if hasattr(gpx, 'time') and gpx.time:
                route_data['metadata']['time'] = gpx.time.isoformat()
            
            # Process tracks
            for track in gpx.tracks:
                track_data = {
                    'name': track.name or 'Unnamed Track',
                    'segments': []
                }
                
                for segment in track.segments:
                    points = []
                    for point in segment.points:
                        point_data = {
                            'lat': point.latitude,
                            'lon': point.longitude,
                            'elevation': point.elevation,
                            'time': point.time.isoformat() if point.time else None
                        }
                        points.append(point_data)
                    
                    track_data['segments'].append(points)
                
                route_data['tracks'].append(track_data)
            
            # Process routes (planned routes without time data)
            for route in gpx.routes:
                route_points = []
                for point in route.points:
                    point_data = {
                        'lat': point.latitude,
                        'lon': point.longitude,
                        'elevation': point.elevation,
                        'name': point.name
                    }
                    route_points.append(point_data)
                
                route_data['routes'].append({
                    'name': route.name or 'Unnamed Route',
                    'points': route_points
                })
            
            # Process waypoints
            for waypoint in gpx.waypoints:
                waypoint_data = {
                    'lat': waypoint.latitude,
                    'lon': waypoint.longitude,
                    'elevation': waypoint.elevation,
                    'name': waypoint.name,
                    'description': waypoint.description
                }
                route_data['waypoints'].append(waypoint_data)
            
            # Extract flattened coordinates array for UI components (especially map display)
            coordinates = []
            # Add all track segment points
            for track in route_data['tracks']:
                for segment in track['segments']:
                    coordinates.extend(segment)
            # Add all route points
            for route in route_data['routes']:
                coordinates.extend(route.get('points', []))
            
            route_data['coordinates'] = coordinates
            
            return route_data
            
        except Exception as e:
            raise ValueError(f"Error parsing GPX file: {str(e)}")
    
    @st.cache_data(ttl=7200)  # Cache for 2 hours
    def parse_route_file(_self, file_content_hash: str, file_content: bytes, filename: str) -> Dict:
        """Parse route file content (GPX only) and extract route data.
        Cached for performance as GPX parsing can be expensive for large files.
        
        Args:
            file_content_hash: Hash of file content for caching
            file_content: File content as bytes
            filename: Original filename to determine file type
            
        Returns:
            Dictionary containing parsed route data
        """
        logger = get_logger(__name__)
        log_function_entry(logger, "parse_route_file", filename=filename, size_bytes=len(file_content))
        start_time = time.time()
        
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'gpx':
                try:
                    logger.info(f"Starting GPX file parsing: {filename}")
                    gpx_content = file_content.decode('utf-8')
                    result = _self.parse_gpx_file(gpx_content)
                    
                    duration = time.time() - start_time
                    log_performance(logger, f"parse_route_file({filename})", duration, 
                                  f"points={result.get('total_points', 0)}, tracks={len(result.get('tracks', []))}")
                    
                    log_function_exit(logger, "parse_route_file", result)
                    return result
                    
                except UnicodeDecodeError as e:
                    logger.error(f"UTF-8 decode error for file {filename}: {str(e)}")
                    raise ValueError("Invalid GPX file: Unable to decode as UTF-8")
            else:
                logger.warning(f"Unsupported file type attempted: {file_extension} for file {filename}")
                raise ValueError(f"Unsupported file type: {file_extension}. Only GPX files are supported.")
                
        except Exception as e:
            duration = time.time() - start_time
            log_error(logger, e, f"Failed to parse route file {filename}")
            log_performance(logger, f"parse_route_file({filename}) [FAILED]", duration)
            raise
    
    def process_route(self, file_path: str) -> Optional[Dict]:
        """
        Process a route file from filesystem path.
        
        Args:
            file_path: Path to the GPX file
            
        Returns:
            Complete route data with statistics or None if processing failed
        """
        logger = get_logger(__name__)
        log_function_entry(logger, "process_route", file_path=file_path)
        
        try:
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            
            # Parse the route file
            file_content_hash = hashlib.md5(file_content).hexdigest()
            route_data = self.parse_route_file(file_content_hash, file_content, filename)
            
            if not route_data:
                logger.error(f"Failed to parse route file: {filename}")
                return None
            
            # Calculate statistics
            route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
            stats = self.calculate_route_statistics(
                route_data_hash, 
                route_data, 
                include_traffic_analysis=self.config.app.enable_traffic_analysis, 
                show_progress=True
            )
            
            # Combine route data and statistics
            complete_route_data = {
                'route_data': route_data,
                'statistics': stats,
                'filename': filename,
                'processed_at': datetime.now().isoformat()
            }
            
            log_function_exit(logger, "process_route")
            return complete_route_data
            
        except Exception as e:
            log_error(logger, e, f"Failed to process route file {file_path}")
            log_function_exit(logger, "process_route")
            return None
    
    def process_route_data(self, route_data: Dict) -> Optional[Dict]:
        """
        Process pre-parsed route data (e.g., from Strava imports).
        
        Args:
            route_data: Already parsed route data structure
            
        Returns:
            Complete route data with statistics or None if processing failed
        """
        logger = get_logger(__name__)
        log_function_entry(logger, "process_route_data")
        
        try:
            if not route_data or 'points' not in route_data:
                logger.error("Invalid route data: missing points")
                return None
            
            # Convert flat points structure to GPX-like structure for statistics calculation
            converted_route_data = {
                'metadata': route_data.get('metadata', {}),
                'tracks': [],
                'routes': [],
                'waypoints': []
            }
            
            # Convert points to track structure (most common for activity data)
            if route_data['points']:
                track_points = []
                for point in route_data['points']:
                    # Convert from Strava format (latitude/longitude) to GPX format (lat/lon)
                    converted_point = {
                        'lat': point.get('latitude', point.get('lat', 0)),
                        'lon': point.get('longitude', point.get('lon', 0)),
                        'elevation': point.get('elevation', 0),
                        'time': point.get('time')
                    }
                    track_points.append(converted_point)
                
                # Add as a single track with one segment
                converted_route_data['tracks'] = [{
                    'name': route_data.get('metadata', {}).get('name', 'Imported Route'),
                    'segments': [track_points]
                }]
            
            # Extract flattened coordinates array for UI components (especially map display)
            # This mirrors the logic from parse_gpx_file to ensure consistency
            coordinates = []
            # Add all track segment points
            for track in converted_route_data['tracks']:
                for segment in track['segments']:
                    coordinates.extend(segment)
            # Add all route points
            for route in converted_route_data['routes']:
                coordinates.extend(route.get('points', []))
            
            converted_route_data['coordinates'] = coordinates
            
            # Calculate statistics using the converted structure
            route_data_hash = hashlib.md5(str(converted_route_data).encode()).hexdigest()
            stats = self.calculate_route_statistics(
                route_data_hash, 
                converted_route_data, 
                include_traffic_analysis=self.config.app.enable_traffic_analysis, 
                show_progress=True
            )
            
            # Combine original route data and statistics
            complete_route_data = {
                'route_data': converted_route_data,  # Use converted structure for consistency
                'statistics': stats,
                'filename': route_data.get('filename', 'unknown_route.gpx'),
                'processed_at': datetime.now().isoformat()
            }
            
            log_function_exit(logger, "process_route_data")
            return complete_route_data
            
        except Exception as e:
            log_error(logger, e, "Failed to process route data")
            log_function_exit(logger, "process_route_data")
            return None
    
    @st.cache_data(ttl=7200)  # Cache route statistics for 2 hours
    def calculate_route_statistics(_self, route_data_hash: str, route_data: Dict, include_traffic_analysis: bool = None, show_progress: bool = True) -> Dict:
        """Calculate comprehensive statistics for the route including ML-ready features.
        Cached for performance as route statistics calculation is computationally expensive.
        
        Args:
            route_data_hash: Hash of route data for caching
            route_data: Parsed route data dictionary
            include_traffic_analysis: Whether to include traffic stop analysis (slow). 
                                    If None, uses configuration setting.
            show_progress: Whether to show progress indicators
            
        Returns:
            Dictionary containing route statistics and advanced metrics
            
        Note: Uses leading underscore on self to exclude from caching key
        """
        logger = get_logger(__name__)
        
        # Handle default value for include_traffic_analysis
        if include_traffic_analysis is None:
            include_traffic_analysis = _self.config.app.enable_traffic_analysis
        
        log_function_entry(logger, "calculate_route_statistics", 
                          include_traffic=include_traffic_analysis, show_progress=show_progress)
        
        analysis_start_time = time.time()
        logger.info("🚀 Starting comprehensive route analysis")
        logger.info(f"🚦 Traffic analysis enabled: {include_traffic_analysis}")
        
        # Initialize progress tracker if requested
        tracker = None
        if show_progress:
            tracker = create_route_analysis_tracker()
            tracker.start()
        
        try:
            # Step 1: Parse and collect route data
            step_start_time = time.time()
            logger.info("📄 Step 1: Starting route data parsing")
            if tracker:
                tracker.start_step("parse_data")
            
            stats = {
                'total_distance_km': 0,
                'total_elevation_gain_m': 0,
                'total_elevation_loss_m': 0,
                'max_elevation_m': None,
                'min_elevation_m': None,
                'total_points': 0,
                'bounds': None
            }
            
            all_points = []
            
            # Collect all points from tracks and routes
            for track in route_data.get('tracks', []):
                for segment in track.get('segments', []):
                    all_points.extend(segment)
            
            for route in route_data.get('routes', []):
                all_points.extend(route.get('points', []))
            
            if not all_points:
                logger.warning("No route points found in route data")
                if tracker:
                    tracker.fail_step("parse_data", "No route points found")
                    tracker.finish()
                return stats
            
            step_duration = time.time() - step_start_time
            log_performance(logger, "parse_route_data", step_duration, f"collected {len(all_points)} points")
            logger.info(f"✅ Step 1 completed: Parsed {len(all_points)} route points")
            
            if tracker:
                tracker.complete_step("parse_data")
                tracker.start_step("basic_stats")
            
            # Step 2: Calculate basic statistics
            step_start_time = time.time()
            logger.info("📊 Step 2: Starting basic statistics calculation")
            stats['total_points'] = len(all_points)
            
            # Calculate bounds
            lats = [p['lat'] for p in all_points]
            lons = [p['lon'] for p in all_points]
            stats['bounds'] = {
                'north': max(lats),
                'south': min(lats),
                'east': max(lons),
                'west': min(lons)
            }
            
            # Calculate basic distance and elevation statistics
            total_distance = 0
            elevations = [p['elevation'] for p in all_points if p['elevation'] is not None]
            
            # Track elevation data quality
            points_with_elevation = len(elevations)
            elevation_data_percentage = (points_with_elevation / len(all_points)) * 100 if all_points else 0
            
            stats['elevation_data_quality'] = {
                'has_elevation_data': points_with_elevation > 0,
                'points_with_elevation': points_with_elevation,
                'total_points': len(all_points),
                'elevation_data_percentage': round(elevation_data_percentage, 1)
            }
            
            if elevations:
                stats['max_elevation_m'] = max(elevations)
                stats['min_elevation_m'] = min(elevations)
                
                # Check for meaningful elevation variation (more than 1 meter difference)
                elevation_range = max(elevations) - min(elevations)
                stats['elevation_data_quality']['elevation_range_m'] = round(elevation_range, 1)
                stats['elevation_data_quality']['has_elevation_variation'] = elevation_range > 1.0
                
                # Calculate elevation gain/loss
                for i in range(1, len(elevations)):
                    diff = elevations[i] - elevations[i-1]
                    if diff > 0:
                        stats['total_elevation_gain_m'] += diff
                    else:
                        stats['total_elevation_loss_m'] += abs(diff)
            else:
                stats['elevation_data_quality']['elevation_range_m'] = 0
                stats['elevation_data_quality']['has_elevation_variation'] = False
            
            # Calculate total distance
            for i in range(1, len(all_points)):
                prev_point = all_points[i-1]
                curr_point = all_points[i]
                distance = haversine_distance(
                    prev_point['lat'], prev_point['lon'],
                    curr_point['lat'], curr_point['lon']
                )
                total_distance += distance
            
            stats['total_distance_km'] = round(total_distance, 2)
            stats['total_elevation_gain_m'] = round(stats['total_elevation_gain_m'], 1)
            stats['total_elevation_loss_m'] = round(stats['total_elevation_loss_m'], 1)
            
            step_duration = time.time() - step_start_time
            log_performance(logger, "calculate_basic_stats", step_duration, 
                          f"distance={stats['total_distance_km']}km, gain={stats['total_elevation_gain_m']}m")
            logger.info(f"✅ Step 2 completed: Distance={stats['total_distance_km']}km, Elevation gain={stats['total_elevation_gain_m']}m")
            
            if tracker:
                tracker.complete_step("basic_stats")
            
            # Advanced ML-ready metrics (only if we have enough points)
            if len(all_points) >= 2:
                # Create hash for caching based on points data
                points_hash = hashlib.md5(str([(p['lat'], p['lon'], p.get('elevation')) for p in all_points]).encode()).hexdigest()
                
                # Step 3 & 4: Combined gradient and climb analysis (optimized)
                step_start_time = time.time()
                logger.info("⛰️ Step 3-4: Starting gradient and climb analysis")
                if tracker:
                    tracker.start_step("gradients")
                gradient_analysis, climb_analysis = _self._analyze_gradients_and_climbs_combined(points_hash, all_points)
                stats['gradient_analysis'] = gradient_analysis
                stats['climb_analysis'] = climb_analysis
                
                step_duration = time.time() - step_start_time
                log_performance(logger, "analyze_gradients_and_climbs", step_duration,
                              f"climbs={len(climb_analysis.get('climbs', []))}, max_gradient={gradient_analysis.get('max_gradient', 0):.1f}%")
                logger.info(f"✅ Step 3-4 completed: Found {len(climb_analysis.get('climbs', []))} climbs, max gradient {gradient_analysis.get('max_gradient', 0):.1f}%")
                
                if tracker:
                    tracker.complete_step("gradients")
                    tracker.complete_step("climbs")
                
                # Step 5: Route complexity analysis
                step_start_time = time.time()
                logger.info("🗺️ Step 5: Starting route complexity analysis")
                if tracker:
                    tracker.start_step("complexity")
                complexity_analysis = _self._analyze_route_complexity(points_hash, all_points)
                stats['complexity_analysis'] = complexity_analysis
                
                step_duration = time.time() - step_start_time
                log_performance(logger, "analyze_route_complexity", step_duration,
                              f"complexity_score={complexity_analysis.get('complexity_score', 0):.2f}")
                logger.info(f"✅ Step 5 completed: Complexity score {complexity_analysis.get('complexity_score', 0):.2f}")
                
                if tracker:
                    tracker.complete_step("complexity")
                
                # Step 6: Terrain classification for ML features
                step_start_time = time.time()
                logger.info("🏔️ Step 6: Starting terrain classification")
                if tracker:
                    tracker.start_step("terrain")
                gradient_hash = hashlib.md5(str(gradient_analysis).encode()).hexdigest()
                terrain_analysis = _self._classify_terrain_type(gradient_hash, gradient_analysis)
                stats['terrain_analysis'] = terrain_analysis
                
                step_duration = time.time() - step_start_time
                log_performance(logger, "classify_terrain_type", step_duration,
                              f"terrain={terrain_analysis.get('primary_terrain_type', 'unknown')}")
                logger.info(f"✅ Step 6 completed: Primary terrain type {terrain_analysis.get('primary_terrain_type', 'unknown')}")
                
                if tracker:
                    tracker.complete_step("terrain")
                
                # Step 7: Power requirements analysis for ML features
                step_start_time = time.time()
                logger.info("⚡ Step 7: Starting power requirements analysis")
                if tracker:
                    tracker.start_step("power")
                power_analysis = _self._estimate_power_requirements(gradient_analysis, total_distance)
                stats['power_analysis'] = power_analysis
                
                step_duration = time.time() - step_start_time
                log_performance(logger, "estimate_power_requirements", step_duration,
                              f"avg_power={power_analysis.get('estimated_average_power_w', 0):.0f}W")
                logger.info(f"✅ Step 7 completed: Estimated average power {power_analysis.get('estimated_average_power_w', 0):.0f}W")
                
                if tracker:
                    tracker.complete_step("power")
                
                # Step 8: Generate ML features
                step_start_time = time.time()
                logger.info("🤖 Step 8: Starting ML features generation")
                if tracker:
                    tracker.start_step("ml_features")
                
                # Additional derived metrics for ML
                ml_features = {
                    'route_density_points_per_km': round(len(all_points) / max(total_distance, 0.1), 1),
                    'elevation_range_m': (stats['max_elevation_m'] - stats['min_elevation_m']) if elevations else 0,
                    'elevation_variation_index': round(stats['total_elevation_gain_m'] / max(total_distance, 0.1), 1),
                    'route_compactness': round(total_distance / max(
                        haversine_distance(stats['bounds']['north'], stats['bounds']['west'],
                                         stats['bounds']['south'], stats['bounds']['east']), 0.1), 2),
                    'difficulty_index': round((
                        gradient_analysis.get('steep_climbs_percent', 0) * 3 +
                        gradient_analysis.get('moderate_climbs_percent', 0) * 1.5 +
                        complexity_analysis.get('complexity_score', 0) * 0.5
                    ) / 100, 3)
                }
                
                stats['ml_features'] = ml_features
                step_duration = time.time() - step_start_time
                log_performance(logger, "generate_ml_features", step_duration,
                              f"difficulty_index={ml_features.get('difficulty_index', 0):.3f}")
                logger.info(f"✅ Step 8 completed: Difficulty index {ml_features.get('difficulty_index', 0):.3f}")
                
                if tracker:
                    tracker.complete_step("ml_features")
                
                # Traffic stop analysis (optional - can be very slow)
                if include_traffic_analysis:
                    step_start_time = time.time()
                    logger.info("🚦 Step 9: Starting traffic stop analysis (optional)")
                    try:
                        # Use separate progress tracker for traffic analysis
                        if show_progress:
                            st.markdown("---")
                            st.markdown("### 🚦 Additional Traffic Analysis")
                        traffic_analysis = _self._analyze_traffic_stops_with_progress(all_points, stats, show_progress)
                        stats['traffic_analysis'] = traffic_analysis
                        
                        step_duration = time.time() - step_start_time
                        log_performance(logger, "analyze_traffic_stops", step_duration,
                                      f"stops={traffic_analysis.get('total_potential_stops', 0)}, lights={traffic_analysis.get('traffic_lights_detected', 0)}")
                        logger.info(f"✅ Step 9 completed: Found {traffic_analysis.get('total_potential_stops', 0)} potential stops, {traffic_analysis.get('traffic_lights_detected', 0)} traffic lights")
                        
                        # Add traffic-related ML features if traffic analysis was successful
                        if traffic_analysis.get('analysis_available'):
                            ml_features.update({
                                'stop_density_per_km': traffic_analysis.get('stop_density_per_km', 0),
                                'estimated_stop_time_penalty_min': traffic_analysis.get('estimated_time_penalty_minutes', 0),
                                'traffic_complexity_factor': round(
                                    traffic_analysis.get('stop_density_per_km', 0) * 0.1 + 
                                    (traffic_analysis.get('traffic_lights_detected', 0) * 0.02), 3
                                )
                            })
                    except Exception as e:
                        step_duration = time.time() - step_start_time
                        log_error(logger, e, "Traffic analysis failed")
                        log_performance(logger, "analyze_traffic_stops [FAILED]", step_duration)
                        logger.warning(f"⚠️ Step 9 failed: Traffic analysis error - {str(e)}")
                        
                        stats['traffic_analysis'] = {
                            'analysis_available': False,
                            'reason': f'Traffic analysis failed: {str(e)}',
                            'traffic_lights_detected': 0,
                            'major_road_crossings': 0,
                            'total_potential_stops': 0
                        }
                else:
                    logger.info("🚦 Step 9: Skipping traffic analysis (disabled for performance)")
                    stats['traffic_analysis'] = {
                        'analysis_available': False,
                        'reason': 'Traffic analysis disabled for performance',
                        'traffic_lights_detected': 0,
                        'major_road_crossings': 0,
                        'total_potential_stops': 0
                    }
            
            # Complete progress tracking
            if tracker:
                tracker.finish()
            
            # Flatten key metrics for UI consumption
            # Extract commonly used metrics from nested analysis objects to top level
            gradient_analysis = stats.get('gradient_analysis', {})
            complexity_analysis = stats.get('complexity_analysis', {})
            power_analysis = stats.get('power_analysis', {})
            traffic_analysis = stats.get('traffic_analysis', {})
            
            # Add UI-expected metrics at top level
            stats.update({
                # Gradient metrics
                'average_gradient': gradient_analysis.get('average_gradient_percent', 0),
                'max_gradient': gradient_analysis.get('max_gradient_percent', 0),
                
                # Difficulty and complexity
                'difficulty_rating': _self._calculate_difficulty_rating(stats),
                'route_complexity_score': complexity_analysis.get('complexity_score', 0),
                
                # Traffic metrics (for UI display)
                'traffic_points': traffic_analysis.get('traffic_lights_detected', 0),
                'intersections': traffic_analysis.get('major_road_crossings', 0),
            })
            
            # Log completion with summary statistics
            total_duration = time.time() - analysis_start_time
            log_performance(logger, "calculate_route_statistics [COMPLETE]", total_duration,
                          f"distance={stats['total_distance_km']}km, points={stats['total_points']}, climbs={len(stats.get('climb_analysis', {}).get('climbs', []))}")
            
            logger.info(f"🎉 Route analysis completed successfully!")
            logger.info(f"📈 Final summary: {stats['total_distance_km']}km route with {stats['total_points']} points, {stats['total_elevation_gain_m']}m elevation gain")
            log_function_exit(logger, "calculate_route_statistics", stats)
            
            return stats
            
        except Exception as e:
            total_duration = time.time() - analysis_start_time
            log_error(logger, e, "Route analysis failed")
            log_performance(logger, "calculate_route_statistics [FAILED]", total_duration)
            logger.error("💥 Route analysis failed with error")
            
            if tracker:
                tracker.fail_step("analysis", str(e))
                tracker.finish()
            raise
    
    @st.cache_data(ttl=7200)  # Cache dataframe creation for 2 hours as it's expensive
    def create_analysis_dataframe(_self, route_data_hash: str, route_data: Dict, stats: Dict) -> pd.DataFrame:
        """Create a structured DataFrame with all route analysis data.
        Cached for performance as dataframe creation is computationally expensive.
        
        Args:
            route_data_hash: Hash of route data for caching
            route_data: Route data dictionary
            stats: Route statistics dictionary
            
        Returns:
            Pandas DataFrame with comprehensive route analysis
            
        Note: Uses leading underscore on self to exclude from caching key
            route_data: Parsed route data
            stats: Route statistics
            
        Returns:
            Pandas DataFrame with comprehensive analysis data
        """
        # Collect all points
        all_points = []
        for track in route_data.get('tracks', []):
            for segment in track.get('segments', []):
                all_points.extend(segment)
        for route in route_data.get('routes', []):
            all_points.extend(route.get('points', []))
        
        if not all_points:
            return pd.DataFrame()
        
        # Create base dataframe with point data
        df_data = []
        for i, point in enumerate(all_points):
            row = {
                'point_index': i,
                'latitude': point['lat'],
                'longitude': point['lon'],
                'elevation_m': point.get('elevation'),
                'time': point.get('time')
            }
            
            # Add distance calculations
            if i > 0:
                prev_point = all_points[i-1]
                distance_segment = haversine_distance(
                    prev_point['lat'], prev_point['lon'],
                    point['lat'], point['lon']
                ) * 1000  # Convert to meters
                row['distance_from_previous_m'] = distance_segment
                row['cumulative_distance_m'] = df_data[i-1]['cumulative_distance_m'] + distance_segment
                
                # Add gradient if elevation available
                if point.get('elevation') is not None and prev_point.get('elevation') is not None:
                    elevation_change = point['elevation'] - prev_point['elevation']
                    gradient = calculate_gradient(distance_segment, elevation_change)
                    row['gradient_percent'] = gradient
                    row['elevation_change_m'] = elevation_change
            else:
                row['distance_from_previous_m'] = 0
                row['cumulative_distance_m'] = 0
                row['gradient_percent'] = 0
                row['elevation_change_m'] = 0
            
            df_data.append(row)
        
        df = pd.DataFrame(df_data)
        
        # Add summary statistics as metadata
        df.attrs['route_summary'] = {
            'total_distance_km': stats.get('total_distance_km', 0),
            'total_elevation_gain_m': stats.get('total_elevation_gain_m', 0),
            'total_elevation_loss_m': stats.get('total_elevation_loss_m', 0),
            'max_elevation_m': stats.get('max_elevation_m'),
            'min_elevation_m': stats.get('min_elevation_m'),
            'total_points': stats.get('total_points', 0)
        }
        
        # Add advanced analysis as metadata if available
        if stats.get('gradient_analysis'):
            df.attrs['gradient_analysis'] = stats['gradient_analysis']
        if stats.get('climb_analysis'):
            df.attrs['climb_analysis'] = stats['climb_analysis']
        if stats.get('complexity_analysis'):
            df.attrs['complexity_analysis'] = stats['complexity_analysis']
        if stats.get('terrain_analysis'):
            df.attrs['terrain_analysis'] = stats['terrain_analysis']
        if stats.get('power_analysis'):
            df.attrs['power_analysis'] = stats['power_analysis']
        if stats.get('traffic_analysis'):
            df.attrs['traffic_analysis'] = stats['traffic_analysis']
        if stats.get('ml_features'):
            df.attrs['ml_features'] = stats['ml_features']
        
        return df
    
    @st.cache_resource(ttl=3600)  # Cache maps for 1 hour
    def create_route_map(_self, route_data_hash: str, route_data: Dict, stats: Dict) -> folium.Map:
        """Create a folium map visualization of the route using feature groups for better stability.
        Cached for performance as map generation is expensive.
        
        Args:
            route_data_hash: Hash of route data for caching
            route_data: Parsed route data
            stats: Route statistics
            
        Returns:
            Folium map object
            
        Note: Uses leading underscore on self to exclude from caching key
        """
        # Determine map center
        if stats['bounds']:
            center_lat = (stats['bounds']['north'] + stats['bounds']['south']) / 2
            center_lon = (stats['bounds']['east'] + stats['bounds']['west']) / 2
        else:
            center_lat, center_lon = 0, 0
        
        # Create map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Create feature groups for better organization and stability
        route_lines_group = folium.FeatureGroup(name="Route Lines", show=True)
        navigation_markers_group = folium.FeatureGroup(name="Navigation", show=True)
        waypoints_group = folium.FeatureGroup(name="Waypoints", show=True)
        traffic_group = folium.FeatureGroup(name="Traffic Infrastructure", show=True)
        
        # Add tracks to route lines group
        for track in route_data.get('tracks', []):
            for segment in track.get('segments', []):
                if segment:
                    coordinates = [[p['lat'], p['lon']] for p in segment]
                    folium.PolyLine(
                        coordinates,
                        color='red',
                        weight=3,
                        opacity=0.8,
                        popup=f"Track: {track['name']}"
                    ).add_to(route_lines_group)
        
        # Add routes to route lines group
        for route in route_data.get('routes', []):
            points = route.get('points', [])
            if points:
                coordinates = [[p['lat'], p['lon']] for p in points]
                folium.PolyLine(
                    coordinates,
                    color='blue',
                    weight=3,
                    opacity=0.8,
                    popup=f"Route: {route['name']}"
                ).add_to(route_lines_group)
        
        # Add waypoints to waypoints group
        for waypoint in route_data.get('waypoints', []):
            folium.Marker(
                [waypoint['lat'], waypoint['lon']],
                popup=f"{waypoint['name']}: {waypoint['description'] or 'Waypoint'}",
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(waypoints_group)
        
        # Add start/end markers to navigation group
        for track in route_data.get('tracks', []):
            for segment in track.get('segments', []):
                if segment:
                    # Start marker
                    start_point = segment[0]
                    folium.Marker(
                        [start_point['lat'], start_point['lon']],
                        popup="Start",
                        icon=folium.Icon(color='green', icon='play')
                    ).add_to(navigation_markers_group)
                    
                    # End marker
                    end_point = segment[-1]
                    folium.Marker(
                        [end_point['lat'], end_point['lon']],
                        popup="End",
                        icon=folium.Icon(color='red', icon='stop')
                    ).add_to(navigation_markers_group)
        
        # Add traffic infrastructure to traffic group
        if stats.get('traffic_analysis', {}).get('analysis_available'):
            traffic_analysis = stats['traffic_analysis']
            
            # Add traffic light markers
            for light in traffic_analysis.get('traffic_light_locations', []):
                folium.Marker(
                    [light['route_lat'], light['route_lon']],
                    popup=f"🚦 Traffic Light (±{light['distance_m']:.0f}m)",
                    icon=folium.Icon(color='orange', icon='exclamation-sign')
                ).add_to(traffic_group)
            
            # Add major road crossing markers
            for crossing in traffic_analysis.get('major_crossing_locations', []):
                folium.Marker(
                    [crossing['route_lat'], crossing['route_lon']],
                    popup=f"🛣️ {crossing['road_name']} ({crossing['highway_type']})",
                    icon=folium.Icon(color='purple', icon='road')
                ).add_to(traffic_group)
        
        # Add all feature groups to map in batch
        route_lines_group.add_to(m)
        navigation_markers_group.add_to(m)
        waypoints_group.add_to(m)
        traffic_group.add_to(m)
        
        # Fit map to bounds
        if stats['bounds']:
            sw = [stats['bounds']['south'], stats['bounds']['west']]
            ne = [stats['bounds']['north'], stats['bounds']['east']]
            m.fit_bounds([sw, ne])
        
        return m
    
    def save_route(self, route_data: Dict, stats: Dict, user_id: str = None, filename: str = None) -> str:
        """Save processed route data using storage manager.
        
        Args:
            route_data: Parsed route data
            stats: Route statistics
            user_id: User ID for user-specific storage (None for anonymous)
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Filename of saved route (for reference)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            route_name = route_data.get('metadata', {}).get('name', 'route')
            # Clean route name for filename
            route_name = ''.join(c for c in route_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            route_name = route_name.replace(' ', '_')
            filename = f"{timestamp}_{route_name}.json"
        
        save_data = {
            'route_data': route_data,
            'statistics': stats,
            'processed_at': datetime.now().isoformat(),
            'processor_version': '1.0',
            'user_id': user_id  # Store user association
        }
        
        # Use storage manager to save data
        success = self.storage_manager.save_data(save_data, user_id, 'routes', filename)
        
        if success:
            return filename
        else:
            raise Exception(f"Failed to save route: {filename}")
    
    def load_saved_routes(self, user_id: str = None) -> List[Dict]:
        """Load saved routes for a user using storage manager.
        
        Args:
            user_id: User ID to load routes for (None for anonymous/legacy routes)
        
        Returns:
            List of saved route information
        """
        saved_routes = []
        
        try:
            # Get routes from storage manager
            files = self.storage_manager.list_user_data(user_id, 'routes') if user_id else self._load_legacy_routes()
            
            for file_info in files:
                try:
                    # Load route data to get metadata
                    route_data = self.storage_manager.load_data(user_id, 'routes', file_info['filename'])
                    
                    if route_data:
                        route_info = {
                            'filename': file_info['filename'],
                            'name': route_data.get('route_data', {}).get('metadata', {}).get('name', 'Unnamed Route'),
                            'processed_at': route_data.get('processed_at', file_info.get('last_modified')),
                            'distance_km': route_data.get('statistics', {}).get('total_distance_km', 0),
                            'elevation_gain_m': route_data.get('statistics', {}).get('total_elevation_gain_m', 0),
                            'user_id': route_data.get('user_id', user_id),
                            'backend': file_info.get('backend', 'unknown')
                        }
                        saved_routes.append(route_info)
                
                except Exception as e:
                    print(f"Error loading route {file_info['filename']}: {e}")
            
            # Sort by processed_at date (newest first)
            saved_routes.sort(key=lambda x: x.get('processed_at', ''), reverse=True)
            
        except Exception as e:
            print(f"Error loading saved routes: {e}")
        
        return saved_routes
    
    def _load_legacy_routes(self) -> List[Dict]:
        """Load legacy routes from local storage for backward compatibility."""
        files = []
        
        if not os.path.exists(self.data_dir):
            return files
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    stat = os.stat(filepath)
                    files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size_bytes': stat.st_size,
                        'size_mb': round(stat.st_size / (1024 * 1024), 2),
                        'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'backend': 'local_legacy'
                    })
                except Exception as e:
                    print(f"Error checking legacy file {filename}: {e}")
        
        return files
    
    def load_route_data(self, filename: str, user_id: str = None) -> Dict:
        """Load a specific saved route data using storage manager.
        
        Args:
            filename: Name of the route file
            user_id: User ID (None for legacy routes)
            
        Returns:
            Saved route data dictionary
        """
        # Try loading from storage manager first
        route_data = self.storage_manager.load_data(user_id, 'routes', filename)
        
        # Fallback to legacy local file if not found and no user_id specified
        if route_data is None and user_id is None:
            legacy_path = os.path.join(self.data_dir, filename)
            if os.path.exists(legacy_path):
                with open(legacy_path, 'r', encoding='utf-8') as f:
                    route_data = json.load(f)
        
        return route_data