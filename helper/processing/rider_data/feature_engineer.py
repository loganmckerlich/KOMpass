"""
Feature Engineering Module - Prepares rider data for machine learning applications.

This module handles:
- Feature extraction from rider data
- Data transformation for ML models
- Composite performance score calculations
- Feature engineering pipeline
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class FeatureEngineer:
    """Handles feature engineering for rider data."""
    
    def get_feature_engineering_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features suitable for machine learning from rider data.
        
        Args:
            rider_data: Complete rider data dictionary
            
        Returns:
            Dictionary containing engineered features
        """
        log_function_entry(logger, "get_feature_engineering_data")
        
        features = {
            "basic_features": {},
            "performance_features": {},
            "training_features": {},
            "temporal_features": {},
            "composite_scores": {}
        }
        
        try:
            # Extract basic features
            features["basic_features"] = self._extract_basic_features(rider_data)
            
            # Extract performance features (pass basic features for FTP fallback)
            features["performance_features"] = self._extract_performance_features(rider_data, features["basic_features"])
            
            # Extract training pattern features
            features["training_features"] = self._extract_training_features(rider_data)
            
            # Extract temporal features
            features["temporal_features"] = self._extract_temporal_features(rider_data)
            
            # Calculate composite performance scores
            features["composite_scores"] = self._calculate_composite_performance_scores(features)
            
            # Add metadata
            features["feature_extraction_timestamp"] = datetime.now().isoformat()
            features["total_features"] = self._count_total_features(features)
            
            logger.info(f"Feature engineering completed: {features['total_features']} features extracted")
            
        except Exception as e:
            logger.error(f"Error in feature engineering: {e}")
            features["error"] = str(e)
        
        log_function_exit(logger, "get_feature_engineering_data")
        return features
    
    def _extract_basic_features(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic athlete features."""
        basic_features = {}
        
        if "basic_info" in rider_data and rider_data["basic_info"]:
            basic_info = rider_data["basic_info"]
            
            # Account age (if created_at available)
            if "created_at" in basic_info:
                try:
                    created_date = datetime.fromisoformat(basic_info["created_at"].replace('Z', '+00:00'))
                    account_age_days = (datetime.now() - created_date.replace(tzinfo=None)).days
                    basic_features["account_age_days"] = account_age_days
                    basic_features["account_age_years"] = account_age_days / 365.25
                except:
                    pass
            
            # Extract available numeric fields including weight and FTP
            numeric_fields = ["follower_count", "friend_count", "mutual_friend_count", "weight", "ftp"]
            for field in numeric_fields:
                if field in basic_info and isinstance(basic_info[field], (int, float)):
                    if field == "weight":
                        basic_features["weight_kg"] = basic_info[field]
                    elif field == "ftp":
                        basic_features["athlete_ftp"] = basic_info[field]
                    else:
                        basic_features[field] = basic_info[field]
        
        return basic_features
    
    def _extract_performance_features(self, rider_data: Dict[str, Any], basic_features: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract performance-related features."""
        performance_features = {}
        
        # Extract FTP from zones data as primary source
        if "zones" in rider_data and rider_data["zones"]:
            zones_data = rider_data["zones"]
            
            # Look for power zones with FTP information
            if "power" in zones_data and zones_data["power"]:
                power_zones = zones_data["power"]
                if "zones" in power_zones and power_zones["zones"]:
                    # FTP is typically the upper boundary of Zone 4 (Threshold)
                    # or we can infer it from zone boundaries
                    zones_list = power_zones["zones"]
                    if len(zones_list) >= 4:  # Should have at least 4 zones
                        # Zone 4 (threshold) upper boundary is typically close to FTP
                        zone4_max = zones_list[3].get("max", 0)
                        if zone4_max > 0:
                            performance_features["estimated_ftp"] = zone4_max
        
        # If no FTP from zones, try to get from basic_features (athlete_ftp)
        if "estimated_ftp" not in performance_features and basic_features:
            if "athlete_ftp" in basic_features and basic_features["athlete_ftp"] > 0:
                performance_features["estimated_ftp"] = basic_features["athlete_ftp"]
        
        # Power analysis features
        if "power_analysis" in rider_data and rider_data["power_analysis"]:
            power_data = rider_data["power_analysis"]
            
            if "power_trend" in power_data:
                trend = power_data["power_trend"]
                performance_features["power_trend_value"] = trend.get("trend_value", 0)
                performance_features["recent_power_avg"] = trend.get("recent_power_avg", 0)
                performance_features["power_improving"] = 1 if trend.get("trend") == "improving" else 0
            
            if "weighted_power_avg" in power_data:
                performance_features["weighted_power_avg"] = power_data["weighted_power_avg"]
        
        # VO2 max features
        if "vo2_analysis" in rider_data and rider_data["vo2_analysis"]:
            vo2_data = rider_data["vo2_analysis"]
            if "estimated_vo2_max" in vo2_data:
                performance_features["estimated_vo2_max"] = vo2_data["estimated_vo2_max"]
                performance_features["vo2_max_classification"] = self._encode_vo2_classification(
                    vo2_data.get("classification", "Unknown")
                )
        
        # Activity-based performance features
        if "recent_activities" in rider_data and rider_data["recent_activities"]:
            activities = rider_data["recent_activities"]
            performance_features.update(self._extract_activity_performance_features(activities))
        
        return performance_features
    
    def _extract_training_features(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract training pattern and load features."""
        training_features = {}
        
        # Fitness metrics
        if "fitness_metrics" in rider_data and rider_data["fitness_metrics"]:
            fitness_data = rider_data["fitness_metrics"]
            
            if "activity_frequency" in fitness_data:
                freq_data = fitness_data["activity_frequency"]
                training_features["activities_per_week"] = freq_data.get("activities_per_week", 0)
                training_features["total_activities"] = freq_data.get("total_activities", 0)
            
            if "training_hours" in fitness_data:
                hours_data = fitness_data["training_hours"]
                training_features["hours_per_week"] = hours_data.get("hours_per_week", 0)
                training_features["total_training_hours"] = hours_data.get("total_hours", 0)
            
            if "consistency" in fitness_data:
                training_features["training_consistency"] = fitness_data["consistency"]
            
            if "intensity_distribution" in fitness_data:
                intensity_data = fitness_data["intensity_distribution"]
                training_features["average_training_power"] = intensity_data.get("average_power", 0)
                training_features["power_variability"] = intensity_data.get("power_variability", 0)
                training_features["high_intensity_ratio"] = (
                    intensity_data.get("high_intensity_sessions", 0) / 
                    max(intensity_data.get("total_power_sessions", 1), 1)
                )
        
        # Training load features
        if "training_load" in rider_data and rider_data["training_load"]:
            load_data = rider_data["training_load"]
            
            if "training_intensity" in load_data:
                training_features["overall_training_intensity"] = load_data["training_intensity"]
            
            if "stress_balance" in load_data:
                stress_data = load_data["stress_balance"]
                training_features["training_stress_balance"] = stress_data.get("stress_balance", 0)
                training_features["recent_weekly_stress"] = stress_data.get("recent_weekly_stress", 0)
        
        return training_features
    
    def _extract_temporal_features(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract time-based features."""
        temporal_features = {}
        
        if "recent_activities" in rider_data and rider_data["recent_activities"]:
            activities = rider_data["recent_activities"]
            df = pd.DataFrame(activities)
            
            if not df.empty and "start_date" in df.columns:
                df["start_date"] = pd.to_datetime(df["start_date"])
                
                # Time since last activity
                last_activity = df["start_date"].max()
                days_since_last = (datetime.now() - last_activity.replace(tzinfo=None)).days
                temporal_features["days_since_last_activity"] = days_since_last
                
                # Activity patterns
                df["hour"] = df["start_date"].dt.hour
                df["day_of_week"] = df["start_date"].dt.dayofweek
                
                # Preferred training times
                temporal_features["most_common_hour"] = df["hour"].mode().iloc[0] if not df["hour"].mode().empty else 12
                temporal_features["most_common_day"] = df["day_of_week"].mode().iloc[0] if not df["day_of_week"].mode().empty else 0
                
                # Morning vs evening preference
                morning_activities = len(df[df["hour"] < 12])
                evening_activities = len(df[df["hour"] >= 18])
                total_activities = len(df)
                
                temporal_features["morning_training_ratio"] = morning_activities / total_activities
                temporal_features["evening_training_ratio"] = evening_activities / total_activities
                
                # Weekly pattern consistency
                weekly_pattern = df.groupby("day_of_week").size()
                temporal_features["weekly_pattern_consistency"] = 1 - (weekly_pattern.std() / weekly_pattern.mean()) if weekly_pattern.mean() > 0 else 0
        
        return temporal_features
    
    def _extract_activity_performance_features(self, activities: List[Dict]) -> Dict[str, Any]:
        """Extract performance features from activities data."""
        features = {}
        
        if not activities:
            return features
        
        df = pd.DataFrame(activities)
        
        # Distance features
        if "distance" in df.columns:
            features["avg_distance"] = df["distance"].mean()
            features["max_distance"] = df["distance"].max()
            features["distance_variability"] = df["distance"].std()
        
        # Speed features
        if "average_speed" in df.columns:
            speed_df = df[df["average_speed"] > 0]
            if not speed_df.empty:
                features["avg_speed"] = speed_df["average_speed"].mean()
                features["max_speed"] = speed_df["average_speed"].max()
                features["speed_consistency"] = 1 - (speed_df["average_speed"].std() / speed_df["average_speed"].mean())
        
        # Elevation features
        if "total_elevation_gain" in df.columns:
            elev_df = df[df["total_elevation_gain"] > 0]
            if not elev_df.empty:
                features["avg_elevation_gain"] = elev_df["total_elevation_gain"].mean()
                features["max_elevation_gain"] = elev_df["total_elevation_gain"].max()
                features["climbing_preference"] = len(elev_df) / len(df)
        
        # Heart rate features
        if "average_heartrate" in df.columns:
            hr_df = df[df["average_heartrate"] > 0]
            if not hr_df.empty:
                features["avg_heart_rate"] = hr_df["average_heartrate"].mean()
                features["max_heart_rate"] = hr_df["average_heartrate"].max()
                features["hr_variability"] = hr_df["average_heartrate"].std()
        
        # Power features
        if "average_watts" in df.columns:
            power_df = df[df["average_watts"] > 0]
            if not power_df.empty:
                features["avg_power"] = power_df["average_watts"].mean()
                features["max_power"] = power_df["average_watts"].max()
                features["power_consistency"] = 1 - (power_df["average_watts"].std() / power_df["average_watts"].mean())
        
        # Activity type diversity
        if "type" in df.columns:
            activity_types = df["type"].value_counts()
            features["activity_type_diversity"] = len(activity_types)
            features["primary_activity_type"] = activity_types.index[0] if not activity_types.empty else "Unknown"
        
        return features
    
    def _calculate_composite_performance_scores(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate composite performance scores."""
        composite_scores = {}
        
        try:
            # Overall fitness score (0-100)
            fitness_components = []
            
            # Cardiovascular fitness component
            if "estimated_vo2_max" in features.get("performance_features", {}):
                vo2_max = features["performance_features"]["estimated_vo2_max"]
                cv_score = min(vo2_max / 70 * 100, 100)  # Normalize to 100, cap at 70 VO2 max
                fitness_components.append(cv_score)
            
            # Power performance component
            if "weighted_power_avg" in features.get("performance_features", {}):
                power_avg = features["performance_features"]["weighted_power_avg"]
                power_score = min(power_avg / 300 * 100, 100)  # Normalize to 100, cap at 300W
                fitness_components.append(power_score)
            
            # Training consistency component
            if "training_consistency" in features.get("training_features", {}):
                consistency = features["training_features"]["training_consistency"]
                consistency_score = consistency * 100
                fitness_components.append(consistency_score)
            
            if fitness_components:
                composite_scores["overall_fitness_score"] = np.mean(fitness_components)
            
            # Training quality score (0-100)
            quality_components = []
            
            # Training frequency
            if "activities_per_week" in features.get("training_features", {}):
                freq = features["training_features"]["activities_per_week"]
                freq_score = min(freq / 5 * 100, 100)  # Normalize to 5 activities per week
                quality_components.append(freq_score)
            
            # Training intensity balance
            if "high_intensity_ratio" in features.get("training_features", {}):
                intensity_ratio = features["training_features"]["high_intensity_ratio"]
                # Optimal ratio around 0.2 (20% high intensity)
                intensity_score = 100 - abs(intensity_ratio - 0.2) * 500
                intensity_score = max(0, min(100, intensity_score))
                quality_components.append(intensity_score)
            
            if quality_components:
                composite_scores["training_quality_score"] = np.mean(quality_components)
            
            # Performance trend score (-100 to +100)
            trend_components = []
            
            if "power_trend_value" in features.get("performance_features", {}):
                power_trend = features["performance_features"]["power_trend_value"]
                trend_components.append(power_trend * 100)  # Convert to percentage
            
            if trend_components:
                composite_scores["performance_trend_score"] = np.mean(trend_components)
            
            # Experience score (0-100)
            experience_components = []
            
            if "account_age_years" in features.get("basic_features", {}):
                age_years = features["basic_features"]["account_age_years"]
                exp_score = min(age_years / 5 * 100, 100)  # Normalize to 5 years experience
                experience_components.append(exp_score)
            
            if "total_activities" in features.get("training_features", {}):
                total_activities = features["training_features"]["total_activities"]
                activity_exp_score = min(total_activities / 500 * 100, 100)  # Normalize to 500 activities
                experience_components.append(activity_exp_score)
            
            if experience_components:
                composite_scores["experience_score"] = np.mean(experience_components)
            
        except Exception as e:
            logger.error(f"Error calculating composite scores: {e}")
            composite_scores["calculation_error"] = str(e)
        
        return composite_scores
    
    def _encode_vo2_classification(self, classification: str) -> int:
        """Encode VO2 max classification as numeric value."""
        classification_map = {
            "Elite": 5,
            "Excellent": 4,
            "Good": 3,
            "Fair": 2,
            "Poor": 1,
            "Unknown": 0
        }
        return classification_map.get(classification, 0)
    
    def _count_total_features(self, features: Dict[str, Any]) -> int:
        """Count total number of features extracted."""
        total = 0
        for category, feature_dict in features.items():
            if isinstance(feature_dict, dict):
                total += len([k for k, v in feature_dict.items() if isinstance(v, (int, float))])
        return total