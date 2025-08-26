"""
Rider Data Processor - Handles comprehensive Strava rider fitness data collection and analysis.

This module fetches and processes various rider metrics including:
- Power records (30s, 5min, 20min, etc.)
- Fitness trends and training load
- Heart rate zones and power zones
- Recent activity analysis
- Feature engineering for ML applications
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import time
import math
from ..config.logging_config import get_logger, log_function_entry, log_function_exit, log_error
from ..storage.storage_manager import get_storage_manager

logger = get_logger(__name__)


class RiderDataProcessor:
    """Processes comprehensive rider fitness data from Strava API."""
    
    def __init__(self, oauth_client):
        """
        Initialize rider data processor.
        
        Args:
            oauth_client: StravaOAuth instance for API calls
        """
        self.oauth_client = oauth_client
        self.storage_manager = get_storage_manager()
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_comprehensive_rider_data(_self, access_token: str) -> Dict[str, Any]:
        """
        Fetch comprehensive rider data from Strava API.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Dictionary containing all rider fitness data
        """
        log_function_entry(logger, "fetch_comprehensive_rider_data")
        
        rider_data = {
            "basic_info": None,
            "stats": None,
            "zones": None,
            "recent_activities": None,
            "fitness_metrics": None,
            "power_analysis": None,
            "training_load": None,
            "fetch_timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. Basic athlete information
            logger.info("Fetching basic athlete information")
            rider_data["basic_info"] = _self.oauth_client.get_athlete(access_token)
            
            # 2. Athlete statistics (includes power records)
            logger.info("Fetching athlete statistics and power records")
            try:
                rider_data["stats"] = _self.oauth_client.get_athlete_stats(access_token)
            except Exception as e:
                logger.warning(f"Could not fetch athlete stats: {e}")
                rider_data["stats"] = None
            
            # 3. Power and heart rate zones
            logger.info("Fetching athlete zones")
            try:
                rider_data["zones"] = _self.oauth_client.get_athlete_zones(access_token)
            except Exception as e:
                logger.warning(f"Could not fetch zones data: {e}")
                rider_data["zones"] = None
            
            # 4. Recent activities for fitness trend analysis
            logger.info("Fetching recent activities for fitness analysis")
            try:
                rider_data["recent_activities"] = _self._fetch_recent_activities_comprehensive(access_token)
            except Exception as e:
                logger.warning(f"Could not fetch recent activities: {e}")
                rider_data["recent_activities"] = []
            
            # 5. Process fitness metrics
            logger.info("Processing fitness metrics")
            rider_data["fitness_metrics"] = _self._calculate_fitness_metrics(
                rider_data["recent_activities"], 
                rider_data["zones"]
            )
            
            # 6. Advanced power analysis
            logger.info("Processing power analysis")
            rider_data["power_analysis"] = _self._analyze_power_metrics(
                rider_data["stats"], 
                rider_data["recent_activities"]
            )
            
            # 7. Training load analysis
            logger.info("Processing training load analysis")
            rider_data["training_load"] = _self._analyze_training_load(rider_data["recent_activities"])
            
            # 8. Advanced cycling metrics and power curve analysis
            logger.info("Processing advanced cycling metrics")
            rider_data["advanced_metrics"] = _self._analyze_advanced_cycling_metrics(
                access_token, rider_data["recent_activities"], rider_data["stats"], rider_data["zones"]
            )
            
            # 9. Power zone distribution analysis
            logger.info("Processing power zone analysis")
            rider_data["power_zone_analysis"] = _self._analyze_power_zones_comprehensive(
                access_token, rider_data["recent_activities"], rider_data["zones"]
            )
            
            # 10. Distance-specific performance profiling
            logger.info("Processing distance-specific performance")
            rider_data["performance_profile"] = _self._analyze_distance_specific_performance(
                rider_data["recent_activities"], rider_data["stats"]
            )
            
            logger.info("Successfully fetched comprehensive rider data")
            log_function_exit(logger, "fetch_comprehensive_rider_data", "Success")
            
            return rider_data
            
        except Exception as e:
            log_error(logger, e, "Failed to fetch comprehensive rider data")
            # Return partial data if some sections succeeded
            rider_data["error"] = str(e)
            return rider_data
    
    def _fetch_recent_activities_comprehensive(self, access_token: str, days_back: int = 90) -> List[Dict]:
        """
        Fetch recent activities with comprehensive data for analysis.
        
        Args:
            access_token: Valid Strava access token
            days_back: Number of days to look back for activities
            
        Returns:
            List of recent activities with detailed metrics
        """
        activities = []
        after_timestamp = int((datetime.now() - timedelta(days=days_back)).timestamp())
        
        try:
            # Fetch activities in batches
            page = 1
            max_pages = 5  # Limit to prevent excessive API calls
            
            while page <= max_pages:
                batch = self.oauth_client.get_athlete_activities(
                    access_token, 
                    page=page, 
                    per_page=50,  # Higher per_page for efficiency
                    after_timestamp=after_timestamp
                )
                
                if not batch:  # No more activities
                    break
                
                activities.extend(batch)
                page += 1
                
                # Rate limiting - be respectful to Strava API
                time.sleep(0.1)
                
                # If we got less than requested, we've reached the end
                if len(batch) < 50:
                    break
            
            logger.info(f"Fetched {len(activities)} activities from last {days_back} days")
            return activities
            
        except Exception as e:
            logger.error(f"Error fetching recent activities: {e}")
            return []
    
    def _calculate_fitness_metrics(self, activities: List[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Calculate fitness metrics from recent activities.
        
        Args:
            activities: List of recent activities
            zones: Athlete's power and HR zones
            
        Returns:
            Dictionary of fitness metrics
        """
        if not activities:
            return {}
        
        try:
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(activities)
            
            # Calculate basic fitness metrics
            metrics = {
                "total_activities": len(df),
                "activity_frequency": self._calculate_activity_frequency(df),
                "total_distance_km": df.get('distance', pd.Series()).sum() / 1000 if 'distance' in df.columns else 0,
                "total_elevation_gain_m": df.get('total_elevation_gain', pd.Series()).sum() if 'total_elevation_gain' in df.columns else 0,
                "average_power_watts": df.get('average_watts', pd.Series()).mean() if 'average_watts' in df.columns else None,
                "average_heartrate": df.get('average_heartrate', pd.Series()).mean() if 'average_heartrate' in df.columns else None,
                "fitness_trend": self._calculate_fitness_trend(df),
                "training_consistency": self._calculate_training_consistency(df),
                "intensity_distribution": self._calculate_intensity_distribution(df, zones)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating fitness metrics: {e}")
            return {}
    
    def _analyze_power_metrics(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze power metrics from stats and recent activities.
        
        Args:
            stats: Athlete statistics from Strava
            activities: Recent activities
            
        Returns:
            Dictionary of power analysis metrics
        """
        power_analysis = {}
        
        try:
            # Extract power records from stats
            if stats and 'all_ride_totals' in stats:
                power_analysis["lifetime_stats"] = {
                    "total_rides": stats['all_ride_totals'].get('count', 0),
                    "total_distance_km": stats['all_ride_totals'].get('distance', 0) / 1000,
                    "total_elevation_gain_m": stats['all_ride_totals'].get('elevation_gain', 0),
                    "total_moving_time_hours": stats['all_ride_totals'].get('moving_time', 0) / 3600
                }
            
            # Recent power analysis from activities
            if activities:
                recent_power_data = [
                    act for act in activities 
                    if act.get('average_watts') and act.get('type') in ['Ride', 'VirtualRide']
                ]
                
                if recent_power_data:
                    power_df = pd.DataFrame(recent_power_data)
                    
                    power_analysis["recent_power_metrics"] = {
                        "avg_power_last_30_days": power_df['average_watts'].mean(),
                        "max_power_last_30_days": power_df['average_watts'].max(),
                        "power_trend": self._calculate_power_trend(power_df),
                        "power_consistency": power_df['average_watts'].std(),
                        "weighted_power_avg": self._calculate_weighted_power_average(power_df)
                    }
            
            return power_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing power metrics: {e}")
            return {}
    
    def _analyze_training_load(self, activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze training load and stress metrics.
        
        Args:
            activities: Recent activities
            
        Returns:
            Dictionary of training load metrics
        """
        if not activities:
            return {}
        
        try:
            # Filter for relevant activities
            training_activities = [
                act for act in activities 
                if act.get('type') in ['Ride', 'VirtualRide', 'Run'] and act.get('moving_time', 0) > 900  # > 15 minutes
            ]
            
            df = pd.DataFrame(training_activities)
            
            if df.empty:
                return {}
            
            # Calculate training load metrics
            load_metrics = {
                "weekly_training_hours": self._calculate_weekly_training_hours(df),
                "training_intensity_factor": self._calculate_training_intensity(df),
                "recovery_metrics": self._calculate_recovery_metrics(df),
                "training_stress_balance": self._calculate_training_stress_balance(df),
                "peak_training_period": self._identify_peak_training_period(df)
            }
            
            return load_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing training load: {e}")
            return {}
    
    def _analyze_advanced_cycling_metrics(self, access_token: str, activities: List[Dict], stats: Optional[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Analyze advanced cycling metrics including critical power curve, VO2 max estimation, etc.
        
        Args:
            access_token: Valid Strava access token for detailed data fetching
            activities: Recent activities list
            stats: Athlete statistics
            zones: Power and HR zones
            
        Returns:
            Dictionary of advanced cycling metrics
        """
        advanced_metrics = {}
        
        try:
            # 1. Critical Power Curve Analysis
            logger.info("Analyzing critical power curve")
            advanced_metrics["critical_power_curve"] = self._analyze_critical_power_curve(stats, activities)
            
            # 2. VO2 Max Estimation
            logger.info("Estimating VO2 max")
            advanced_metrics["vo2_max_estimation"] = self._estimate_vo2_max(stats, activities)
            
            # 3. Lactate Threshold Analysis
            logger.info("Analyzing lactate threshold")
            advanced_metrics["lactate_threshold"] = self._analyze_lactate_threshold(stats, zones)
            
            # 4. Power Profile Classification
            logger.info("Classifying power profile")
            advanced_metrics["power_profile"] = self._classify_power_profile(stats)
            
            # 5. Aerobic Efficiency Analysis
            logger.info("Analyzing aerobic efficiency")
            advanced_metrics["aerobic_efficiency"] = self._analyze_aerobic_efficiency(activities)
            
            # 6. Anaerobic Capacity Analysis  
            logger.info("Analyzing anaerobic capacity")
            advanced_metrics["anaerobic_capacity"] = self._analyze_anaerobic_capacity(stats, activities)
            
            # 7. Fatigue Resistance
            logger.info("Analyzing fatigue resistance")
            advanced_metrics["fatigue_resistance"] = self._analyze_fatigue_resistance(activities)
            
            # 8. Training Stress Score Analysis
            logger.info("Analyzing training stress")
            advanced_metrics["training_stress"] = self._analyze_training_stress_comprehensive(activities, zones)
            
            return advanced_metrics
            
        except Exception as e:
            logger.error(f"Error analyzing advanced cycling metrics: {e}")
            return {}
    
    def _analyze_critical_power_curve(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze critical power curve for different durations (1min, 5min, 20min, 1hr).
        This is essential for predicting performance at different intensities.
        """
        cp_curve = {}
        
        try:
            if stats:
                # Extract power records from stats
                power_records = {}
                
                # Strava provides power records in recent_ride_totals and all_ride_totals
                for totals_key in ['recent_ride_totals', 'all_ride_totals']:
                    if totals_key in stats:
                        totals = stats[totals_key]
                        
                        # Map Strava power record fields to standard durations
                        duration_mapping = {
                            'pr_date': 'peak_power_date',
                            'max_watts': 'peak_power'
                        }
                        
                        for strava_key, our_key in duration_mapping.items():
                            if strava_key in totals:
                                power_records[our_key] = totals[strava_key]
                
                cp_curve["power_records"] = power_records
            
            # Calculate power-to-weight ratios if weight is available
            if stats and stats.get('athlete', {}).get('weight'):
                weight = stats['athlete']['weight']
                cp_curve["power_to_weight_ratios"] = {}
                
                for duration, power in cp_curve.get("power_records", {}).items():
                    if isinstance(power, (int, float)) and power > 0:
                        cp_curve["power_to_weight_ratios"][f"{duration}_w_per_kg"] = round(power / weight, 2)
            
            # Estimate Critical Power (CP) and W' (anaerobic work capacity)
            cp_curve.update(self._estimate_critical_power_model(cp_curve.get("power_records", {})))
            
            # Performance classification based on power curve
            cp_curve["performance_classification"] = self._classify_performance_level(cp_curve)
            
            return cp_curve
            
        except Exception as e:
            logger.error(f"Error analyzing critical power curve: {e}")
            return {}
    
    def _classify_performance_level(self, cp_curve: Dict[str, Any]) -> str:
        """Classify overall performance level based on power curve data."""
        try:
            power_to_weight_ratios = cp_curve.get("power_to_weight_ratios", {})
            
            if not power_to_weight_ratios:
                return "Insufficient data for classification"
            
            # Use peak power-to-weight ratio for classification
            max_ratio = 0
            for key, ratio in power_to_weight_ratios.items():
                if isinstance(ratio, (int, float)):
                    max_ratio = max(max_ratio, ratio)
            
            if max_ratio >= 6.0:
                return "Elite/Professional Level"
            elif max_ratio >= 5.0:
                return "Competitive Racer"
            elif max_ratio >= 4.0:
                return "Strong Club Rider"
            elif max_ratio >= 3.0:
                return "Recreational Cyclist"
            else:
                return "Fitness Cyclist"
                
        except Exception as e:
            logger.error(f"Error classifying performance level: {e}")
            return "Classification unavailable"
    
    def _estimate_critical_power_model(self, power_records: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate Critical Power (CP) and W' using available power records.
        Critical Power is the theoretical power that can be sustained indefinitely.
        W' is the anaerobic work capacity above CP.
        """
        cp_model = {}
        
        try:
            # We need at least 2 power records for modeling
            duration_powers = []
            
            # Map common duration records to seconds
            duration_mapping = {
                'peak_power': 5,  # Assume peak power is ~5 second sprint
                'max_watts': 300,  # Assume max watts is around 5 minutes
            }
            
            for record_type, duration_seconds in duration_mapping.items():
                if record_type in power_records and isinstance(power_records[record_type], (int, float)):
                    duration_powers.append((duration_seconds, power_records[record_type]))
            
            if len(duration_powers) >= 2:
                # Sort by duration
                duration_powers.sort()
                
                # Simple 2-parameter model: Power = CP + W'/t
                # Where t is time in seconds, CP is critical power, W' is anaerobic work capacity
                
                # Use the longest duration as approximation of CP
                longest_duration, longest_power = duration_powers[-1]
                
                # Estimate CP as 95% of longest sustainable power
                estimated_cp = longest_power * 0.95
                
                # Estimate W' from shorter durations
                estimated_w_prime = 0
                if len(duration_powers) > 1:
                    short_duration, short_power = duration_powers[0]
                    estimated_w_prime = (short_power - estimated_cp) * short_duration
                
                cp_model.update({
                    "critical_power_watts": round(estimated_cp, 1),
                    "w_prime_joules": round(estimated_w_prime, 0),
                    "cp_model_confidence": "low" if len(duration_powers) < 3 else "medium",
                    "model_note": "Estimated from available power records - more data needed for accuracy"
                })
            
            return cp_model
            
        except Exception as e:
            logger.error(f"Error estimating critical power model: {e}")
            return {}
    
    def _estimate_vo2_max(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Estimate VO2 max using power data and established formulas.
        VO2 max is crucial for endurance performance prediction.
        """
        vo2_estimation = {}
        
        try:
            # Method 1: Using peak power (if available)
            if stats:
                peak_power = None
                weight = None
                
                # Extract peak power from stats
                for totals_key in ['recent_ride_totals', 'all_ride_totals']:
                    if totals_key in stats and 'max_watts' in stats[totals_key]:
                        peak_power = stats[totals_key]['max_watts']
                        break
                
                # Get athlete weight
                if 'athlete' in stats and 'weight' in stats['athlete']:
                    weight = stats['athlete']['weight']
                
                if peak_power and weight:
                    # Hawley & Noakes formula: VO2max (ml/kg/min) = 10.8 * Power/Weight + 7
                    vo2_max_hawley = 10.8 * (peak_power / weight) + 7
                    
                    # Coggan formula for 5-min power: VO2max ≈ 10.8 * (5-min power / weight) + 7
                    # Assuming max_watts is roughly 5-min power
                    vo2_max_coggan = 10.8 * (peak_power * 0.9 / weight) + 7  # Adjust for 5-min vs peak
                    
                    vo2_estimation.update({
                        "vo2_max_hawley_formula": round(vo2_max_hawley, 1),
                        "vo2_max_coggan_formula": round(vo2_max_coggan, 1),
                        "vo2_max_average": round((vo2_max_hawley + vo2_max_coggan) / 2, 1),
                        "peak_power_used": peak_power,
                        "weight_used": weight,
                        "power_to_weight": round(peak_power / weight, 2)
                    })
                    
                    # Classify VO2 max level
                    avg_vo2 = (vo2_max_hawley + vo2_max_coggan) / 2
                    vo2_estimation["vo2_classification"] = self._classify_vo2_max(avg_vo2)
            
            # Method 2: Estimate from sustained power efforts in activities
            if activities:
                sustained_efforts = self._extract_sustained_efforts(activities)
                if sustained_efforts:
                    vo2_estimation["sustained_effort_analysis"] = sustained_efforts
            
            return vo2_estimation
            
        except Exception as e:
            logger.error(f"Error estimating VO2 max: {e}")
            return {}
    
    def _classify_vo2_max(self, vo2_max: float) -> str:
        """Classify VO2 max level for male cyclists (adjust ranges as needed)."""
        if vo2_max >= 70:
            return "Exceptional (Elite/Pro level)"
        elif vo2_max >= 60:
            return "Excellent (Competitive cyclist)"
        elif vo2_max >= 50:
            return "Good (Recreational racer)"
        elif vo2_max >= 40:
            return "Fair (Fitness cyclist)"
        else:
            return "Below average"
    
    def _analyze_lactate_threshold(self, stats: Optional[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Analyze lactate threshold (LT) and functional threshold power (FTP).
        Critical for zone-specific speed prediction.
        """
        lt_analysis = {}
        
        try:
            # Extract FTP from athlete data or zones
            ftp = None
            
            if stats and 'athlete' in stats:
                ftp = stats['athlete'].get('ftp')
            
            if not ftp and zones:
                # Try to extract FTP from power zones
                if 'power' in zones and zones['power']:
                    power_zones = zones['power']
                    # FTP is typically the boundary between zone 3 and zone 4
                    if len(power_zones) >= 4:
                        ftp = power_zones[3].get('min', 0)  # Zone 4 minimum
            
            if ftp:
                lt_analysis.update({
                    "ftp_watts": ftp,
                    "lactate_threshold_power": ftp,  # FTP approximates LT
                })
                
                # Calculate power zone boundaries based on FTP
                if ftp > 0:
                    lt_analysis["power_zone_boundaries"] = {
                        "active_recovery": round(ftp * 0.55, 0),  # < 55% FTP
                        "endurance": round(ftp * 0.75, 0),        # 56-75% FTP  
                        "tempo": round(ftp * 0.90, 0),            # 76-90% FTP
                        "lactate_threshold": round(ftp * 1.05, 0), # 91-105% FTP
                        "vo2_max": round(ftp * 1.20, 0),          # 106-120% FTP
                        "anaerobic": round(ftp * 1.50, 0),        # 121-150% FTP
                        "neuromuscular": round(ftp * 2.00, 0),    # > 150% FTP
                    }
                    
                    # Calculate expected speeds at different power zones (this is what Logan needs!)
                    lt_analysis["zone_speed_estimates"] = self._estimate_zone_speeds(ftp)
            
            # FTP trend analysis if we had historical data
            lt_analysis["ftp_trend"] = {
                "note": "FTP trend analysis requires historical FTP data",
                "current_ftp": ftp,
                "ftp_per_kg": None  # Will calculate if weight available
            }
            
            return lt_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing lactate threshold: {e}")
            return {}
    
    def _estimate_zone_speeds(self, ftp: float) -> Dict[str, Dict[str, float]]:
        """
        Estimate riding speeds at different power zones.
        This is the key functionality Logan requested for predicting ride times.
        """
        zone_speeds = {}
        
        try:
            # These are rough estimates - would need calibration with actual rider data
            # Assumptions: Average cyclist, road bike, flat terrain, no wind
            
            # Power to speed conversion (very rough estimates)
            # Based on typical power-speed relationships for road cycling
            
            zones = {
                "zone1_recovery": ftp * 0.55,
                "zone2_endurance": ftp * 0.75, 
                "zone3_tempo": ftp * 0.90,
                "zone4_threshold": ftp * 1.00,
                "zone5_vo2max": ftp * 1.15,
                "zone6_anaerobic": ftp * 1.35
            }
            
            for zone_name, power in zones.items():
                # Rough power-to-speed conversion (needs calibration with real data)
                # Based on: Speed ≈ (Power / drag_coefficient)^(1/3)
                # These are estimates for average conditions
                
                if power > 0:
                    # Very rough speed estimates (km/h) - these need real-world calibration
                    estimated_speed_kmh = 15 + (power - 100) * 0.05  # Crude linear approximation
                    estimated_speed_kmh = max(estimated_speed_kmh, 15)  # Minimum 15 km/h
                    estimated_speed_kmh = min(estimated_speed_kmh, 55)  # Maximum 55 km/h
                    
                    zone_speeds[zone_name] = {
                        "power_watts": round(power, 0),
                        "estimated_speed_kmh": round(estimated_speed_kmh, 1),
                        "estimated_speed_mph": round(estimated_speed_kmh * 0.621371, 1),
                        "note": "Estimates for flat terrain, no wind - needs calibration"
                    }
            
            return zone_speeds
            
        except Exception as e:
            logger.error(f"Error estimating zone speeds: {e}")
            return {}
    
    def _classify_power_profile(self, stats: Optional[Dict]) -> Dict[str, Any]:
        """
        Classify rider's power profile (sprinter, climber, time trialist, all-rounder).
        """
        profile = {}
        
        try:
            if not stats:
                return {"classification": "Unknown", "reason": "No power data available"}
            
            # Extract different duration powers
            power_records = {}
            
            for totals_key in ['recent_ride_totals', 'all_ride_totals']:
                if totals_key in stats:
                    totals = stats[totals_key]
                    if 'max_watts' in totals:
                        power_records['max_power'] = totals['max_watts']
            
            # Get FTP if available
            ftp = None
            if 'athlete' in stats:
                ftp = stats['athlete'].get('ftp')
            
            if power_records and ftp:
                max_power = power_records.get('max_power', 0)
                
                # Calculate power ratios
                sprint_to_ftp = max_power / ftp if ftp > 0 else 0
                
                # Classify based on power profile
                if sprint_to_ftp > 2.5:
                    classification = "Sprinter"
                    strengths = ["High peak power", "Short explosive efforts"]
                elif sprint_to_ftp > 2.0:
                    classification = "Pursuit/Time Trialist"  
                    strengths = ["High sustained power", "Good power endurance"]
                elif sprint_to_ftp > 1.8:
                    classification = "All-rounder"
                    strengths = ["Balanced power profile", "Versatile across disciplines"]
                else:
                    classification = "Climber/Endurance"
                    strengths = ["Power endurance", "Sustained efforts"]
                
                profile.update({
                    "classification": classification,
                    "strengths": strengths,
                    "sprint_to_ftp_ratio": round(sprint_to_ftp, 2),
                    "max_power": max_power,
                    "ftp": ftp,
                    "confidence": "medium"
                })
            
            return profile
            
        except Exception as e:
            logger.error(f"Error classifying power profile: {e}")
            return {}
    
    def _analyze_aerobic_efficiency(self, activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze aerobic efficiency (power per heart rate).
        """
        efficiency = {}
        
        try:
            power_hr_data = []
            
            for activity in activities[-30:]:  # Last 30 activities
                if (activity.get('average_watts') and 
                    activity.get('average_heartrate') and
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    power_hr_ratio = activity['average_watts'] / activity['average_heartrate']
                    power_hr_data.append({
                        'date': activity.get('start_date_local'),
                        'power_hr_ratio': power_hr_ratio,
                        'power': activity['average_watts'],
                        'hr': activity['average_heartrate']
                    })
            
            if power_hr_data:
                df = pd.DataFrame(power_hr_data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                efficiency.update({
                    "avg_power_hr_ratio": round(df['power_hr_ratio'].mean(), 2),
                    "efficiency_trend": self._calculate_efficiency_trend(df),
                    "recent_efficiency": round(df.tail(10)['power_hr_ratio'].mean(), 2),
                    "efficiency_consistency": round(df['power_hr_ratio'].std(), 2),
                    "sample_size": len(df)
                })
            
            return efficiency
            
        except Exception as e:
            logger.error(f"Error analyzing aerobic efficiency: {e}")
            return {}
    
    def _calculate_efficiency_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate trend in aerobic efficiency over time."""
        if len(df) < 5:
            return {}
        
        # Simple trend analysis
        recent_avg = df.tail(10)['power_hr_ratio'].mean()
        older_avg = df.head(10)['power_hr_ratio'].mean()
        
        trend_direction = "improving" if recent_avg > older_avg else "declining"
        trend_magnitude = abs(recent_avg - older_avg) / older_avg if older_avg > 0 else 0
        
        return {
            "trend_direction": trend_direction,
            "trend_magnitude": round(trend_magnitude * 100, 1),  # As percentage
            "recent_avg": round(recent_avg, 2),
            "older_avg": round(older_avg, 2)
        }
    
    def _analyze_anaerobic_capacity(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze anaerobic capacity and short-duration power capabilities.
        """
        anaerobic = {}
        
        try:
            # Extract peak power capabilities
            if stats:
                peak_power = None
                for totals_key in ['recent_ride_totals', 'all_ride_totals']:
                    if totals_key in stats and 'max_watts' in stats[totals_key]:
                        peak_power = stats[totals_key]['max_watts']
                        break
                
                if peak_power:
                    anaerobic["peak_power_watts"] = peak_power
                    
                    # Estimate anaerobic power reserve
                    ftp = stats.get('athlete', {}).get('ftp', 0)
                    if ftp > 0:
                        anaerobic_reserve = peak_power - ftp
                        anaerobic.update({
                            "anaerobic_power_reserve": anaerobic_reserve,
                            "anaerobic_reserve_ratio": round(anaerobic_reserve / ftp, 2)
                        })
            
            # Analyze short efforts in recent activities
            short_efforts = []
            for activity in activities[-20:]:  # Last 20 activities
                if (activity.get('max_watts') and 
                    activity.get('moving_time', 0) < 3600 and  # < 1 hour activities
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    short_efforts.append({
                        'max_watts': activity['max_watts'],
                        'avg_watts': activity.get('average_watts', 0),
                        'duration': activity.get('moving_time', 0)
                    })
            
            if short_efforts:
                df_efforts = pd.DataFrame(short_efforts)
                anaerobic.update({
                    "recent_max_power_avg": round(df_efforts['max_watts'].mean(), 0),
                    "power_variability": round(df_efforts['max_watts'].std(), 0),
                    "anaerobic_consistency": self._calculate_anaerobic_consistency(df_efforts)
                })
            
            return anaerobic
            
        except Exception as e:
            logger.error(f"Error analyzing anaerobic capacity: {e}")
            return {}
    
    def _calculate_anaerobic_consistency(self, df_efforts: pd.DataFrame) -> float:
        """Calculate consistency of anaerobic efforts."""
        if len(df_efforts) < 3:
            return 0.0
        
        # Coefficient of variation (lower = more consistent)
        cv = df_efforts['max_watts'].std() / df_efforts['max_watts'].mean()
        consistency_score = max(0, 1 - cv)  # Convert to 0-1 scale
        
        return round(consistency_score, 3)
    
    def _analyze_fatigue_resistance(self, activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze fatigue resistance and power sustainability over long efforts.
        """
        fatigue_resistance = {}
        
        try:
            # Find long activities (> 1.5 hours) with power data
            long_activities = []
            for activity in activities:
                if (activity.get('moving_time', 0) > 5400 and  # > 1.5 hours
                    activity.get('average_watts') and
                    activity.get('max_watts') and
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    # Calculate power sustainability metrics
                    avg_power = activity['average_watts']
                    max_power = activity['max_watts']
                    duration_hours = activity['moving_time'] / 3600
                    
                    power_sustainability = avg_power / max_power if max_power > 0 else 0
                    
                    long_activities.append({
                        'duration_hours': duration_hours,
                        'avg_power': avg_power,
                        'max_power': max_power,
                        'power_sustainability': power_sustainability,
                        'normalized_power': avg_power / duration_hours  # Simple normalization
                    })
            
            if long_activities:
                df_long = pd.DataFrame(long_activities)
                
                fatigue_resistance.update({
                    "avg_power_sustainability": round(df_long['power_sustainability'].mean(), 3),
                    "long_ride_power_avg": round(df_long['avg_power'].mean(), 0),
                    "endurance_consistency": round(df_long['power_sustainability'].std(), 3),
                    "longest_ride_hours": round(df_long['duration_hours'].max(), 1),
                    "sample_rides": len(df_long)
                })
                
                # Classify fatigue resistance
                avg_sustainability = df_long['power_sustainability'].mean()
                if avg_sustainability > 0.8:
                    classification = "Excellent fatigue resistance"
                elif avg_sustainability > 0.7:
                    classification = "Good fatigue resistance"
                elif avg_sustainability > 0.6:
                    classification = "Moderate fatigue resistance"
                else:
                    classification = "Needs endurance development"
                
                fatigue_resistance["fatigue_resistance_classification"] = classification
            
            return fatigue_resistance
            
        except Exception as e:
            logger.error(f"Error analyzing fatigue resistance: {e}")
            return {}
    
    def _analyze_training_stress_comprehensive(self, activities: List[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Comprehensive training stress analysis including TSS estimation.
        """
        stress_analysis = {}
        
        try:
            # Extract FTP for TSS calculation
            ftp = 250  # Default FTP if not available
            if zones and 'power' in zones:
                power_zones = zones['power']
                if len(power_zones) >= 4:
                    ftp = power_zones[3].get('min', 250)
            
            stress_scores = []
            
            for activity in activities[-60:]:  # Last 60 activities
                if (activity.get('average_watts') and 
                    activity.get('moving_time') and
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    # Estimate TSS (Training Stress Score)
                    avg_power = activity['average_watts']
                    duration_hours = activity['moving_time'] / 3600
                    
                    intensity_factor = avg_power / ftp if ftp > 0 else 0
                    estimated_tss = duration_hours * 100 * (intensity_factor ** 2)
                    
                    stress_scores.append({
                        'date': activity.get('start_date_local'),
                        'tss': estimated_tss,
                        'duration_hours': duration_hours,
                        'intensity_factor': intensity_factor,
                        'avg_power': avg_power
                    })
            
            if stress_scores:
                df_stress = pd.DataFrame(stress_scores)
                df_stress['date'] = pd.to_datetime(df_stress['date'])
                df_stress = df_stress.sort_values('date')
                
                # Calculate Training Stress Balance (TSB)
                df_stress['ctl'] = df_stress['tss'].rolling(window=42, min_periods=7).mean()  # Chronic Training Load
                df_stress['atl'] = df_stress['tss'].rolling(window=7, min_periods=3).mean()   # Acute Training Load
                df_stress['tsb'] = df_stress['ctl'] - df_stress['atl']  # Training Stress Balance
                
                stress_analysis.update({
                    "avg_weekly_tss": round(df_stress['tss'].rolling(window=7).sum().mean(), 0),
                    "current_ctl": round(df_stress['ctl'].iloc[-1], 0) if len(df_stress) > 7 else 0,
                    "current_atl": round(df_stress['atl'].iloc[-1], 0) if len(df_stress) > 3 else 0,
                    "current_tsb": round(df_stress['tsb'].iloc[-1], 0) if len(df_stress) > 7 else 0,
                    "avg_intensity_factor": round(df_stress['intensity_factor'].mean(), 3),
                    "training_load_trend": self._analyze_training_load_trend(df_stress),
                    "ftp_used": ftp
                })
                
                # Interpret TSB
                current_tsb = stress_analysis.get("current_tsb", 0)
                if current_tsb > 10:
                    tsb_interpretation = "Well rested - good for hard training or racing"
                elif current_tsb > -10:
                    tsb_interpretation = "Neutral - normal training"
                elif current_tsb > -30:
                    tsb_interpretation = "Moderately fatigued - consider recovery"
                else:
                    tsb_interpretation = "Highly fatigued - rest recommended"
                
                stress_analysis["tsb_interpretation"] = tsb_interpretation
            
            return stress_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing training stress: {e}")
            return {}
    
    def _analyze_training_load_trend(self, df_stress: pd.DataFrame) -> Dict[str, Any]:
        """Analyze training load trends over time."""
        if len(df_stress) < 14:
            return {}
        
        recent_ctl = df_stress['ctl'].tail(7).mean()
        older_ctl = df_stress['ctl'].head(7).mean()
        
        trend_direction = "increasing" if recent_ctl > older_ctl else "decreasing"
        trend_magnitude = abs(recent_ctl - older_ctl) / older_ctl if older_ctl > 0 else 0
        
        return {
            "ctl_trend_direction": trend_direction,
            "ctl_trend_magnitude": round(trend_magnitude * 100, 1),
            "recent_ctl": round(recent_ctl, 0),
            "older_ctl": round(older_ctl, 0)
        }
    
    def _analyze_power_zones_comprehensive(self, access_token: str, activities: List[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Comprehensive power zone analysis including time-in-zone distribution.
        This is critical for Logan's use case of predicting speeds at different zones.
        """
        zone_analysis = {}
        
        try:
            # Extract power zones from athlete data
            power_zones = []
            if zones and 'power' in zones:
                power_zones = zones['power']
            
            zone_analysis["configured_zones"] = power_zones
            
            # Analyze time-in-zone for recent activities
            if activities and power_zones:
                zone_distribution = self._calculate_time_in_zones(activities, power_zones)
                zone_analysis["time_in_zone_analysis"] = zone_distribution
            
            # Calculate zone-specific performance metrics
            if power_zones:
                zone_performance = self._analyze_zone_specific_performance(activities, power_zones)
                zone_analysis["zone_performance_metrics"] = zone_performance
            
            # Speed predictions for each zone (Logan's key requirement)
            if power_zones:
                zone_speed_predictions = self._create_zone_speed_predictions(power_zones, activities)
                zone_analysis["zone_speed_predictions"] = zone_speed_predictions
            
            return zone_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing power zones: {e}")
            return {}
    
    def _calculate_time_in_zones(self, activities: List[Dict], power_zones: List[Dict]) -> Dict[str, Any]:
        """
        Calculate time spent in each power zone across recent activities.
        """
        zone_time_analysis = {}
        
        try:
            # Create zone boundaries
            zone_boundaries = []
            
            if not power_zones or not isinstance(power_zones, list):
                logger.warning("No valid power zones data available")
                return {"error": "No power zones configured"}
            
            for i, zone in enumerate(power_zones):
                if isinstance(zone, dict):
                    zone_boundaries.append({
                        'zone_number': i + 1,
                        'min_power': zone.get('min', 0),
                        'max_power': zone.get('max', 999999),
                        'total_time_seconds': 0,
                        'activity_count': 0
                    })
                else:
                    logger.warning(f"Invalid zone data structure: {zone}")
                    continue
            
            # Analyze activities for zone distribution
            for activity in activities[-30:]:  # Last 30 activities
                if (activity.get('average_watts') and 
                    activity.get('moving_time') and
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    avg_power = activity['average_watts']
                    duration = activity['moving_time']
                    
                    # Find which zone this activity's average power falls into
                    for zone in zone_boundaries:
                        if zone['min_power'] <= avg_power < zone['max_power']:
                            zone['total_time_seconds'] += duration
                            zone['activity_count'] += 1
                            break
            
            # Calculate percentages and summaries
            total_time = sum(zone['total_time_seconds'] for zone in zone_boundaries)
            
            for zone in zone_boundaries:
                zone['percentage_of_total_time'] = (zone['total_time_seconds'] / total_time * 100) if total_time > 0 else 0
                zone['average_session_time_minutes'] = (zone['total_time_seconds'] / zone['activity_count'] / 60) if zone['activity_count'] > 0 else 0
            
            zone_time_analysis.update({
                "zone_distribution": zone_boundaries,
                "total_analyzed_time_hours": total_time / 3600,
                "activities_analyzed": len([a for a in activities[-30:] if a.get('average_watts')]),
                "zone_balance_score": self._calculate_zone_balance_score(zone_boundaries)
            })
            
            return zone_time_analysis
            
        except Exception as e:
            logger.error(f"Error calculating time in zones: {e}")
            return {}
    
    def _calculate_zone_balance_score(self, zone_boundaries: List[Dict]) -> Dict[str, Any]:
        """Calculate how balanced the training is across zones."""
        if not zone_boundaries:
            return {}
        
        percentages = [zone['percentage_of_total_time'] for zone in zone_boundaries]
        
        # Ideal distribution (polarized training model)
        # Zone 1-2: ~80%, Zone 3-4: ~15%, Zone 5+: ~5%
        ideal_distribution = {
            1: 40, 2: 40, 3: 10, 4: 5, 5: 3, 6: 2  # Rough ideal percentages
        }
        
        balance_score = 0
        for i, zone in enumerate(zone_boundaries):
            zone_num = i + 1
            actual_pct = zone['percentage_of_total_time']
            ideal_pct = ideal_distribution.get(zone_num, 0)
            
            # Calculate deviation from ideal
            deviation = abs(actual_pct - ideal_pct)
            balance_score += max(0, 10 - deviation)  # 10 points max per zone
        
        max_possible_score = len(zone_boundaries) * 10
        normalized_score = (balance_score / max_possible_score) if max_possible_score > 0 else 0
        
        return {
            "balance_score": round(normalized_score, 3),
            "interpretation": "Excellent" if normalized_score > 0.8 else "Good" if normalized_score > 0.6 else "Needs improvement"
        }
    
    def _analyze_zone_specific_performance(self, activities: List[Dict], power_zones: List[Dict]) -> Dict[str, Any]:
        """
        Analyze performance capabilities at each power zone.
        """
        zone_performance = {}
        
        try:
            for i, zone in enumerate(power_zones):
                if not isinstance(zone, dict):
                    logger.warning(f"Invalid zone data structure: {zone}")
                    continue
                    
                zone_num = i + 1
                zone_min = zone.get('min', 0)
                zone_max = zone.get('max', 999999)
                
                # Find activities in this zone
                zone_activities = []
                for activity in activities:
                    if (activity.get('average_watts') and 
                        zone_min <= activity['average_watts'] < zone_max and
                        activity.get('type') in ['Ride', 'VirtualRide']):
                        zone_activities.append(activity)
                
                if zone_activities:
                    # Calculate zone-specific metrics
                    durations = [act['moving_time'] for act in zone_activities if act.get('moving_time')]
                    distances = [act['distance'] for act in zone_activities if act.get('distance')]
                    speeds = [act['average_speed'] for act in zone_activities if act.get('average_speed')]
                    
                    zone_performance[f"zone_{zone_num}"] = {
                        "activity_count": len(zone_activities),
                        "avg_duration_minutes": round(np.mean(durations) / 60, 1) if durations else 0,
                        "max_duration_minutes": round(max(durations) / 60, 1) if durations else 0,
                        "avg_distance_km": round(np.mean(distances) / 1000, 1) if distances else 0,
                        "avg_speed_kmh": round(np.mean(speeds) * 3.6, 1) if speeds else 0,  # Convert m/s to km/h
                        "power_range": f"{zone_min}-{zone_max}W",
                        "sustainability_rating": self._calculate_zone_sustainability(durations, zone_min)
                    }
            
            return zone_performance
            
        except Exception as e:
            logger.error(f"Error analyzing zone-specific performance: {e}")
            return {}
    
    def _calculate_zone_sustainability(self, durations: List[float], zone_power: float) -> str:
        """Calculate sustainability rating for a power zone."""
        if not durations:
            return "Unknown"
        
        max_duration_hours = max(durations) / 3600
        avg_duration_hours = np.mean(durations) / 3600
        
        # Higher power zones should have shorter sustainable durations
        if zone_power < 200:  # Lower zones
            if max_duration_hours > 4:
                return "Excellent sustainability"
            elif max_duration_hours > 2:
                return "Good sustainability"
            else:
                return "Limited sustainability"
        else:  # Higher zones
            if max_duration_hours > 1:
                return "Excellent sustainability"
            elif max_duration_hours > 0.5:
                return "Good sustainability"
            else:
                return "Sprint/Short efforts only"
    
    def _create_zone_speed_predictions(self, power_zones: List[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Create speed predictions for each power zone - Logan's key requirement!
        This enables predicting how long rides will take at different intensities.
        """
        speed_predictions = {}
        
        try:
            # Calculate baseline speed-power relationships from actual data
            speed_power_data = []
            for activity in activities:
                if (activity.get('average_watts') and 
                    activity.get('average_speed') and
                    activity.get('type') in ['Ride', 'VirtualRide'] and
                    activity.get('moving_time', 0) > 1800):  # Minimum 30 minutes for stable data
                    
                    speed_kmh = activity['average_speed'] * 3.6  # Convert m/s to km/h
                    power = activity['average_watts']
                    
                    speed_power_data.append({
                        'speed_kmh': speed_kmh,
                        'power_watts': power,
                        'duration_hours': activity['moving_time'] / 3600
                    })
            
            if speed_power_data and len(speed_power_data) >= 5:
                df_speed_power = pd.DataFrame(speed_power_data)
                
                # Create speed predictions for each zone
                for i, zone in enumerate(power_zones):
                    zone_num = i + 1
                    zone_mid_power = (zone.get('min', 0) + zone.get('max', 500)) / 2
                    
                    # Find activities near this power level for calibration
                    similar_power_activities = df_speed_power[
                        (df_speed_power['power_watts'] >= zone_mid_power * 0.9) &
                        (df_speed_power['power_watts'] <= zone_mid_power * 1.1)
                    ]
                    
                    if len(similar_power_activities) >= 3:
                        # Use actual data for prediction
                        avg_speed = similar_power_activities['speed_kmh'].mean()
                        speed_std = similar_power_activities['speed_kmh'].std()
                        confidence = "High"
                    else:
                        # Use power-speed estimation model
                        avg_speed = self._estimate_speed_from_power(zone_mid_power, df_speed_power)
                        speed_std = 2.0  # Default uncertainty
                        confidence = "Medium" if len(df_speed_power) >= 10 else "Low"
                    
                    # Calculate time predictions for common distances
                    distance_predictions = {}
                    for distance_km in [10, 20, 40, 80, 100, 160]:  # Common cycling distances
                        if avg_speed > 0:
                            time_hours = distance_km / avg_speed
                            distance_predictions[f"{distance_km}km"] = {
                                "estimated_time_hours": round(time_hours, 2),
                                "estimated_time_formatted": self._format_duration(time_hours),
                                "speed_kmh": round(avg_speed, 1)
                            }
                    
                    speed_predictions[f"zone_{zone_num}"] = {
                        "zone_name": f"Zone {zone_num}",
                        "power_range_watts": f"{zone.get('min', 0)}-{zone.get('max', 500)}",
                        "mid_power_watts": round(zone_mid_power, 0),
                        "predicted_speed_kmh": round(avg_speed, 1),
                        "speed_uncertainty_kmh": round(speed_std, 1),
                        "confidence_level": confidence,
                        "distance_time_predictions": distance_predictions,
                        "calibration_rides": len(similar_power_activities)
                    }
                
                # Overall model quality
                speed_predictions["model_info"] = {
                    "total_calibration_rides": len(df_speed_power),
                    "data_quality": "Good" if len(df_speed_power) >= 20 else "Limited",
                    "note": "Predictions assume flat terrain and calm conditions"
                }
            
            else:
                # Fallback to basic estimates
                speed_predictions = self._create_basic_zone_speed_estimates(power_zones)
                speed_predictions["model_info"] = {
                    "note": "Basic estimates - need more ride data for accurate predictions"
                }
            
            return speed_predictions
            
        except Exception as e:
            logger.error(f"Error creating zone speed predictions: {e}")
            return {}
    
    def _estimate_speed_from_power(self, power_watts: float, df_speed_power: pd.DataFrame) -> float:
        """Estimate speed from power using existing data correlation."""
        if len(df_speed_power) < 3:
            # Fallback basic estimation
            return 15 + (power_watts - 100) * 0.05
        
        # Simple linear relationship estimation
        correlation = np.corrcoef(df_speed_power['power_watts'], df_speed_power['speed_kmh'])[0, 1]
        
        if abs(correlation) > 0.3:  # Reasonable correlation
            # Linear fit
            slope = np.cov(df_speed_power['power_watts'], df_speed_power['speed_kmh'])[0, 1] / np.var(df_speed_power['power_watts'])
            intercept = df_speed_power['speed_kmh'].mean() - slope * df_speed_power['power_watts'].mean()
            
            estimated_speed = slope * power_watts + intercept
            return max(15, min(estimated_speed, 50))  # Reasonable bounds
        else:
            # Fallback to basic estimation
            return 15 + (power_watts - 100) * 0.05
    
    def _create_basic_zone_speed_estimates(self, power_zones: List[Dict]) -> Dict[str, Any]:
        """Create basic speed estimates when insufficient data available."""
        basic_estimates = {}
        
        for i, zone in enumerate(power_zones):
            if not isinstance(zone, dict):
                continue
                
            zone_num = i + 1
            zone_mid_power = (zone.get('min', 0) + zone.get('max', 500)) / 2
            
            # Very basic speed estimation (needs real-world calibration)
            estimated_speed = 15 + (zone_mid_power - 100) * 0.05
            estimated_speed = max(15, min(estimated_speed, 50))  # Reasonable bounds
            
            distance_predictions = {}
            for distance_km in [10, 20, 40, 80, 100, 160]:
                time_hours = distance_km / estimated_speed if estimated_speed > 0 else 0
                distance_predictions[f"{distance_km}km"] = {
                    "estimated_time_hours": round(time_hours, 2),
                    "estimated_time_formatted": self._format_duration(time_hours),
                    "speed_kmh": round(estimated_speed, 1)
                }
            
            basic_estimates[f"zone_{zone_num}"] = {
                "zone_name": f"Zone {zone_num}",
                "power_range_watts": f"{zone.get('min', 0)}-{zone.get('max', 500)}",
                "mid_power_watts": round(zone_mid_power, 0),
                "predicted_speed_kmh": round(estimated_speed, 1),
                "confidence_level": "Low - Basic Estimate",
                "distance_time_predictions": distance_predictions
            }
        
        return basic_estimates
    
    def _format_duration(self, hours: float) -> str:
        """Format duration in hours to HH:MM format."""
        if hours <= 0:
            return "0:00"
        
        total_minutes = int(hours * 60)
        hours_part = total_minutes // 60
        minutes_part = total_minutes % 60
        
        return f"{hours_part}:{minutes_part:02d}"
    
    def _analyze_distance_specific_performance(self, activities: List[Dict], stats: Optional[Dict]) -> Dict[str, Any]:
        """
        Analyze performance across different distance categories.
        Logan's requirement: good info for both short and long rides.
        """
        distance_performance = {}
        
        try:
            # Categorize activities by distance
            distance_categories = {
                "short_rides_under_30km": [],
                "medium_rides_30_80km": [],
                "long_rides_80_160km": [],
                "ultra_rides_over_160km": []
            }
            
            for activity in activities:
                if (activity.get('distance') and 
                    activity.get('average_watts') and
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    distance_km = activity['distance'] / 1000
                    
                    if distance_km < 30:
                        distance_categories["short_rides_under_30km"].append(activity)
                    elif distance_km < 80:
                        distance_categories["medium_rides_30_80km"].append(activity)
                    elif distance_km < 160:
                        distance_categories["long_rides_80_160km"].append(activity)
                    else:
                        distance_categories["ultra_rides_over_160km"].append(activity)
            
            # Analyze each distance category
            for category, activities_in_category in distance_categories.items():
                if activities_in_category:
                    analysis = self._analyze_distance_category(activities_in_category, category)
                    distance_performance[category] = analysis
            
            # Cross-distance performance comparison
            distance_performance["performance_comparison"] = self._compare_distance_performance(distance_categories)
            
            # Power decay analysis across distances
            distance_performance["power_decay_analysis"] = self._analyze_power_decay_by_distance(distance_categories)
            
            return distance_performance
            
        except Exception as e:
            logger.error(f"Error analyzing distance-specific performance: {e}")
            return {}
    
    def _analyze_distance_category(self, activities: List[Dict], category: str) -> Dict[str, Any]:
        """Analyze performance metrics for a specific distance category."""
        if not activities:
            return {}
        
        # Extract metrics
        powers = [act['average_watts'] for act in activities if act.get('average_watts')]
        distances = [act['distance'] / 1000 for act in activities if act.get('distance')]
        speeds = [act['average_speed'] * 3.6 for act in activities if act.get('average_speed')]  # Convert to km/h
        durations = [act['moving_time'] / 3600 for act in activities if act.get('moving_time')]  # Convert to hours
        
        analysis = {
            "activity_count": len(activities),
            "avg_power_watts": round(np.mean(powers), 0) if powers else 0,
            "max_power_watts": round(max(powers), 0) if powers else 0,
            "avg_distance_km": round(np.mean(distances), 1) if distances else 0,
            "avg_speed_kmh": round(np.mean(speeds), 1) if speeds else 0,
            "avg_duration_hours": round(np.mean(durations), 2) if durations else 0,
            "power_consistency": round(np.std(powers), 0) if len(powers) > 1 else 0
        }
        
        # Calculate efficiency metrics
        if powers and speeds:
            power_speed_ratios = [p/s for p, s in zip(powers, speeds) if s > 0]
            analysis["avg_power_per_speed"] = round(np.mean(power_speed_ratios), 1) if power_speed_ratios else 0
        
        # Distance-specific insights
        if "short" in category:
            analysis["category_focus"] = "High intensity, power development"
            analysis["typical_use"] = "Training, intervals, recovery rides"
        elif "medium" in category:
            analysis["category_focus"] = "Tempo work, endurance base"
            analysis["typical_use"] = "Weekend rides, group rides, fitness"
        elif "long" in category:
            analysis["category_focus"] = "Endurance, fat oxidation"
            analysis["typical_use"] = "Long weekend rides, base training"
        else:  # ultra
            analysis["category_focus"] = "Ultra-endurance, mental toughness"
            analysis["typical_use"] = "Events, long-distance challenges"
        
        return analysis
    
    def _compare_distance_performance(self, distance_categories: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Compare performance across different distance categories."""
        comparison = {}
        
        try:
            # Calculate average power for each category
            power_by_distance = {}
            for category, activities in distance_categories.items():
                if activities:
                    powers = [act['average_watts'] for act in activities if act.get('average_watts')]
                    power_by_distance[category] = np.mean(powers) if powers else 0
            
            # Find power decay trend
            if len(power_by_distance) >= 2:
                sorted_categories = sorted(power_by_distance.items(), key=lambda x: x[1], reverse=True)
                
                comparison["power_by_distance"] = power_by_distance
                comparison["strongest_distance"] = sorted_categories[0][0] if sorted_categories else "Unknown"
                
                # Calculate power decay rate
                if len(sorted_categories) >= 2:
                    highest_power = sorted_categories[0][1]
                    lowest_power = sorted_categories[-1][1]
                    power_decay_pct = ((highest_power - lowest_power) / highest_power * 100) if highest_power > 0 else 0
                    
                    comparison["power_decay_percentage"] = round(power_decay_pct, 1)
                    
                    # Classify endurance profile
                    if power_decay_pct < 10:
                        endurance_profile = "Excellent endurance - minimal power loss"
                    elif power_decay_pct < 20:
                        endurance_profile = "Good endurance - moderate power loss"
                    elif power_decay_pct < 35:
                        endurance_profile = "Average endurance - noticeable power loss"
                    else:
                        endurance_profile = "Limited endurance - significant power loss"
                    
                    comparison["endurance_profile"] = endurance_profile
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing distance performance: {e}")
            return {}
    
    def _analyze_power_decay_by_distance(self, distance_categories: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analyze how power decreases with increasing distance."""
        decay_analysis = {}
        
        try:
            # Collect power and distance data points
            power_distance_points = []
            
            for category, activities in distance_categories.items():
                for activity in activities:
                    if activity.get('average_watts') and activity.get('distance'):
                        power_distance_points.append({
                            'distance_km': activity['distance'] / 1000,
                            'power_watts': activity['average_watts'],
                            'duration_hours': activity.get('moving_time', 0) / 3600
                        })
            
            if len(power_distance_points) >= 5:
                df_decay = pd.DataFrame(power_distance_points)
                
                # Group by distance ranges and calculate average power
                df_decay['distance_bin'] = pd.cut(df_decay['distance_km'], 
                                                bins=[0, 30, 50, 80, 120, 200, 999],
                                                labels=['0-30km', '30-50km', '50-80km', '80-120km', '120-200km', '200km+'])
                
                decay_by_bin = df_decay.groupby('distance_bin', observed=False).agg({
                    'power_watts': ['mean', 'std', 'count'],
                    'duration_hours': 'mean'
                }).round(1)
                
                # Convert to serializable format
                decay_dict = {}
                for bin_name in decay_by_bin.index:
                    decay_dict[str(bin_name)] = {
                        'power_mean': decay_by_bin.loc[bin_name, ('power_watts', 'mean')],
                        'power_std': decay_by_bin.loc[bin_name, ('power_watts', 'std')],
                        'activity_count': decay_by_bin.loc[bin_name, ('power_watts', 'count')],
                        'avg_duration_hours': decay_by_bin.loc[bin_name, ('duration_hours', 'mean')]
                    }
                
                decay_analysis["power_by_distance_bins"] = decay_dict
                
                # Calculate power decay model
                if len(df_decay) >= 10:
                    # Simple correlation analysis
                    correlation = np.corrcoef(df_decay['distance_km'], df_decay['power_watts'])[0, 1]
                    decay_analysis["distance_power_correlation"] = round(correlation, 3)
                    
                    if correlation < -0.3:  # Significant negative correlation
                        decay_analysis["decay_pattern"] = "Clear power decay with distance"
                    elif correlation < -0.1:
                        decay_analysis["decay_pattern"] = "Moderate power decay with distance" 
                    else:
                        decay_analysis["decay_pattern"] = "No clear power decay pattern"
            
            return decay_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing power decay: {e}")
            return {}
    
    def _extract_sustained_efforts(self, activities: List[Dict]) -> Dict[str, Any]:
        """Extract sustained effort analysis from activities."""
        sustained_efforts = {}
        
        try:
            # Find activities with sustained high power
            high_power_activities = []
            for activity in activities:
                if (activity.get('average_watts') and 
                    activity.get('moving_time', 0) > 1200 and  # > 20 minutes
                    activity.get('type') in ['Ride', 'VirtualRide']):
                    
                    avg_power = activity['average_watts']
                    duration_minutes = activity['moving_time'] / 60
                    
                    # Consider "sustained" if average power is relatively high for the duration
                    power_per_minute = avg_power / duration_minutes * 60  # Normalize
                    
                    high_power_activities.append({
                        'avg_power': avg_power,
                        'duration_minutes': duration_minutes,
                        'power_per_minute': power_per_minute,
                        'date': activity.get('start_date_local')
                    })
            
            if high_power_activities:
                df_sustained = pd.DataFrame(high_power_activities)
                
                sustained_efforts.update({
                    "avg_sustained_power": round(df_sustained['avg_power'].mean(), 0),
                    "max_sustained_power": round(df_sustained['avg_power'].max(), 0),
                    "avg_sustained_duration": round(df_sustained['duration_minutes'].mean(), 1),
                    "sustained_effort_count": len(df_sustained),
                    "power_endurance_score": round(df_sustained['power_per_minute'].mean(), 1)
                })
            
            return sustained_efforts
            
        except Exception as e:
            logger.error(f"Error extracting sustained efforts: {e}")
            return {}
    
    def _calculate_activity_frequency(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate activity frequency metrics."""
        if df.empty:
            return {}
        
        # Convert start_date to datetime
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        
        # Calculate frequency
        days_span = (df['start_date'].max() - df['start_date'].min()).days
        if days_span == 0:
            days_span = 1
        
        return {
            "activities_per_week": len(df) * 7 / days_span,
            "riding_days_per_week": df.groupby(df['start_date'].dt.date).size().count() * 7 / days_span
        }
    
    def _calculate_fitness_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate fitness trend over time."""
        if df.empty or 'start_date_local' not in df.columns:
            return {}
        
        try:
            df['start_date'] = pd.to_datetime(df['start_date_local'])
            df = df.sort_values('start_date')
            
            # Calculate 7-day rolling averages
            if 'average_watts' in df.columns:
                df['power_7day_avg'] = df['average_watts'].rolling(window=7, min_periods=1).mean()
            
            # Calculate trend direction
            recent_period = df.tail(14)  # Last 2 weeks
            older_period = df.head(14)   # First 2 weeks
            
            trend = {}
            if 'average_watts' in df.columns and len(recent_period) > 0 and len(older_period) > 0:
                recent_avg = recent_period['average_watts'].mean()
                older_avg = older_period['average_watts'].mean()
                trend['power_trend_direction'] = 'improving' if recent_avg > older_avg else 'declining'
                trend['power_trend_magnitude'] = abs(recent_avg - older_avg) / older_avg if older_avg > 0 else 0
            
            return trend
            
        except Exception as e:
            logger.error(f"Error calculating fitness trend: {e}")
            return {}
    
    def _calculate_training_consistency(self, df: pd.DataFrame) -> float:
        """Calculate training consistency score."""
        if df.empty or 'start_date_local' not in df.columns:
            return 0.0
        
        try:
            df['start_date'] = pd.to_datetime(df['start_date_local'])
            
            # Calculate days between activities
            df_sorted = df.sort_values('start_date')
            gaps = df_sorted['start_date'].diff().dt.days.dropna()
            
            if len(gaps) == 0:
                return 1.0
            
            # Consistency is inverse of gap variance (lower variance = more consistent)
            gap_variance = gaps.var()
            consistency_score = 1.0 / (1.0 + gap_variance / 10)  # Normalize
            
            return min(max(consistency_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating training consistency: {e}")
            return 0.0
    
    def _calculate_intensity_distribution(self, df: pd.DataFrame, zones: Optional[Dict]) -> Dict[str, Any]:
        """Calculate training intensity distribution."""
        if df.empty:
            return {}
        
        # Simple intensity classification based on effort
        intensity_dist = {}
        
        if 'average_heartrate' in df.columns:
            hr_data = df['average_heartrate'].dropna()
            if len(hr_data) > 0:
                intensity_dist['avg_heart_rate'] = hr_data.mean()
                intensity_dist['hr_distribution'] = {
                    'easy': len(hr_data[hr_data < hr_data.quantile(0.6)]) / len(hr_data),
                    'moderate': len(hr_data[(hr_data >= hr_data.quantile(0.6)) & (hr_data < hr_data.quantile(0.85))]) / len(hr_data),
                    'hard': len(hr_data[hr_data >= hr_data.quantile(0.85)]) / len(hr_data)
                }
        
        return intensity_dist
    
    def _calculate_power_trend(self, power_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate power trend over recent activities."""
        if power_df.empty:
            return {}
        
        power_df['start_date'] = pd.to_datetime(power_df['start_date_local'])
        power_df = power_df.sort_values('start_date')
        
        # Calculate moving average
        power_df['power_ma'] = power_df['average_watts'].rolling(window=5, min_periods=1).mean()
        
        # Trend analysis
        recent_power = power_df.tail(10)['average_watts'].mean()
        older_power = power_df.head(10)['average_watts'].mean()
        
        return {
            'trend_direction': 'improving' if recent_power > older_power else 'declining',
            'trend_strength': abs(recent_power - older_power) / older_power if older_power > 0 else 0
        }
    
    def _calculate_weighted_power_average(self, power_df: pd.DataFrame) -> float:
        """Calculate weighted power average based on activity duration."""
        if power_df.empty or 'moving_time' not in power_df.columns:
            return 0.0
        
        total_weighted_power = (power_df['average_watts'] * power_df['moving_time']).sum()
        total_time = power_df['moving_time'].sum()
        
        return total_weighted_power / total_time if total_time > 0 else 0.0
    
    def _calculate_weekly_training_hours(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate weekly training hours."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        df['week'] = df['start_date'].dt.isocalendar().week
        
        weekly_hours = df.groupby('week')['moving_time'].sum() / 3600  # Convert to hours
        
        return {
            'avg_weekly_hours': weekly_hours.mean(),
            'max_weekly_hours': weekly_hours.max(),
            'current_week_hours': weekly_hours.iloc[-1] if len(weekly_hours) > 0 else 0
        }
    
    def _calculate_training_intensity(self, df: pd.DataFrame) -> float:
        """Calculate overall training intensity factor."""
        if df.empty:
            return 0.0
        
        # Simple intensity calculation based on relative effort
        if 'average_watts' in df.columns and 'moving_time' in df.columns:
            weighted_intensity = (df['average_watts'] * df['moving_time']).sum() / df['moving_time'].sum()
            return weighted_intensity / 200  # Normalize against typical threshold power
        
        return 0.0
    
    def _calculate_recovery_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate recovery-related metrics."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        df_sorted = df.sort_values('start_date')
        
        # Calculate rest days between activities
        gaps = df_sorted['start_date'].diff().dt.days.dropna()
        
        return {
            'avg_rest_days': gaps.mean() if len(gaps) > 0 else 0,
            'max_rest_period': gaps.max() if len(gaps) > 0 else 0,
            'recovery_consistency': gaps.std() if len(gaps) > 0 else 0
        }
    
    def _calculate_training_stress_balance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate training stress balance approximation."""
        if df.empty:
            return {}
        
        # Simplified TSB calculation based on activity frequency and intensity
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        
        # Recent stress (last 7 days) vs. chronic stress (last 28 days)
        now = datetime.now()
        last_7_days = df[df['start_date'] > (now - timedelta(days=7))]
        last_28_days = df[df['start_date'] > (now - timedelta(days=28))]
        
        acute_load = len(last_7_days) * 7  # Activities per week
        chronic_load = len(last_28_days) * 28 / 4  # Activities per week over 4 weeks
        
        tsb = chronic_load - acute_load if chronic_load > 0 else 0
        
        return {
            'acute_training_load': acute_load,
            'chronic_training_load': chronic_load,
            'training_stress_balance': tsb
        }
    
    def _identify_peak_training_period(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify peak training periods."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date_local'])
        df['week'] = df['start_date'].dt.isocalendar().week
        
        weekly_volume = df.groupby('week').agg({
            'moving_time': 'sum',
            'distance': 'sum'
        })
        
        if weekly_volume.empty:
            return {}
        
        peak_week = weekly_volume['moving_time'].idxmax()
        
        return {
            'peak_training_week': int(peak_week),
            'peak_weekly_hours': weekly_volume.loc[peak_week, 'moving_time'] / 3600,
            'peak_weekly_distance': weekly_volume.loc[peak_week, 'distance'] / 1000
        }
    
    def get_feature_engineering_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and engineer features for ML applications.
        Enhanced with advanced cycling metrics for performance prediction.
        
        Args:
            rider_data: Comprehensive rider data dictionary
            
        Returns:
            Dictionary of engineered features for ML
        """
        features = {}
        
        try:
            # Basic rider characteristics
            if rider_data.get("basic_info"):
                basic_info = rider_data["basic_info"]
                features.update({
                    "rider_weight_kg": basic_info.get("weight"),
                    "rider_ftp": basic_info.get("ftp"),
                    "rider_experience_years": (datetime.now().year - datetime.fromisoformat(basic_info.get("created_at", "2020-01-01T00:00:00Z").replace("Z", "+00:00")).year) if basic_info.get("created_at") else None
                })
            
            # Power-related features (enhanced)
            if rider_data.get("power_analysis"):
                power_analysis = rider_data["power_analysis"]
                features.update({
                    "recent_avg_power": power_analysis.get("recent_power_metrics", {}).get("avg_power_last_30_days"),
                    "power_consistency": power_analysis.get("recent_power_metrics", {}).get("power_consistency"),
                    "power_trend_improving": 1 if power_analysis.get("recent_power_metrics", {}).get("power_trend", {}).get("trend_direction") == "improving" else 0
                })
            
            # Advanced cycling metrics features
            if rider_data.get("advanced_metrics"):
                advanced = rider_data["advanced_metrics"]
                
                # Critical power curve features
                if advanced.get("critical_power_curve"):
                    cp_curve = advanced["critical_power_curve"]
                    features.update({
                        "critical_power_watts": cp_curve.get("critical_power_watts"),
                        "w_prime_joules": cp_curve.get("w_prime_joules"),
                        "cp_model_confidence": 1 if cp_curve.get("cp_model_confidence") == "high" else 0.5 if cp_curve.get("cp_model_confidence") == "medium" else 0
                    })
                
                # VO2 max features
                if advanced.get("vo2_max_estimation"):
                    vo2_data = advanced["vo2_max_estimation"]
                    features.update({
                        "estimated_vo2_max": vo2_data.get("vo2_max_average"),
                        "power_to_weight_ratio": vo2_data.get("power_to_weight")
                    })
                
                # Lactate threshold features  
                if advanced.get("lactate_threshold"):
                    lt_data = advanced["lactate_threshold"]
                    features.update({
                        "lactate_threshold_power": lt_data.get("lactate_threshold_power"),
                        "ftp_watts": lt_data.get("ftp_watts")
                    })
                
                # Power profile classification
                if advanced.get("power_profile"):
                    profile = advanced["power_profile"]
                    features.update({
                        "sprint_to_ftp_ratio": profile.get("sprint_to_ftp_ratio"),
                        "is_sprinter": 1 if "Sprinter" in profile.get("classification", "") else 0,
                        "is_climber": 1 if "Climber" in profile.get("classification", "") else 0,
                        "is_time_trialist": 1 if "Time Trialist" in profile.get("classification", "") else 0
                    })
                
                # Aerobic efficiency features
                if advanced.get("aerobic_efficiency"):
                    efficiency = advanced["aerobic_efficiency"]
                    features.update({
                        "power_hr_ratio": efficiency.get("avg_power_hr_ratio"),
                        "efficiency_improving": 1 if efficiency.get("efficiency_trend", {}).get("trend_direction") == "improving" else 0
                    })
                
                # Anaerobic capacity features
                if advanced.get("anaerobic_capacity"):
                    anaerobic = advanced["anaerobic_capacity"]
                    features.update({
                        "peak_power_watts": anaerobic.get("peak_power_watts"),
                        "anaerobic_power_reserve": anaerobic.get("anaerobic_power_reserve"),
                        "anaerobic_consistency": anaerobic.get("anaerobic_consistency")
                    })
                
                # Fatigue resistance features
                if advanced.get("fatigue_resistance"):
                    fatigue = advanced["fatigue_resistance"]
                    features.update({
                        "power_sustainability": fatigue.get("avg_power_sustainability"),
                        "endurance_rating": 1 if "Excellent" in fatigue.get("fatigue_resistance_classification", "") else 0.5 if "Good" in fatigue.get("fatigue_resistance_classification", "") else 0
                    })
                
                # Training stress features
                if advanced.get("training_stress"):
                    stress = advanced["training_stress"]
                    features.update({
                        "current_ctl": stress.get("current_ctl"),
                        "current_atl": stress.get("current_atl"),
                        "training_stress_balance": stress.get("current_tsb"),
                        "avg_weekly_tss": stress.get("avg_weekly_tss"),
                        "avg_intensity_factor": stress.get("avg_intensity_factor")
                    })
            
            # Power zone analysis features
            if rider_data.get("power_zone_analysis"):
                zone_analysis = rider_data["power_zone_analysis"]
                
                # Zone balance and distribution
                if zone_analysis.get("time_in_zone_analysis"):
                    zone_time = zone_analysis["time_in_zone_analysis"]
                    features.update({
                        "zone_balance_score": zone_time.get("zone_balance_score", {}).get("balance_score"),
                        "total_training_hours": zone_time.get("total_analyzed_time_hours")
                    })
                
                # Zone-specific performance  
                if zone_analysis.get("zone_performance_metrics"):
                    zone_perf = zone_analysis["zone_performance_metrics"]
                    for zone_key, zone_data in zone_perf.items():
                        if isinstance(zone_data, dict):
                            features.update({
                                f"{zone_key}_max_duration": zone_data.get("max_duration_minutes"),
                                f"{zone_key}_avg_speed": zone_data.get("avg_speed_kmh")
                            })
            
            # Distance-specific performance features  
            if rider_data.get("performance_profile"):
                distance_perf = rider_data["performance_profile"]
                
                # Extract key distance performance metrics
                for distance_category, perf_data in distance_perf.items():
                    if isinstance(perf_data, dict) and "rides" in distance_category:
                        category_short = distance_category.replace("_rides", "").replace("_", "")
                        features.update({
                            f"{category_short}_avg_power": perf_data.get("avg_power_watts"),
                            f"{category_short}_avg_speed": perf_data.get("avg_speed_kmh"),
                            f"{category_short}_activity_count": perf_data.get("activity_count")
                        })
                
                # Power decay analysis
                if distance_perf.get("performance_comparison"):
                    comparison = distance_perf["performance_comparison"]
                    features.update({
                        "power_decay_percentage": comparison.get("power_decay_percentage"),
                        "endurance_excellent": 1 if "Excellent" in comparison.get("endurance_profile", "") else 0
                    })
            
            # Fitness features (enhanced)
            if rider_data.get("fitness_metrics"):
                fitness = rider_data["fitness_metrics"]
                features.update({
                    "activity_frequency_per_week": fitness.get("activity_frequency", {}).get("activities_per_week", 0),
                    "training_consistency_score": fitness.get("training_consistency", 0),
                    "avg_heart_rate": fitness.get("intensity_distribution", {}).get("avg_heart_rate"),
                    "total_activities": fitness.get("total_activities", 0),
                    "total_distance_km": fitness.get("total_distance_km", 0)
                })
            
            # Training load features (enhanced)
            if rider_data.get("training_load"):
                load = rider_data["training_load"]
                features.update({
                    "avg_weekly_training_hours": load.get("weekly_training_hours", {}).get("avg_weekly_hours", 0),
                    "max_weekly_training_hours": load.get("weekly_training_hours", {}).get("max_weekly_hours", 0),
                    "training_intensity_factor": load.get("training_intensity_factor", 0),
                    "avg_rest_days": load.get("recovery_metrics", {}).get("avg_rest_days", 0),
                    "recovery_consistency": load.get("recovery_metrics", {}).get("recovery_consistency", 0)
                })
            
            # Calculate composite performance scores
            features.update(self._calculate_composite_performance_scores(features))
            
            logger.info(f"Engineered {len(features)} features for ML applications")
            return features
            
        except Exception as e:
            log_error(logger, e, "Error engineering features")
            return features
    
    def _calculate_composite_performance_scores(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate composite performance scores from individual features."""
        composite_scores = {}
        
        try:
            # Power Performance Score (0-100)
            power_components = []
            if features.get("recent_avg_power"):
                power_components.append(min(features["recent_avg_power"] / 300 * 50, 50))  # Normalize to 50 max
            if features.get("critical_power_watts"):
                power_components.append(min(features["critical_power_watts"] / 250 * 25, 25))  # Normalize to 25 max
            if features.get("peak_power_watts"):
                power_components.append(min(features["peak_power_watts"] / 800 * 25, 25))  # Normalize to 25 max
            
            if power_components:
                composite_scores["power_performance_score"] = round(sum(power_components), 1)
            
            # Endurance Performance Score (0-100)
            endurance_components = []
            if features.get("estimated_vo2_max"):
                endurance_components.append(min(features["estimated_vo2_max"] / 70 * 40, 40))  # Normalize to 40 max
            if features.get("power_sustainability"):
                endurance_components.append(features["power_sustainability"] * 30)  # 0-1 scale to 30 max
            if features.get("avg_weekly_training_hours"):
                endurance_components.append(min(features["avg_weekly_training_hours"] / 20 * 30, 30))  # Normalize to 30 max
            
            if endurance_components:
                composite_scores["endurance_performance_score"] = round(sum(endurance_components), 1)
            
            # Training Quality Score (0-100)
            training_components = []
            if features.get("training_consistency_score"):
                training_components.append(features["training_consistency_score"] * 40)  # 0-1 scale to 40 max
            if features.get("zone_balance_score"):
                training_components.append(features["zone_balance_score"] * 30)  # 0-1 scale to 30 max
            if features.get("activity_frequency_per_week"):
                training_components.append(min(features["activity_frequency_per_week"] / 6 * 30, 30))  # Normalize to 30 max
            
            if training_components:
                composite_scores["training_quality_score"] = round(sum(training_components), 1)
            
            # Overall Performance Index (0-100)
            overall_components = []
            for score_key in ["power_performance_score", "endurance_performance_score", "training_quality_score"]:
                if composite_scores.get(score_key):
                    overall_components.append(composite_scores[score_key])
            
            if overall_components:
                composite_scores["overall_performance_index"] = round(sum(overall_components) / len(overall_components), 1)
            
            return composite_scores
            
        except Exception as e:
            logger.error(f"Error calculating composite scores: {e}")
            return {}
    
    def validate_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and assess the completeness of rider data.
        
        Args:
            rider_data: Comprehensive rider data dictionary
            
        Returns:
            Dictionary containing validation results and data quality metrics
        """
        validation = {
            "is_valid": True,
            "completeness_score": 0.0,
            "missing_components": [],
            "data_quality": {},
            "recommendations": []
        }
        
        try:
            # Check required components
            required_components = [
                "basic_info", "stats", "zones", "recent_activities", 
                "fitness_metrics", "power_analysis", "training_load",
                "advanced_metrics", "power_zone_analysis", "performance_profile"
            ]
            
            available_components = 0
            for component in required_components:
                if rider_data.get(component):
                    available_components += 1
                else:
                    validation["missing_components"].append(component)
            
            validation["completeness_score"] = available_components / len(required_components)
            
            # Assess data quality
            if rider_data.get("recent_activities"):
                activities_count = len(rider_data["recent_activities"])
                validation["data_quality"]["activity_count"] = activities_count
                
                if activities_count < 10:
                    validation["recommendations"].append("More recent activities would improve fitness analysis accuracy")
                elif activities_count > 100:
                    validation["data_quality"]["rich_dataset"] = True
            
            # Check for power data availability
            if rider_data.get("power_analysis", {}).get("recent_power_metrics"):
                validation["data_quality"]["has_power_data"] = True
            else:
                validation["recommendations"].append("Power meter data would enable advanced performance analysis")
            
            # Check data freshness
            fetch_time = rider_data.get("fetch_timestamp")
            if fetch_time:
                from datetime import datetime
                fetch_dt = datetime.fromisoformat(fetch_time)
                age_hours = (datetime.now() - fetch_dt).total_seconds() / 3600
                validation["data_quality"]["data_age_hours"] = age_hours
                
                if age_hours > 24:
                    validation["recommendations"].append("Consider refreshing rider data for most current metrics")
            
            # Overall validation
            if validation["completeness_score"] < 0.5:
                validation["is_valid"] = False
                validation["recommendations"].append("Insufficient data for reliable analysis")
            
            logger.info(f"Rider data validation: {validation['completeness_score']:.1%} complete")
            return validation
            
        except Exception as e:
            log_error(logger, e, "Error validating rider data")
            validation["is_valid"] = False
            validation["error"] = str(e)
            return validation
    
    def remove_pii_from_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove personally identifiable information from rider data before storage.
        
        Args:
            rider_data: Complete rider data with potential PII
            
        Returns:
            Sanitized rider data with PII removed
        """
        log_function_entry(logger, "remove_pii_from_rider_data")
        
        try:
            sanitized_data = rider_data.copy()
            
            # Remove PII from basic_info
            if sanitized_data.get("basic_info"):
                basic_info = sanitized_data["basic_info"].copy()
                
                # Remove direct identifiers
                pii_fields = [
                    "firstname", "lastname", "profile", "profile_medium", 
                    "city", "state", "country", "email", "premium",
                    "created_at", "updated_at", "badge_type_id", "friend", 
                    "follower", "athlete_type", "date_preference", 
                    "measurement_preference", "clubs", "bikes", "shoes"
                ]
                
                for field in pii_fields:
                    basic_info.pop(field, None)
                
                # Keep only relevant fitness data
                allowed_fields = ["id", "sex", "weight", "ftp"]
                sanitized_basic_info = {k: v for k, v in basic_info.items() if k in allowed_fields}
                
                # Hash the user ID for anonymization but consistency
                if "id" in sanitized_basic_info:
                    import hashlib
                    user_id_hash = hashlib.sha256(str(sanitized_basic_info["id"]).encode()).hexdigest()[:16]
                    sanitized_basic_info["user_hash"] = user_id_hash
                    del sanitized_basic_info["id"]
                
                sanitized_data["basic_info"] = sanitized_basic_info
            
            # Remove PII from recent activities
            if sanitized_data.get("recent_activities"):
                sanitized_activities = []
                for activity in sanitized_data["recent_activities"]:
                    sanitized_activity = activity.copy()
                    
                    # Remove location and identifying info
                    pii_activity_fields = [
                        "name", "location_city", "location_state", "location_country",
                        "start_latlng", "end_latlng", "map", "photos", "gear",
                        "description", "athlete", "segment_efforts", "splits_metric",
                        "splits_standard", "laps", "gear_id", "external_id", "upload_id"
                    ]
                    
                    for field in pii_activity_fields:
                        sanitized_activity.pop(field, None)
                    
                    # Keep only performance metrics
                    allowed_activity_fields = [
                        "distance", "moving_time", "elapsed_time", "total_elevation_gain",
                        "type", "start_date", "average_speed", "max_speed", "average_cadence",
                        "average_watts", "weighted_average_watts", "kilojoules", "device_watts",
                        "has_heartrate", "average_heartrate", "max_heartrate", "pr_count",
                        "achievement_count", "kudos_count", "suffer_score", "workout_type"
                    ]
                    
                    sanitized_activity = {k: v for k, v in sanitized_activity.items() 
                                        if k in allowed_activity_fields}
                    
                    sanitized_activities.append(sanitized_activity)
                
                sanitized_data["recent_activities"] = sanitized_activities
            
            # Add anonymization metadata
            sanitized_data["anonymization"] = {
                "processed_at": datetime.now().isoformat(),
                "pii_removed": True,
                "anonymization_version": "1.0"
            }
            
            logger.info("Successfully removed PII from rider data")
            log_function_exit(logger, "remove_pii_from_rider_data", {"success": True})
            
            return sanitized_data
            
        except Exception as e:
            log_error(logger, e, "Error removing PII from rider data")
            log_function_exit(logger, "remove_pii_from_rider_data", {"success": False})
            return rider_data
    
    def save_rider_data(self, rider_data: Dict[str, Any], user_id: str) -> bool:
        """
        Save rider data to storage with PII removed.
        
        Args:
            rider_data: Complete rider data
            user_id: Strava user ID
            
        Returns:
            Success status
        """
        log_function_entry(logger, "save_rider_data", {"user_id": user_id})
        
        try:
            # Remove PII before saving
            sanitized_data = self.remove_pii_from_rider_data(rider_data)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fitness_data_{timestamp}.json"
            
            # Save to storage
            success = self.storage_manager.save_data(sanitized_data, user_id, 'fitness', filename)
            
            if success:
                logger.info(f"Successfully saved rider data for user {user_id}")
            else:
                logger.error(f"Failed to save rider data for user {user_id}")
            
            log_function_exit(logger, "save_rider_data", {"success": success})
            return success
            
        except Exception as e:
            log_error(logger, e, "Error saving rider data")
            log_function_exit(logger, "save_rider_data", {"success": False})
            return False
    
    def load_rider_data(self, user_id: str, filename: str = None) -> Optional[Dict[str, Any]]:
        """
        Load saved rider data for a user.
        
        Args:
            user_id: Strava user ID
            filename: Specific filename to load (optional, loads latest if not specified)
            
        Returns:
            Saved rider data or None if not found
        """
        log_function_entry(logger, "load_rider_data", {"user_id": user_id, "filename": filename})
        
        try:
            if filename:
                # Load specific file
                data = self.storage_manager.load_data(user_id, 'fitness', filename)
            else:
                # Load most recent fitness data
                files = self.storage_manager.list_user_data(user_id, 'fitness')
                if not files:
                    log_function_exit(logger, "load_rider_data", {"success": False, "reason": "no_files"})
                    return None
                
                # Sort by timestamp and get most recent
                files.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
                latest_file = files[0]
                data = self.storage_manager.load_data(user_id, 'fitness', latest_file['filename'])
            
            if data:
                logger.info(f"Successfully loaded rider data for user {user_id}")
                log_function_exit(logger, "load_rider_data", {"success": True})
            else:
                logger.warning(f"No rider data found for user {user_id}")
                log_function_exit(logger, "load_rider_data", {"success": False, "reason": "not_found"})
            
            return data
            
        except Exception as e:
            log_error(logger, e, "Error loading rider data")
            log_function_exit(logger, "load_rider_data", {"success": False})
            return None
    
    def get_rider_data_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of all saved rider data for a user.
        
        Args:
            user_id: Strava user ID
            
        Returns:
            List of available rider data files with metadata
        """
        log_function_entry(logger, "get_rider_data_history", {"user_id": user_id})
        
        try:
            files = self.storage_manager.list_user_data(user_id, 'fitness')
            
            history = []
            for file_info in files:
                try:
                    # Load metadata from each file
                    data = self.storage_manager.load_data(user_id, 'fitness', file_info['filename'])
                    if data:
                        history_item = {
                            'filename': file_info['filename'],
                            'saved_at': data.get('fetch_timestamp', file_info.get('last_modified')),
                            'anonymized': data.get('anonymization', {}).get('pii_removed', False),
                            'size_mb': file_info.get('size_mb', 0),
                            'activity_count': len(data.get('recent_activities', [])),
                            'has_power_data': bool(data.get('power_analysis', {}).get('recent_power_metrics')),
                            'completeness_score': self._quick_completeness_check(data)
                        }
                        history.append(history_item)
                except Exception as e:
                    logger.warning(f"Error loading metadata for {file_info['filename']}: {e}")
            
            # Sort by save date (newest first)
            history.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
            
            logger.info(f"Retrieved {len(history)} rider data files for user {user_id}")
            log_function_exit(logger, "get_rider_data_history", {"success": True, "count": len(history)})
            
            return history
            
        except Exception as e:
            log_error(logger, e, "Error getting rider data history")
            log_function_exit(logger, "get_rider_data_history", {"success": False})
            return []
    
    def _quick_completeness_check(self, rider_data: Dict[str, Any]) -> float:
        """Quick completeness check for rider data."""
        required_components = ["basic_info", "stats", "zones", "recent_activities", "fitness_metrics"]
        available = sum(1 for component in required_components if rider_data.get(component))
        return available / len(required_components)