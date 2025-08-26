"""
Unit conversion utilities for KOMpass.
Handles conversions between metric and imperial units.
"""

from typing import Union, Dict, Any


class UnitConverter:
    """Handles unit conversions between metric and imperial systems."""
    
    # Conversion factors
    KM_TO_MILES = 0.621371
    MILES_TO_KM = 1.609344
    METERS_TO_FEET = 3.28084
    FEET_TO_METERS = 0.3048
    
    @staticmethod
    def km_to_miles(km: float) -> float:
        """Convert kilometers to miles."""
        return km * UnitConverter.KM_TO_MILES if km is not None else None
    
    @staticmethod
    def miles_to_km(miles: float) -> float:
        """Convert miles to kilometers."""
        return miles * UnitConverter.MILES_TO_KM if miles is not None else None
    
    @staticmethod
    def meters_to_feet(meters: float) -> float:
        """Convert meters to feet."""
        return meters * UnitConverter.METERS_TO_FEET if meters is not None else None
    
    @staticmethod
    def feet_to_meters(feet: float) -> float:
        """Convert feet to meters."""
        return feet * UnitConverter.FEET_TO_METERS if feet is not None else None
    
    @staticmethod
    def format_distance(distance_km: float, use_imperial: bool = False) -> str:
        """Format distance with appropriate units."""
        if distance_km is None:
            return "N/A"
        
        if use_imperial:
            distance_miles = UnitConverter.km_to_miles(distance_km)
            return f"{distance_miles:.2f} mi"
        else:
            return f"{distance_km:.2f} km"
    
    @staticmethod
    def format_elevation(elevation_m: float, use_imperial: bool = False) -> str:
        """Format elevation with appropriate units."""
        if elevation_m is None:
            return "N/A"
        
        if use_imperial:
            elevation_ft = UnitConverter.meters_to_feet(elevation_m)
            return f"{elevation_ft:.0f} ft"
        else:
            return f"{elevation_m:.0f} m"
    
    @staticmethod
    def format_speed(speed_kmh: float, use_imperial: bool = False) -> str:
        """Format speed with appropriate units."""
        if speed_kmh is None:
            return "N/A"
        
        if use_imperial:
            speed_mph = UnitConverter.km_to_miles(speed_kmh)
            return f"{speed_mph:.1f} mph"
        else:
            return f"{speed_kmh:.1f} km/h"
    
    @staticmethod
    def get_distance_unit(use_imperial: bool = False) -> str:
        """Get distance unit string."""
        return "mi" if use_imperial else "km"
    
    @staticmethod
    def get_elevation_unit(use_imperial: bool = False) -> str:
        """Get elevation unit string."""
        return "ft" if use_imperial else "m"
    
    @staticmethod
    def get_speed_unit(use_imperial: bool = False) -> str:
        """Get speed unit string."""
        return "mph" if use_imperial else "km/h"
    
    @staticmethod
    def convert_route_stats(stats: Dict[str, Any], use_imperial: bool = False) -> Dict[str, Any]:
        """Convert route statistics to specified unit system.
        
        Args:
            stats: Route statistics dictionary
            use_imperial: Whether to use imperial units
            
        Returns:
            Dictionary with converted values and unit labels
        """
        if not use_imperial:
            # Return original stats with metric unit labels
            converted = stats.copy()
            converted['_units'] = {
                'distance': 'km',
                'elevation': 'm',
                'speed': 'km/h'
            }
            return converted
        
        # Convert to imperial
        converted = stats.copy()
        
        # Distance conversions
        if 'total_distance_km' in stats:
            converted['total_distance_mi'] = UnitConverter.km_to_miles(stats['total_distance_km'])
        
        # Elevation conversions
        if 'total_elevation_gain_m' in stats:
            converted['total_elevation_gain_ft'] = UnitConverter.meters_to_feet(stats['total_elevation_gain_m'])
        if 'total_elevation_loss_m' in stats:
            converted['total_elevation_loss_ft'] = UnitConverter.meters_to_feet(stats['total_elevation_loss_m'])
        if 'max_elevation_m' in stats:
            converted['max_elevation_ft'] = UnitConverter.meters_to_feet(stats['max_elevation_m'])
        if 'min_elevation_m' in stats:
            converted['min_elevation_ft'] = UnitConverter.meters_to_feet(stats['min_elevation_m'])
        
        # Convert climb analysis
        if 'climb_analysis' in stats:
            climb = stats['climb_analysis'].copy()
            if 'total_climb_distance_km' in climb:
                climb['total_climb_distance_mi'] = UnitConverter.km_to_miles(climb['total_climb_distance_km'])
            if 'average_climb_length_m' in climb:
                climb['average_climb_length_ft'] = UnitConverter.meters_to_feet(climb['average_climb_length_m'])
            if 'total_climb_elevation_m' in climb:
                climb['total_climb_elevation_ft'] = UnitConverter.meters_to_feet(climb['total_climb_elevation_m'])
            converted['climb_analysis'] = climb
        
        # Convert ML features
        if 'ml_features' in stats:
            ml = stats['ml_features'].copy()
            if 'elevation_range_m' in ml:
                ml['elevation_range_ft'] = UnitConverter.meters_to_feet(ml['elevation_range_m'])
            if 'route_density_points_per_km' in ml:
                ml['route_density_points_per_mi'] = ml['route_density_points_per_km'] / UnitConverter.KM_TO_MILES
            if 'elevation_variation_index' in ml:
                # Convert m/km to ft/mi
                ml['elevation_variation_index_ft_mi'] = UnitConverter.meters_to_feet(ml['elevation_variation_index']) / UnitConverter.KM_TO_MILES
            converted['ml_features'] = ml
        
        # Convert traffic analysis
        if 'traffic_analysis' in stats and stats['traffic_analysis'].get('analysis_available'):
            traffic = stats['traffic_analysis'].copy()
            if 'stop_density_per_km' in traffic:
                traffic['stop_density_per_mi'] = traffic['stop_density_per_km'] / UnitConverter.KM_TO_MILES
            if 'average_distance_between_stops_km' in traffic:
                traffic['average_distance_between_stops_mi'] = UnitConverter.km_to_miles(traffic['average_distance_between_stops_km'])
            converted['traffic_analysis'] = traffic
        
        # Add unit labels
        converted['_units'] = {
            'distance': 'mi',
            'elevation': 'ft',
            'speed': 'mph'
        }
        
        return converted