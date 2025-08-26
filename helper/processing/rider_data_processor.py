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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
from ..config.logging_config import get_logger, log_function_entry, log_function_exit, log_error

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
            
            # Power-related features
            if rider_data.get("power_analysis"):
                power_analysis = rider_data["power_analysis"]
                features.update({
                    "recent_avg_power": power_analysis.get("recent_power_metrics", {}).get("avg_power_last_30_days"),
                    "power_consistency": power_analysis.get("recent_power_metrics", {}).get("power_consistency"),
                    "power_trend_improving": 1 if power_analysis.get("recent_power_metrics", {}).get("power_trend", {}).get("trend_direction") == "improving" else 0
                })
            
            # Fitness features
            if rider_data.get("fitness_metrics"):
                fitness = rider_data["fitness_metrics"]
                features.update({
                    "activity_frequency_per_week": fitness.get("activity_frequency", {}).get("activities_per_week", 0),
                    "training_consistency_score": fitness.get("training_consistency", 0),
                    "avg_heart_rate": fitness.get("intensity_distribution", {}).get("avg_heart_rate")
                })
            
            # Training load features
            if rider_data.get("training_load"):
                load = rider_data["training_load"]
                features.update({
                    "avg_weekly_training_hours": load.get("weekly_training_hours", {}).get("avg_weekly_hours", 0),
                    "training_stress_balance": load.get("training_stress_balance", {}).get("training_stress_balance", 0),
                    "recovery_consistency": load.get("recovery_metrics", {}).get("recovery_consistency", 0)
                })
            
            logger.info(f"Engineered {len(features)} features for ML applications")
            return features
            
        except Exception as e:
            log_error(logger, e, "Error engineering features")
            return features
    
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
                "fitness_metrics", "power_analysis", "training_load"
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