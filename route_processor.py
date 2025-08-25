"""
Route processing module for KOMpass.
Handles GPX file parsing, route analysis, and data persistence.
"""

import gpxpy
import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import folium
from math import radians, cos, sin, asin, sqrt


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in kilometers.
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


class RouteProcessor:
    """Handles route file processing and analysis."""
    
    def __init__(self, data_dir: str = "saved_routes"):
        """Initialize the route processor.
        
        Args:
            data_dir: Directory to save processed route data
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def parse_gpx_file(self, gpx_content: str) -> Dict:
        """Parse GPX file content and extract route data.
        
        Args:
            gpx_content: String content of the GPX file
            
        Returns:
            Dictionary containing parsed route data
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
    
    def calculate_route_statistics(self, route_data: Dict) -> Dict:
        """Calculate basic statistics for the route.
        
        Args:
            route_data: Parsed route data dictionary
            
        Returns:
            Dictionary containing route statistics
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
        
        # Calculate distance and elevation statistics
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
        
        return stats
    
    def create_route_map(self, route_data: Dict, stats: Dict) -> folium.Map:
        """Create a folium map visualization of the route.
        
        Args:
            route_data: Parsed route data
            stats: Route statistics
            
        Returns:
            Folium map object
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