"""
Fitness Metrics Analyzer - Processes rider fitness and performance data.

This module handles calculations for:
- General fitness metrics and trends
- Power analysis and critical power curves
- Training load and stress analysis
- VO2 max estimation
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import math

from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class FitnessMetricsAnalyzer:
    """Analyzes rider fitness metrics and trends."""
    
    def calculate_fitness_metrics(self, activities: List[Dict], zones: Optional[Dict]) -> Dict[str, Any]:
        """
        Calculate comprehensive fitness metrics from activities.
        
        Args:
            activities: List of activity data
            zones: Power and heart rate zones data
            
        Returns:
            Dictionary containing fitness metrics
        """
        log_function_entry(logger, "calculate_fitness_metrics")
        
        if not activities:
            logger.warning("No activities provided for fitness metrics calculation")
            return {}
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(activities)
        
        # Basic activity frequency and volume
        metrics = {
            "activity_frequency": self._calculate_activity_frequency(df),
            "training_hours": self._calculate_weekly_training_hours(df),
            "fitness_trend": self._calculate_fitness_trend(df),
            "consistency": self._calculate_training_consistency(df),
            "intensity_distribution": self._calculate_intensity_distribution(df, zones),
            "recovery_metrics": self._calculate_recovery_metrics(df)
        }
        
        log_function_exit(logger, "calculate_fitness_metrics")
        return metrics
    
    def analyze_power_metrics(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze power-related metrics and performance.
        
        Args:
            stats: Athlete statistics including power records
            activities: Recent activities data
            
        Returns:
            Dictionary containing power analysis
        """
        log_function_entry(logger, "analyze_power_metrics")
        
        power_analysis = {}
        
        if stats and 'all_ride_totals' in stats:
            # Power records analysis
            power_analysis['power_records'] = self._extract_power_records(stats)
            power_analysis['critical_power_curve'] = self._analyze_critical_power_curve(stats, activities)
            power_analysis['performance_level'] = self._classify_performance_level(power_analysis.get('critical_power_curve', {}))
        
        # Training power trends from activities
        if activities:
            df = pd.DataFrame(activities)
            power_df = df[df['average_watts'].notna() & (df['average_watts'] > 0)]
            
            if not power_df.empty:
                power_analysis['power_trend'] = self._calculate_power_trend(power_df)
                power_analysis['weighted_power_avg'] = self._calculate_weighted_power_average(power_df)
        
        log_function_exit(logger, "analyze_power_metrics")
        return power_analysis
    
    def analyze_training_load(self, activities: List[Dict]) -> Dict[str, Any]:
        """
        Analyze training load and stress metrics.
        
        Args:
            activities: List of activity data
            
        Returns:
            Dictionary containing training load analysis
        """
        log_function_entry(logger, "analyze_training_load")
        
        if not activities:
            return {}
        
        df = pd.DataFrame(activities)
        
        training_load = {
            "weekly_hours": self._calculate_weekly_training_hours(df),
            "training_intensity": self._calculate_training_intensity(df),
            "stress_balance": self._calculate_training_stress_balance(df),
            "peak_period": self._identify_peak_training_period(df)
        }
        
        log_function_exit(logger, "analyze_training_load")
        return training_load
    
    def estimate_vo2_max(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """
        Estimate VO2 max from power data and activities.
        
        Args:
            stats: Athlete statistics
            activities: Recent activities
            
        Returns:
            Dictionary containing VO2 max estimation
        """
        log_function_entry(logger, "estimate_vo2_max")
        
        vo2_analysis = {}
        
        # Method 1: From 20-minute power record (if available)
        if stats and 'all_ride_totals' in stats:
            power_20min = None
            for pr in stats.get('biggest_ride_distance', {}).get('power', []):
                if '20' in str(pr.get('duration', 0)):  # Approximate 20-minute effort
                    power_20min = pr.get('value')
                    break
            
            if power_20min:
                # VO2 max estimation: VO2 = 10.8 * P + 7
                # Where P is watts/kg for 20-minute power
                estimated_weight = 75  # Default assumption, could be improved with actual weight
                power_per_kg = power_20min / estimated_weight
                vo2_max_estimated = 10.8 * power_per_kg + 7
                
                vo2_analysis['estimated_vo2_max'] = vo2_max_estimated
                vo2_analysis['classification'] = self._classify_vo2_max(vo2_max_estimated)
                vo2_analysis['method'] = '20-minute power'
        
        # Method 2: From recent activity power data
        if activities and not vo2_analysis:
            df = pd.DataFrame(activities)
            power_df = df[df['average_watts'].notna() & (df['average_watts'] > 0)]
            
            if not power_df.empty:
                # Use highest sustained power efforts
                max_power = power_df['average_watts'].max()
                estimated_weight = 75
                power_per_kg = max_power / estimated_weight
                vo2_max_estimated = 10.8 * power_per_kg + 7
                
                vo2_analysis['estimated_vo2_max'] = vo2_max_estimated
                vo2_analysis['classification'] = self._classify_vo2_max(vo2_max_estimated)
                vo2_analysis['method'] = 'activity power average'
        
        log_function_exit(logger, "estimate_vo2_max")
        return vo2_analysis
    
    def _extract_power_records(self, stats: Dict) -> Dict[str, Any]:
        """Extract and format power records from stats."""
        power_records = {}
        
        if 'all_ride_totals' in stats:
            ride_totals = stats['all_ride_totals']
            
            # Extract various power metrics if available
            if 'achievement_count' in ride_totals:
                power_records['achievements'] = ride_totals['achievement_count']
            
            # Look for power-related records in the stats structure
            # This structure may vary depending on Strava API response
            
        return power_records
    
    def _analyze_critical_power_curve(self, stats: Optional[Dict], activities: List[Dict]) -> Dict[str, Any]:
        """Analyze critical power curve from available data."""
        # Simplified implementation - in real app would need more sophisticated analysis
        return {
            "analysis_available": bool(stats and activities),
            "data_points": len(activities) if activities else 0
        }
    
    def _classify_performance_level(self, cp_curve: Dict[str, Any]) -> str:
        """Classify performance level based on critical power curve."""
        if not cp_curve.get("analysis_available"):
            return "Unknown"
        
        # Simplified classification - would need actual power curve analysis
        data_points = cp_curve.get("data_points", 0)
        if data_points > 50:
            return "Well-trained"
        elif data_points > 20:
            return "Trained"
        else:
            return "Recreational"
    
    def _classify_vo2_max(self, vo2_max: float) -> str:
        """Classify VO2 max into performance categories."""
        if vo2_max >= 65:
            return "Elite"
        elif vo2_max >= 55:
            return "Excellent"
        elif vo2_max >= 45:
            return "Good"
        elif vo2_max >= 35:
            return "Fair"
        else:
            return "Poor"
    
    def _calculate_activity_frequency(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate activity frequency metrics."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        days_span = (df['start_date'].max() - df['start_date'].min()).days
        
        return {
            "activities_per_week": len(df) / max(days_span / 7, 1),
            "total_activities": len(df),
            "days_analyzed": days_span
        }
    
    def _calculate_weekly_training_hours(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate weekly training hours."""
        if df.empty or 'moving_time' not in df.columns:
            return {}
        
        total_hours = df['moving_time'].sum() / 3600  # Convert seconds to hours
        df['start_date'] = pd.to_datetime(df['start_date'])
        weeks = (df['start_date'].max() - df['start_date'].min()).days / 7
        
        return {
            "total_hours": total_hours,
            "hours_per_week": total_hours / max(weeks, 1),
            "weeks_analyzed": weeks
        }
    
    def _calculate_fitness_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate fitness trend over time."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        df_sorted = df.sort_values('start_date')
        
        # Simple trend based on activity frequency and intensity
        weekly_groups = df_sorted.groupby(df_sorted['start_date'].dt.to_period('W'))
        weekly_counts = weekly_groups.size()
        
        if len(weekly_counts) < 2:
            return {"trend": "insufficient_data"}
        
        # Calculate trend (positive = improving, negative = declining)
        recent_avg = weekly_counts.tail(4).mean()
        earlier_avg = weekly_counts.head(4).mean()
        trend = (recent_avg - earlier_avg) / max(earlier_avg, 1)
        
        return {
            "trend": "improving" if trend > 0.1 else "stable" if trend > -0.1 else "declining",
            "trend_value": trend,
            "recent_weekly_avg": recent_avg,
            "earlier_weekly_avg": earlier_avg
        }
    
    def _calculate_training_consistency(self, df: pd.DataFrame) -> float:
        """Calculate training consistency score (0-1)."""
        if df.empty:
            return 0.0
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        weekly_groups = df.groupby(df['start_date'].dt.to_period('W'))
        weekly_counts = weekly_groups.size()
        
        if len(weekly_counts) < 2:
            return 0.0
        
        # Consistency based on standard deviation of weekly activity counts
        mean_weekly = weekly_counts.mean()
        std_weekly = weekly_counts.std()
        
        if mean_weekly == 0:
            return 0.0
        
        # Lower coefficient of variation = higher consistency
        cv = std_weekly / mean_weekly
        consistency = max(0, 1 - cv)
        
        return min(consistency, 1.0)
    
    def _calculate_intensity_distribution(self, df: pd.DataFrame, zones: Optional[Dict]) -> Dict[str, Any]:
        """Calculate training intensity distribution."""
        if df.empty:
            return {}
        
        # Simple intensity calculation based on average power
        if 'average_watts' in df.columns:
            power_df = df[df['average_watts'].notna() & (df['average_watts'] > 0)]
            
            if not power_df.empty:
                power_mean = power_df['average_watts'].mean()
                power_std = power_df['average_watts'].std()
                
                return {
                    "average_power": power_mean,
                    "power_variability": power_std,
                    "high_intensity_sessions": len(power_df[power_df['average_watts'] > power_mean + power_std]),
                    "total_power_sessions": len(power_df)
                }
        
        return {}
    
    def _calculate_power_trend(self, power_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate power trend over time."""
        if power_df.empty:
            return {}
        
        power_df['start_date'] = pd.to_datetime(power_df['start_date'])
        power_df_sorted = power_df.sort_values('start_date')
        
        # Simple trend calculation
        recent_power = power_df_sorted.tail(10)['average_watts'].mean()
        earlier_power = power_df_sorted.head(10)['average_watts'].mean()
        
        trend = (recent_power - earlier_power) / max(earlier_power, 1)
        
        return {
            "trend": "improving" if trend > 0.05 else "stable" if trend > -0.05 else "declining",
            "trend_value": trend,
            "recent_power_avg": recent_power,
            "earlier_power_avg": earlier_power
        }
    
    def _calculate_weighted_power_average(self, power_df: pd.DataFrame) -> float:
        """Calculate weighted average power over recent activities."""
        if power_df.empty:
            return 0.0
        
        # Weight by recency (more recent activities have higher weight)
        power_df['start_date'] = pd.to_datetime(power_df['start_date'])
        max_date = power_df['start_date'].max()
        power_df['days_ago'] = (max_date - power_df['start_date']).dt.days
        
        # Exponential decay weight (half-life of 30 days)
        power_df['weight'] = np.exp(-power_df['days_ago'] / 30)
        
        weighted_sum = (power_df['average_watts'] * power_df['weight']).sum()
        weight_sum = power_df['weight'].sum()
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_training_intensity(self, df: pd.DataFrame) -> float:
        """Calculate overall training intensity score."""
        if df.empty:
            return 0.0
        
        # Simple intensity based on average power and heart rate
        intensity_score = 0.0
        
        if 'average_watts' in df.columns:
            power_df = df[df['average_watts'].notna() & (df['average_watts'] > 0)]
            if not power_df.empty:
                # Normalize power intensity (assuming 200W as moderate)
                intensity_score += (power_df['average_watts'].mean() / 200) * 0.6
        
        if 'average_heartrate' in df.columns:
            hr_df = df[df['average_heartrate'].notna() & (df['average_heartrate'] > 0)]
            if not hr_df.empty:
                # Normalize HR intensity (assuming 150 bpm as moderate)
                intensity_score += (hr_df['average_heartrate'].mean() / 150) * 0.4
        
        return min(intensity_score, 2.0)  # Cap at 2.0 for very high intensity
    
    def _calculate_recovery_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate recovery-related metrics."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        df_sorted = df.sort_values('start_date')
        
        # Calculate time between activities
        time_diffs = df_sorted['start_date'].diff().dt.total_seconds() / 3600  # Hours
        
        return {
            "average_recovery_hours": time_diffs.mean() if not time_diffs.empty else 0,
            "min_recovery_hours": time_diffs.min() if not time_diffs.empty else 0,
            "max_recovery_hours": time_diffs.max() if not time_diffs.empty else 0
        }
    
    def _calculate_training_stress_balance(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate training stress balance metrics."""
        if df.empty:
            return {}
        
        # Simplified TSB calculation based on activity frequency and intensity
        df['start_date'] = pd.to_datetime(df['start_date'])
        
        # Group by week and calculate weekly stress
        weekly_groups = df.groupby(df['start_date'].dt.to_period('W'))
        weekly_stress = []
        
        for week, group in weekly_groups:
            if 'moving_time' in group.columns:
                hours = group['moving_time'].sum() / 3600
                stress = hours * 10  # Simplified stress calculation
                weekly_stress.append(stress)
        
        if len(weekly_stress) < 2:
            return {}
        
        # Calculate recent vs. historical stress
        recent_stress = np.mean(weekly_stress[-4:]) if len(weekly_stress) >= 4 else np.mean(weekly_stress)
        historical_stress = np.mean(weekly_stress[:-4]) if len(weekly_stress) > 4 else recent_stress
        
        return {
            "recent_weekly_stress": recent_stress,
            "historical_weekly_stress": historical_stress,
            "stress_balance": (recent_stress - historical_stress) / max(historical_stress, 1)
        }
    
    def _identify_peak_training_period(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Identify peak training period in the dataset."""
        if df.empty:
            return {}
        
        df['start_date'] = pd.to_datetime(df['start_date'])
        
        # Group by week and find peak volume
        weekly_groups = df.groupby(df['start_date'].dt.to_period('W'))
        weekly_hours = weekly_groups['moving_time'].sum() / 3600 if 'moving_time' in df.columns else weekly_groups.size()
        
        if weekly_hours.empty:
            return {}
        
        peak_week = weekly_hours.idxmax()
        peak_value = weekly_hours.max()
        
        return {
            "peak_week": str(peak_week),
            "peak_value": peak_value,
            "metric": "hours" if 'moving_time' in df.columns else "activities"
        }