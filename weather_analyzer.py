"""
Weather analysis module for KOMpass.
Provides weather forecasting and analysis for cycling routes.
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math
from math import radians, cos, sin, atan2, degrees


class WeatherAnalyzer:
    """Handles weather analysis for cycling routes using free weather APIs."""
    
    def __init__(self):
        """Initialize the weather analyzer."""
        # Using Open-Meteo API - completely free, no API key required
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.request_timeout = 10
    
    def get_weather_forecast(self, lat: float, lon: float, 
                           start_time: datetime, duration_hours: float) -> Dict:
        """
        Get weather forecast for a specific location and time period.
        
        Args:
            lat: Latitude
            lon: Longitude  
            start_time: Departure time
            duration_hours: Estimated ride duration in hours
            
        Returns:
            Weather forecast data
        """
        try:
            # Calculate end time
            end_time = start_time + timedelta(hours=duration_hours)
            
            # Format dates for API (ISO format)
            start_date = start_time.strftime("%Y-%m-%d")
            end_date = end_time.strftime("%Y-%m-%d")
            
            # Parameters for Open-Meteo API
            params = {
                'latitude': lat,
                'longitude': lon,
                'hourly': [
                    'temperature_2m',
                    'relative_humidity_2m', 
                    'precipitation_probability',
                    'precipitation',
                    'wind_speed_10m',
                    'wind_direction_10m',
                    'uv_index',
                    'apparent_temperature'
                ],
                'start_date': start_date,
                'end_date': end_date,
                'timezone': 'auto',
                'wind_speed_unit': 'kmh',
                'temperature_unit': 'celsius'
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {
                'error': f'Weather API request failed: {str(e)}',
                'available': False
            }
        except Exception as e:
            return {
                'error': f'Weather processing error: {str(e)}',
                'available': False
            }
    
    def calculate_route_timing(self, route_points: List[Dict], 
                             departure_time: datetime, 
                             estimated_duration_hours: float = 2.0) -> List[Dict]:
        """
        Calculate timing along the route using estimated duration.
        
        Args:
            route_points: List of route points with lat/lon
            departure_time: Planned departure time
            estimated_duration_hours: Estimated total ride duration
            
        Returns:
            List of points with estimated arrival times
        """
        if not route_points:
            return []
        
        timed_points = []
        total_points = len(route_points)
        
        for i, point in enumerate(route_points):
            # Calculate time progression as fraction of total route
            time_fraction = i / max(total_points - 1, 1)
            time_offset_hours = time_fraction * estimated_duration_hours
            
            estimated_time = departure_time + timedelta(hours=time_offset_hours)
            
            timed_points.append({
                'lat': point['lat'],
                'lon': point['lon'],
                'elevation': point.get('elevation'),
                'point_index': i,
                'estimated_time': estimated_time,
                'time_offset_hours': time_offset_hours,
                'time_offset_minutes': time_offset_hours * 60
            })
        
        return timed_points
    
    def analyze_wind_conditions(self, route_points: List[Dict], 
                              weather_data: Dict, start_time: datetime) -> Dict:
        """
        Analyze wind conditions along the route.
        
        Args:
            route_points: Timed route points
            weather_data: Weather forecast data
            start_time: Departure time
            
        Returns:
            Wind analysis results
        """
        if 'error' in weather_data or not route_points:
            return {
                'analysis_available': False,
                'reason': weather_data.get('error', 'No route data')
            }
        
        try:
            hourly_data = weather_data.get('hourly', {})
            times = hourly_data.get('time', [])
            wind_speeds = hourly_data.get('wind_speed_10m', [])
            wind_directions = hourly_data.get('wind_direction_10m', [])
            
            if not times or not wind_speeds or not wind_directions:
                return {'analysis_available': False, 'reason': 'Incomplete wind data'}
            
            wind_analysis = []
            route_bearings = self._calculate_route_bearings(route_points)
            
            for i, point in enumerate(route_points):
                # Find the corresponding weather data for this time
                point_time = start_time + timedelta(hours=point.get('time_offset_hours', point.get('estimated_time_offset_hours', 0)))
                
                # Find closest weather hour
                closest_weather_idx = self._find_closest_time_index(times, point_time)
                
                if closest_weather_idx is not None:
                    wind_speed_kmh = wind_speeds[closest_weather_idx]
                    wind_direction_deg = wind_directions[closest_weather_idx]
                    
                    # Calculate headwind/tailwind component
                    if i < len(route_bearings):
                        route_bearing = route_bearings[i]
                        wind_effect = self._calculate_wind_effect(
                            wind_direction_deg, wind_speed_kmh, route_bearing
                        )
                    else:
                        wind_effect = {'headwind_component': 0, 'crosswind_component': 0}
                    
                    wind_analysis.append({
                        'point_index': i,
                        'time': point_time.isoformat(),
                        'wind_speed_kmh': wind_speed_kmh,
                        'wind_direction_deg': wind_direction_deg,
                        'route_bearing_deg': route_bearings[i] if i < len(route_bearings) else None,
                        'headwind_component_kmh': wind_effect['headwind_component'],
                        'crosswind_component_kmh': wind_effect['crosswind_component'],
                        'wind_category': self._categorize_wind_effect(wind_effect['headwind_component'])
                    })
            
            # Calculate summary statistics
            if wind_analysis:
                headwinds = [w['headwind_component_kmh'] for w in wind_analysis]
                avg_headwind = sum(headwinds) / len(headwinds)
                max_headwind = max(headwinds)
                min_headwind = min(headwinds)  # Negative values are tailwinds
                
                # Count wind conditions
                strong_headwind_count = sum(1 for h in headwinds if h > 15)
                tailwind_count = sum(1 for h in headwinds if h < -5)
                
                return {
                    'analysis_available': True,
                    'avg_headwind_component_kmh': round(avg_headwind, 1),
                    'max_headwind_kmh': round(max_headwind, 1),
                    'max_tailwind_kmh': round(abs(min_headwind), 1) if min_headwind < 0 else 0,
                    'strong_headwind_sections': strong_headwind_count,
                    'tailwind_sections': tailwind_count,
                    'total_points_analyzed': len(wind_analysis),
                    'wind_impact_summary': self._summarize_wind_impact(headwinds),
                    'detailed_analysis': wind_analysis
                }
            else:
                return {'analysis_available': False, 'reason': 'No wind data points found'}
                
        except Exception as e:
            return {
                'analysis_available': False,
                'reason': f'Wind analysis error: {str(e)}'
            }
    
    def analyze_precipitation(self, route_points: List[Dict], 
                           weather_data: Dict, start_time: datetime) -> Dict:
        """
        Analyze precipitation conditions along the route.
        
        Args:
            route_points: Timed route points
            weather_data: Weather forecast data  
            start_time: Departure time
            
        Returns:
            Precipitation analysis results
        """
        if 'error' in weather_data or not route_points:
            return {
                'analysis_available': False,
                'reason': weather_data.get('error', 'No route data')
            }
        
        try:
            hourly_data = weather_data.get('hourly', {})
            times = hourly_data.get('time', [])
            precip_probability = hourly_data.get('precipitation_probability', [])
            precip_amount = hourly_data.get('precipitation', [])
            
            if not times or not precip_probability:
                return {'analysis_available': False, 'reason': 'No precipitation data'}
            
            rain_analysis = []
            max_rain_prob = 0
            total_expected_rain = 0
            rain_periods = 0
            
            for point in route_points:
                point_time = start_time + timedelta(hours=point.get('time_offset_hours', point.get('estimated_time_offset_hours', 0)))
                closest_idx = self._find_closest_time_index(times, point_time)
                
                if closest_idx is not None:
                    rain_prob = precip_probability[closest_idx]
                    rain_amount = precip_amount[closest_idx] if precip_amount else 0
                    
                    max_rain_prob = max(max_rain_prob, rain_prob)
                    total_expected_rain += rain_amount
                    
                    if rain_prob > 30:  # 30% threshold for likely rain
                        rain_periods += 1
                    
                    rain_analysis.append({
                        'point_index': point['point_index'],
                        'time': point_time.isoformat(),
                        'precipitation_probability': rain_prob,
                        'precipitation_amount_mm': rain_amount,
                        'rain_risk_level': self._categorize_rain_risk(rain_prob)
                    })
            
            return {
                'analysis_available': True,
                'max_precipitation_probability': max_rain_prob,
                'expected_total_precipitation_mm': round(total_expected_rain, 1),
                'high_rain_risk_periods': rain_periods,
                'rain_risk_summary': self._summarize_rain_risk(max_rain_prob, rain_periods, len(route_points)),
                'detailed_analysis': rain_analysis
            }
            
        except Exception as e:
            return {
                'analysis_available': False,
                'reason': f'Precipitation analysis error: {str(e)}'
            }
    
    def analyze_temperature_conditions(self, route_points: List[Dict],
                                     weather_data: Dict, start_time: datetime) -> Dict:
        """
        Analyze temperature and heat conditions along the route.
        
        Args:
            route_points: Timed route points
            weather_data: Weather forecast data
            start_time: Departure time
            
        Returns:
            Temperature analysis results
        """
        if 'error' in weather_data or not route_points:
            return {
                'analysis_available': False,
                'reason': weather_data.get('error', 'No route data')
            }
        
        try:
            hourly_data = weather_data.get('hourly', {})
            times = hourly_data.get('time', [])
            temperatures = hourly_data.get('temperature_2m', [])
            apparent_temps = hourly_data.get('apparent_temperature', [])
            humidity = hourly_data.get('relative_humidity_2m', [])
            uv_index = hourly_data.get('uv_index', [])
            
            if not times or not temperatures:
                return {'analysis_available': False, 'reason': 'No temperature data'}
            
            temp_analysis = []
            temps_list = []
            apparent_temps_list = []
            high_heat_periods = 0
            
            for point in route_points:
                point_time = start_time + timedelta(hours=point.get('time_offset_hours', point.get('estimated_time_offset_hours', 0)))
                closest_idx = self._find_closest_time_index(times, point_time)
                
                if closest_idx is not None:
                    temp = temperatures[closest_idx]
                    apparent_temp = apparent_temps[closest_idx] if apparent_temps else temp
                    humid = humidity[closest_idx] if humidity else 50
                    uv = uv_index[closest_idx] if uv_index else 0
                    
                    temps_list.append(temp)
                    apparent_temps_list.append(apparent_temp)
                    
                    # Check for high heat conditions
                    if apparent_temp > 30:  # Above 30°C apparent temperature
                        high_heat_periods += 1
                    
                    temp_analysis.append({
                        'point_index': point['point_index'],
                        'time': point_time.isoformat(),
                        'temperature_c': temp,
                        'apparent_temperature_c': apparent_temp,
                        'humidity_percent': humid,
                        'uv_index': uv,
                        'heat_stress_level': self._categorize_heat_stress(apparent_temp, humid),
                        'sun_exposure_risk': self._categorize_uv_risk(uv)
                    })
            
            if temps_list:
                min_temp = min(temps_list)
                max_temp = max(temps_list)
                avg_temp = sum(temps_list) / len(temps_list)
                temp_range = max_temp - min_temp
                
                return {
                    'analysis_available': True,
                    'min_temperature_c': round(min_temp, 1),
                    'max_temperature_c': round(max_temp, 1),
                    'avg_temperature_c': round(avg_temp, 1),
                    'temperature_range_c': round(temp_range, 1),
                    'max_apparent_temperature_c': round(max(apparent_temps_list), 1) if apparent_temps_list else None,
                    'high_heat_periods': high_heat_periods,
                    'heat_stress_summary': self._summarize_heat_conditions(max_temp, high_heat_periods),
                    'detailed_analysis': temp_analysis
                }
            else:
                return {'analysis_available': False, 'reason': 'No temperature data points'}
                
        except Exception as e:
            return {
                'analysis_available': False,
                'reason': f'Temperature analysis error: {str(e)}'
            }
    
    def get_comprehensive_weather_analysis(self, route_points: List[Dict],
                                         start_time: datetime,
                                         estimated_duration_hours: float = 2.0) -> Dict:
        """
        Get comprehensive weather analysis for the entire route.
        
        Args:
            route_points: List of route points
            start_time: Planned departure time
            estimated_duration_hours: Estimated ride duration
            
        Returns:
            Complete weather analysis
        """
        if not route_points:
            return {'analysis_available': False, 'reason': 'No route data'}
        
        # Calculate timing along route
        timed_points = self.calculate_route_timing(route_points, start_time, estimated_duration_hours)
        
        if not timed_points:
            return {'analysis_available': False, 'reason': 'Unable to calculate route timing'}
        
        # Use route center for weather forecast
        center_lat = sum(p['lat'] for p in route_points) / len(route_points)
        center_lon = sum(p['lon'] for p in route_points) / len(route_points)
        
        # Get weather forecast
        weather_data = self.get_weather_forecast(
            center_lat, center_lon, start_time, estimated_duration_hours + 1
        )
        
        if 'error' in weather_data:
            return {
                'analysis_available': False,
                'reason': weather_data['error']
            }
        
        # Perform individual analyses
        wind_analysis = self.analyze_wind_conditions(timed_points, weather_data, start_time)
        rain_analysis = self.analyze_precipitation(timed_points, weather_data, start_time)
        temp_analysis = self.analyze_temperature_conditions(timed_points, weather_data, start_time)
        
        # Generate weather recommendations
        recommendations = self._generate_weather_recommendations(
            wind_analysis, rain_analysis, temp_analysis
        )
        
        return {
            'analysis_available': True,
            'departure_time': start_time.isoformat(),
            'estimated_duration_hours': round(estimated_duration_hours, 2),
            'route_center': {'lat': center_lat, 'lon': center_lon},
            'wind_analysis': wind_analysis,
            'precipitation_analysis': rain_analysis,
            'temperature_analysis': temp_analysis,
            'recommendations': recommendations
        }
    
    # Helper methods
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return c * 6371  # Earth's radius in km
    
    def _calculate_route_bearings(self, route_points: List[Dict]) -> List[float]:
        """Calculate bearing between consecutive route points."""
        bearings = []
        
        for i in range(len(route_points) - 1):
            p1 = route_points[i]
            p2 = route_points[i + 1]
            
            lat1, lon1 = radians(p1['lat']), radians(p1['lon'])
            lat2, lon2 = radians(p2['lat']), radians(p2['lon'])
            
            dlon = lon2 - lon1
            y = sin(dlon) * cos(lat2)
            x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
            
            bearing = atan2(y, x)
            bearing = degrees(bearing)
            bearing = (bearing + 360) % 360
            
            bearings.append(bearing)
        
        # Add last bearing for final point
        if bearings:
            bearings.append(bearings[-1])
        
        return bearings
    
    def _calculate_wind_effect(self, wind_direction: float, wind_speed: float, 
                              route_bearing: float) -> Dict:
        """Calculate headwind and crosswind components."""
        # Convert angles to radians
        wind_rad = radians(wind_direction)
        route_rad = radians(route_bearing)
        
        # Calculate relative wind angle (wind direction - route bearing)
        relative_angle = wind_direction - route_bearing
        relative_angle = (relative_angle + 180) % 360 - 180  # Normalize to [-180, 180]
        
        # Calculate wind components
        headwind_component = wind_speed * cos(radians(relative_angle))
        crosswind_component = wind_speed * sin(radians(relative_angle))
        
        return {
            'headwind_component': round(headwind_component, 1),
            'crosswind_component': round(abs(crosswind_component), 1)
        }
    
    def _find_closest_time_index(self, times: List[str], target_time: datetime) -> Optional[int]:
        """Find the index of the closest time in the weather data."""
        try:
            target_str = target_time.strftime("%Y-%m-%dT%H:00")
            
            # Find exact match first
            if target_str in times:
                return times.index(target_str)
            
            # Find closest time
            target_hour = target_time.hour
            target_date = target_time.date()
            
            closest_idx = None
            min_diff = float('inf')
            
            for i, time_str in enumerate(times):
                try:
                    time_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    if time_obj.date() == target_date:
                        hour_diff = abs(time_obj.hour - target_hour)
                        if hour_diff < min_diff:
                            min_diff = hour_diff
                            closest_idx = i
                except Exception:
                    continue
            
            return closest_idx
            
        except Exception:
            return None
    
    def _categorize_wind_effect(self, headwind_component: float) -> str:
        """Categorize wind effect on cycling."""
        if headwind_component > 20:
            return "Strong Headwind"
        elif headwind_component > 10:
            return "Moderate Headwind"
        elif headwind_component > 0:
            return "Light Headwind"
        elif headwind_component > -10:
            return "Light Tailwind"
        elif headwind_component > -20:
            return "Moderate Tailwind"
        else:
            return "Strong Tailwind"
    
    def _categorize_rain_risk(self, probability: float) -> str:
        """Categorize rain risk level."""
        if probability >= 70:
            return "High Risk"
        elif probability >= 40:
            return "Moderate Risk"
        elif probability >= 20:
            return "Low Risk"
        else:
            return "Very Low Risk"
    
    def _categorize_heat_stress(self, apparent_temp: float, humidity: float) -> str:
        """Categorize heat stress level."""
        if apparent_temp > 35:
            return "Extreme Heat"
        elif apparent_temp > 30:
            return "High Heat"
        elif apparent_temp > 25:
            return "Moderate Heat"
        else:
            return "Comfortable"
    
    def _categorize_uv_risk(self, uv_index: float) -> str:
        """Categorize UV exposure risk."""
        if uv_index >= 8:
            return "Very High"
        elif uv_index >= 6:
            return "High"
        elif uv_index >= 3:
            return "Moderate"
        else:
            return "Low"
    
    def _summarize_wind_impact(self, headwinds: List[float]) -> str:
        """Generate wind impact summary."""
        avg_headwind = sum(headwinds) / len(headwinds)
        
        if avg_headwind > 15:
            return "Expect significant headwinds throughout the ride"
        elif avg_headwind > 5:
            return "Moderate headwinds expected for most of the ride"
        elif avg_headwind > -5:
            return "Variable wind conditions, minimal overall impact"
        else:
            return "Favorable tailwinds expected for most of the ride"
    
    def _summarize_rain_risk(self, max_prob: float, rain_periods: int, total_points: int) -> str:
        """Generate rain risk summary."""
        rain_percentage = (rain_periods / total_points) * 100 if total_points > 0 else 0
        
        if max_prob >= 70:
            return f"High chance of rain ({max_prob}% max probability)"
        elif rain_percentage > 50:
            return f"Rain likely for {rain_percentage:.0f}% of the ride"
        elif max_prob >= 30:
            return f"Some chance of rain (up to {max_prob}% probability)"
        else:
            return "Low chance of rain throughout the ride"
    
    def _summarize_heat_conditions(self, max_temp: float, heat_periods: int) -> str:
        """Generate heat condition summary."""
        if max_temp > 35:
            return f"Extreme heat expected ({max_temp}°C max), high risk of heat stress"
        elif max_temp > 30:
            return f"High temperatures expected ({max_temp}°C max), monitor hydration"
        elif max_temp > 25:
            return f"Warm conditions ({max_temp}°C max), ensure adequate hydration"
        else:
            return f"Comfortable temperatures ({max_temp}°C max)"
    
    def _generate_weather_recommendations(self, wind_analysis: Dict, 
                                        rain_analysis: Dict, 
                                        temp_analysis: Dict) -> List[str]:
        """Generate practical weather recommendations."""
        recommendations = []
        
        # Wind recommendations
        if wind_analysis.get('analysis_available'):
            avg_headwind = wind_analysis.get('avg_headwind_component_kmh', 0)
            if avg_headwind > 15:
                recommendations.append("🌪️ Strong headwinds expected - consider postponing or choosing an alternate route")
            elif avg_headwind > 8:
                recommendations.append("💨 Moderate headwinds - allow extra time and energy for the ride")
        
        # Rain recommendations  
        if rain_analysis.get('analysis_available'):
            max_rain_prob = rain_analysis.get('max_precipitation_probability', 0)
            if max_rain_prob > 70:
                recommendations.append("🌧️ High chance of rain - bring waterproof gear and consider postponing")
            elif max_rain_prob > 40:
                recommendations.append("☔ Moderate chance of rain - pack rain jacket and be prepared for wet conditions")
        
        # Temperature recommendations
        if temp_analysis.get('analysis_available'):
            max_temp = temp_analysis.get('max_temperature_c', 20)
            heat_periods = temp_analysis.get('high_heat_periods', 0)
            
            if max_temp > 35:
                recommendations.append("🥵 Extreme heat warning - consider early morning start, extra water, electrolytes")
            elif max_temp > 30:
                recommendations.append("🌡️ High temperatures - ensure extra hydration and consider sun protection")
            elif heat_periods > 0:
                recommendations.append("☀️ Hot periods expected - plan rest stops and carry extra water")
        
        if not recommendations:
            recommendations.append("✅ Good weather conditions expected for cycling")
        
        return recommendations
    
