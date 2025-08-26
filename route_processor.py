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
try:
    from fitparse import FitFile
    FIT_SUPPORT = True
except ImportError:
    FIT_SUPPORT = False

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
            data_dir: Directory to save processed route data
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
        
        # Overpass API configuration for OpenStreetMap queries
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self.request_delay = 1.0  # Seconds between API requests to be respectful
    
    def _analyze_gradients(self, points: List[Dict]) -> Dict:
        """Analyze gradient characteristics of the route."""
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
    
    def _analyze_climbs(self, points: List[Dict]) -> Dict:
        """Analyze climbing segments and characteristics."""
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
                        current_climb['difficulty_score'] = self._calculate_climb_difficulty(current_climb)
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
    
    def _analyze_route_complexity(self, points: List[Dict]) -> Dict:
        """Analyze route complexity based on direction changes and curvature."""
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
    
    def _classify_terrain_type(self, gradient_analysis: Dict) -> Dict:
        """Classify terrain type based on gradient characteristics for ML features."""
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
        traffic_light_threshold = 0.025  # Reduced from 50m to 25m for better accuracy
        
        for route_point in route_points:
            for light in traffic_lights:
                distance = haversine_distance(
                    route_point['lat'], route_point['lon'],
                    light['lat'], light['lon']
                )
                
                # If within 25 meters, consider it a potential stop
                if distance <= traffic_light_threshold:
                    nearby_traffic_lights.append({
                        'route_point_index': route_points.index(route_point),
                        'route_lat': route_point['lat'],
                        'route_lon': route_point['lon'],
                        'light_lat': light['lat'],
                        'light_lon': light['lon'],
                        'distance_m': distance * 1000,
                        'tags': light.get('tags', {})
                    })
        
        # Find major road crossings - reduce threshold and be more selective
        major_road_crossings = []
        crossing_threshold = 0.015  # Reduced from 20m to 15m
        
        for road in major_roads:
            road_geometry = road.get('geometry', [])
            highway_type = road.get('highway_type', 'unknown')
            
            # Only consider major roads that typically require stops
            if highway_type not in ['motorway', 'trunk', 'primary', 'secondary']:
                continue
            
            for route_point in route_points:
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
                            'route_point_index': route_points.index(route_point),
                            'route_lat': route_point['lat'],
                            'route_lon': route_point['lon'],
                            'road_name': road.get('name', 'Unnamed Road'),
                            'highway_type': road.get('highway_type', 'unknown'),
                            'distance_to_road_m': distance_to_road * 1000
                        })
                        break  # Only count once per road
        
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
    
    def _remove_duplicate_stops(self, stops: List[Dict], threshold_m: float = 50) -> List[Dict]:
        """Remove duplicate stops that are within threshold distance of each other."""
        if not stops:
            return []
        
        unique_stops = []
        threshold_km = threshold_m / 1000
        
        for stop in stops:
            is_duplicate = False
            
            for unique_stop in unique_stops:
                distance = haversine_distance(
                    stop['route_lat'], stop['route_lon'],
                    unique_stop['route_lat'], unique_stop['route_lon']
                )
                
                if distance <= threshold_km:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_stops.append(stop)
        
        return unique_stops
    
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
            
            return route_data
            
        except Exception as e:
            raise ValueError(f"Error parsing GPX file: {str(e)}")
    
    def parse_fit_file(self, fit_content: bytes) -> Dict:
        """Parse FIT file content and extract route data.
        
        Args:
            fit_content: Bytes content of the FIT file
            
        Returns:
            Dictionary containing parsed route data
        """
        if not FIT_SUPPORT:
            raise ValueError("FIT file support not available. Please install fitparse library.")
        
        try:
            # Create a temporary file to parse
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.fit') as tmp_file:
                tmp_file.write(fit_content)
                tmp_file.flush()
                
                fitfile = FitFile(tmp_file.name)
                
                route_data = {
                    'metadata': {},
                    'tracks': [],
                    'routes': [],
                    'waypoints': []
                }
                
                points = []
                track_name = "FIT Activity"
                
                # Process record messages (GPS points)
                for record in fitfile.get_messages('record'):
                    lat = None
                    lon = None
                    elevation = None
                    timestamp = None
                    
                    for field in record:
                        if field.name == 'position_lat':
                            lat = field.value * (180.0 / 2**31) if field.value else None
                        elif field.name == 'position_long':
                            lon = field.value * (180.0 / 2**31) if field.value else None
                        elif field.name == 'altitude':
                            elevation = field.value
                        elif field.name == 'timestamp':
                            timestamp = field.value
                    
                    # Only add points with valid GPS coordinates
                    if lat is not None and lon is not None:
                        point_data = {
                            'lat': lat,
                            'lon': lon,
                            'elevation': elevation,
                            'time': timestamp.isoformat() if timestamp else None
                        }
                        points.append(point_data)
                
                # Get activity info if available
                for file_id in fitfile.get_messages('file_id'):
                    for field in file_id:
                        if field.name == 'time_created':
                            route_data['metadata']['time'] = field.value.isoformat() if field.value else None
                
                # Get session info for metadata
                for session in fitfile.get_messages('session'):
                    for field in session:
                        if field.name == 'start_time':
                            route_data['metadata']['start_time'] = field.value.isoformat() if field.value else None
                        elif field.name == 'sport':
                            route_data['metadata']['sport'] = field.value
                
                # Add points as a track
                if points:
                    track_data = {
                        'name': track_name,
                        'segments': [points]
                    }
                    route_data['tracks'].append(track_data)
                    route_data['metadata']['name'] = track_name
                    route_data['metadata']['description'] = f"FIT file with {len(points)} GPS points"
                
                # Clean up temp file
                os.unlink(tmp_file.name)
                
                return route_data
                
        except Exception as e:
            raise ValueError(f"Error parsing FIT file: {str(e)}")
    
    def parse_route_file(self, file_content: bytes, filename: str) -> Dict:
        """Parse route file content (GPX or FIT) and extract route data.
        
        Args:
            file_content: File content as bytes
            filename: Original filename to determine file type
            
        Returns:
            Dictionary containing parsed route data
        """
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'gpx':
            try:
                gpx_content = file_content.decode('utf-8')
                return self.parse_gpx_file(gpx_content)
            except UnicodeDecodeError:
                raise ValueError("Invalid GPX file: Unable to decode as UTF-8")
        
        elif file_extension == 'fit':
            return self.parse_fit_file(file_content)
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}. Supported types: GPX, FIT")
    
    @st.cache_data(ttl=3600)  # Cache route statistics for 1 hour
    def calculate_route_statistics(_self, route_data: Dict) -> Dict:
        """Calculate comprehensive statistics for the route including ML-ready features.
        
        Args:
            route_data: Parsed route data dictionary
            
        Returns:
            Dictionary containing route statistics and advanced metrics
            
        Note: Uses leading underscore on self to exclude from caching key
        """
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
            return stats
        
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
        
        if elevations:
            stats['max_elevation_m'] = max(elevations)
            stats['min_elevation_m'] = min(elevations)
            
            # Calculate elevation gain/loss
            for i in range(1, len(elevations)):
                diff = elevations[i] - elevations[i-1]
                if diff > 0:
                    stats['total_elevation_gain_m'] += diff
                else:
                    stats['total_elevation_loss_m'] += abs(diff)
        
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
        
        # Advanced ML-ready metrics
        if len(all_points) >= 2:
            # Gradient analysis
            gradient_analysis = _self._analyze_gradients(all_points)
            stats['gradient_analysis'] = gradient_analysis
            
            # Climbing analysis
            climb_analysis = _self._analyze_climbs(all_points)
            stats['climb_analysis'] = climb_analysis
            
            # Route complexity analysis
            complexity_analysis = _self._analyze_route_complexity(all_points)
            stats['complexity_analysis'] = complexity_analysis
            
            # Terrain classification for ML features
            terrain_analysis = _self._classify_terrain_type(gradient_analysis)
            stats['terrain_analysis'] = terrain_analysis
            
            # Power requirements analysis for ML features
            power_analysis = _self._estimate_power_requirements(gradient_analysis, total_distance)
            stats['power_analysis'] = power_analysis
            
            # Traffic stop analysis
            traffic_analysis = _self._analyze_traffic_stops(all_points, stats)
            stats['traffic_analysis'] = traffic_analysis
            
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
            
            # Add traffic-related ML features
            if traffic_analysis.get('analysis_available'):
                ml_features.update({
                    'stop_density_per_km': traffic_analysis.get('stop_density_per_km', 0),
                    'estimated_stop_time_penalty_min': traffic_analysis.get('estimated_time_penalty_minutes', 0),
                    'traffic_complexity_factor': round(
                        traffic_analysis.get('stop_density_per_km', 0) * 0.1 + 
                        (traffic_analysis.get('traffic_lights_detected', 0) * 0.02), 3
                    )
                })
            
            stats['ml_features'] = ml_features
        
        return stats
    
    @st.cache_resource(ttl=3600)  # Cache maps for 1 hour
    def create_route_map(_self, route_data: Dict, stats: Dict) -> folium.Map:
        """Create a folium map visualization of the route.
        
        Args:
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
        
        # Add tracks
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
                    ).add_to(m)
        
        # Add routes
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
                ).add_to(m)
        
        # Add waypoints
        for waypoint in route_data.get('waypoints', []):
            folium.Marker(
                [waypoint['lat'], waypoint['lon']],
                popup=f"{waypoint['name']}: {waypoint['description'] or 'Waypoint'}",
                icon=folium.Icon(color='green', icon='info-sign')
            ).add_to(m)
        
        # Add start/end markers for tracks
        for track in route_data.get('tracks', []):
            for segment in track.get('segments', []):
                if segment:
                    # Start marker
                    start_point = segment[0]
                    folium.Marker(
                        [start_point['lat'], start_point['lon']],
                        popup="Start",
                        icon=folium.Icon(color='green', icon='play')
                    ).add_to(m)
                    
                    # End marker
                    end_point = segment[-1]
                    folium.Marker(
                        [end_point['lat'], end_point['lon']],
                        popup="End",
                        icon=folium.Icon(color='red', icon='stop')
                    ).add_to(m)
        
        # Add traffic infrastructure markers if available
        if stats.get('traffic_analysis', {}).get('analysis_available'):
            traffic_analysis = stats['traffic_analysis']
            
            # Add traffic light markers
            for light in traffic_analysis.get('traffic_light_locations', []):
                folium.Marker(
                    [light['route_lat'], light['route_lon']],
                    popup=f"🚦 Traffic Light (±{light['distance_m']:.0f}m)",
                    icon=folium.Icon(color='orange', icon='exclamation-sign')
                ).add_to(m)
            
            # Add major road crossing markers
            for crossing in traffic_analysis.get('major_crossing_locations', []):
                folium.Marker(
                    [crossing['route_lat'], crossing['route_lon']],
                    popup=f"🛣️ {crossing['road_name']} ({crossing['highway_type']})",
                    icon=folium.Icon(color='purple', icon='road')
                ).add_to(m)
        
        # Fit map to bounds
        if stats['bounds']:
            sw = [stats['bounds']['south'], stats['bounds']['west']]
            ne = [stats['bounds']['north'], stats['bounds']['east']]
            m.fit_bounds([sw, ne])
        
        return m
    
    def save_route(self, route_data: Dict, stats: Dict, filename: str = None) -> str:
        """Save processed route data to file.
        
        Args:
            route_data: Parsed route data
            stats: Route statistics
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            route_name = route_data.get('metadata', {}).get('name', 'route')
            # Clean route name for filename
            route_name = ''.join(c for c in route_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            route_name = route_name.replace(' ', '_')
            filename = f"{timestamp}_{route_name}.json"
        
        filepath = os.path.join(self.data_dir, filename)
        
        save_data = {
            'route_data': route_data,
            'statistics': stats,
            'processed_at': datetime.now().isoformat(),
            'processor_version': '1.0'
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    def load_saved_routes(self) -> List[Dict]:
        """Load all saved routes from the data directory.
        
        Returns:
            List of saved route information
        """
        saved_routes = []
        
        if not os.path.exists(self.data_dir):
            return saved_routes
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    route_info = {
                        'filename': filename,
                        'filepath': filepath,
                        'name': data.get('route_data', {}).get('metadata', {}).get('name', 'Unnamed Route'),
                        'processed_at': data.get('processed_at'),
                        'distance_km': data.get('statistics', {}).get('total_distance_km', 0),
                        'elevation_gain_m': data.get('statistics', {}).get('total_elevation_gain_m', 0)
                    }
                    saved_routes.append(route_info)
                except Exception as e:
                    print(f"Error loading {filename}: {e}")
        
        # Sort by processed_at date (newest first)
        saved_routes.sort(key=lambda x: x['processed_at'], reverse=True)
        return saved_routes
    
    def load_route_data(self, filepath: str) -> Dict:
        """Load a specific saved route data file.
        
        Args:
            filepath: Path to the saved route file
            
        Returns:
            Saved route data dictionary
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)