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
    def format_distance(distance_km: float) -> str:
        """Format distance in metric units (km)."""
        if distance_km is None:
            return "N/A"
        return f"{distance_km:.2f} km"
    
    @staticmethod
    def format_elevation(elevation_m: float) -> str:
        """Format elevation in metric units (m)."""
        if elevation_m is None:
            return "N/A"
        return f"{elevation_m:.0f} m"
    
    @staticmethod
    def format_speed(speed_kmh: float) -> str:
        """Format speed in metric units (km/h)."""
        if speed_kmh is None:
            return "N/A"
        return f"{speed_kmh:.1f} km/h"
    
    @staticmethod
    def get_distance_unit() -> str:
        """Get distance unit string (always metric)."""
        return "km"
    
    @staticmethod
    def get_elevation_unit() -> str:
        """Get elevation unit string (always metric)."""
        return "m"
    
    @staticmethod
    def get_speed_unit() -> str:
        """Get speed unit string (always metric)."""
        return "km/h"
    
    @staticmethod
    def convert_route_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
        """Return route statistics with metric unit labels.
        
        Args:
            stats: Route statistics dictionary
            
        Returns:
            Dictionary with metric unit labels (no conversion needed)
        """
        # Return original stats with metric unit labels
        converted = stats.copy()
        converted['_units'] = {
            'distance': 'km',
            'elevation': 'm',
            'speed': 'km/h'
        }
        return converted