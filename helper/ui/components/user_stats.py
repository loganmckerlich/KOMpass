"""
User Stats Page Component - Displays personal cycling metrics and performance data.

This component shows the user's cycling performance metrics including:
- FTP and power data
- Training history and trends
- Personal records and achievements
- Fitness analysis based on Strava data
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ...config.logging_config import get_logger
from ...auth.auth_manager import get_auth_manager


logger = get_logger(__name__)


class UserStatsPage:
    """Handles rendering of user statistics and personal cycling metrics."""
    
    def __init__(self):
        """Initialize user stats page."""
        self.auth_manager = get_auth_manager()
    
    def render_user_stats_page(self):
        """Render the user stats page with personal cycling metrics."""
        logger.info("Rendering user stats page")
        
        # Ensure user is authenticated
        if not self.auth_manager.is_authenticated():
            st.error("⚠️ Authentication required to view user stats")
            return
        
        # Get athlete and rider data
        athlete_info = self.auth_manager.get_athlete_info()
        rider_data = self.auth_manager.get_rider_fitness_data()
        
        if not athlete_info:
            st.error("❌ Failed to load athlete information")
            return
        
        # Page header
        st.markdown("# 📊 Your Cycling Stats")
        
        athlete_name = f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}".strip()
        st.markdown(f"### Personal metrics for **{athlete_name or 'Cyclist'}**")
        
        # Check if we have rider data
        if not rider_data:
            self._render_no_data_message()
            return
        
        # Render different sections of user stats
        self._render_overview_metrics(athlete_info, rider_data)
        self._render_power_metrics(rider_data)
        self._render_training_analysis(rider_data)
        self._render_recent_performance(rider_data)
    
    def _render_no_data_message(self):
        """Render message when no rider data is available."""
        st.warning("⏳ Loading your cycling data...")
        
        with st.expander("ℹ️ What data do we analyze?"):
            st.markdown("""
            KOMpass analyzes your Strava data to provide insights including:
            
            **Power Analysis:**
            - Functional Threshold Power (FTP) estimates
            - Critical power curves (5s, 1min, 5min, 20min)
            - Power zone distribution
            
            **Training Metrics:**
            - Weekly training hours
            - Training stress and intensity
            - Activity patterns and trends
            
            **Performance Tracking:**
            - Recent performance trends
            - Personal records and achievements
            - Fitness progression over time
            
            *Note: It may take a moment to process your recent activities.*
            """)
    
    def _render_overview_metrics(self, athlete_info: Dict[str, Any], rider_data: Dict[str, Any]):
        """Render overview metrics cards."""
        st.markdown("## 🎯 Performance Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Extract basic info
        basic_features = rider_data.get('basic_features', {})
        performance_features = rider_data.get('performance_features', {})
        training_features = rider_data.get('training_features', {})
        
        with col1:
            ftp = performance_features.get('estimated_ftp', 0)
            st.metric(
                label="🔋 Estimated FTP",
                value=f"{int(ftp)} W" if ftp > 0 else "N/A",
                help="Functional Threshold Power - sustainable power for 1 hour"
            )
        
        with col2:
            weight = basic_features.get('weight_kg', 0)
            power_to_weight = (ftp / weight) if weight > 0 and ftp > 0 else 0
            st.metric(
                label="⚖️ Power-to-Weight",
                value=f"{power_to_weight:.1f} W/kg" if power_to_weight > 0 else "N/A",
                help="Power-to-weight ratio for climbing performance"
            )
        
        with col3:
            training_hours = training_features.get('hours_per_week', 0)
            st.metric(
                label="⏱️ Weekly Hours",
                value=f"{training_hours:.1f}h" if training_hours > 0 else "N/A",
                help="Average training hours per week"
            )
        
        with col4:
            activities_count = len(rider_data.get('recent_activities', []))
            st.metric(
                label="🚴 Recent Activities",
                value=str(activities_count),
                help="Number of recent cycling activities analyzed"
            )
    
    def _render_power_metrics(self, rider_data: Dict[str, Any]):
        """Render power analysis metrics."""
        st.markdown("## ⚡ Power Analysis")
        
        performance_features = rider_data.get('performance_features', {})
        
        if not performance_features:
            st.info("📊 Power analysis will be available once more activities are processed.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🎯 Critical Power Estimates")
            
            # Power duration metrics
            power_5s = performance_features.get('max_power_5s', 0)
            power_1min = performance_features.get('max_power_1min', 0)
            power_5min = performance_features.get('max_power_5min', 0)
            power_20min = performance_features.get('max_power_20min', 0)
            
            if power_5s > 0:
                st.metric("🚀 5-second Power", f"{int(power_5s)} W", help="Sprint power")
            if power_1min > 0:
                st.metric("💪 1-minute Power", f"{int(power_1min)} W", help="Neuromuscular power")
            if power_5min > 0:
                st.metric("🏃 5-minute Power", f"{int(power_5min)} W", help="VO2 max power")
            if power_20min > 0:
                st.metric("⏰ 20-minute Power", f"{int(power_20min)} W", help="Threshold power")
        
        with col2:
            st.markdown("### 📈 Power Distribution")
            
            # Power zone analysis
            avg_power = performance_features.get('weighted_power_avg', 0)
            max_power = performance_features.get('max_power_overall', 0)
            
            if avg_power > 0:
                st.metric("📊 Average Power", f"{int(avg_power)} W", help="Weighted average power")
            if max_power > 0:
                st.metric("⚡ Peak Power", f"{int(max_power)} W", help="Maximum recorded power")
            
            # Efficiency metrics
            efficiency = performance_features.get('power_efficiency_score', 0)
            if efficiency > 0:
                st.metric(
                    "🎯 Power Efficiency", 
                    f"{efficiency:.1f}%",
                    help="Consistency in power output"
                )
    
    def _render_training_analysis(self, rider_data: Dict[str, Any]):
        """Render training analysis section."""
        st.markdown("## 📚 Training Analysis")
        
        training_features = rider_data.get('training_features', {})
        
        if not training_features:
            st.info("📊 Training analysis will be available once more activities are processed.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📊 Training Load")
            
            # Training intensity
            intensity = training_features.get('training_intensity_score', 0)
            if intensity > 0:
                st.metric(
                    "🔥 Training Intensity",
                    f"{intensity:.1f}",
                    help="Average training intensity score"
                )
            
            # Training consistency
            consistency = training_features.get('training_consistency_score', 0)
            if consistency > 0:
                st.metric(
                    "📅 Training Consistency",
                    f"{consistency:.1f}%",
                    help="Consistency of training schedule"
                )
        
        with col2:
            st.markdown("### 🎯 Zone Distribution")
            
            # Zone time distribution
            zone1_time = training_features.get('zone1_time_percent', 0)
            zone2_time = training_features.get('zone2_time_percent', 0)
            zone4_time = training_features.get('zone4_time_percent', 0)
            
            if zone1_time > 0:
                st.metric("Zone 1 (Recovery)", f"{zone1_time:.1f}%")
            if zone2_time > 0:
                st.metric("Zone 2 (Endurance)", f"{zone2_time:.1f}%")
            if zone4_time > 0:
                st.metric("Zone 4 (Threshold)", f"{zone4_time:.1f}%")
    
    def _render_recent_performance(self, rider_data: Dict[str, Any]):
        """Render recent performance trends."""
        st.markdown("## 📈 Recent Performance")
        
        recent_activities = rider_data.get('recent_activities', [])
        
        if not recent_activities:
            st.info("📊 Recent performance data will appear here once activities are analyzed.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🚴 Activity Summary")
            
            # Recent activity stats
            total_distance = sum(activity.get('distance', 0) for activity in recent_activities) / 1000  # Convert to km
            total_time = sum(activity.get('moving_time', 0) for activity in recent_activities) / 3600  # Convert to hours
            
            st.metric("📏 Total Distance", f"{total_distance:.0f} km")
            st.metric("⏱️ Total Time", f"{total_time:.1f} hours")
            
            if total_time > 0:
                avg_speed = total_distance / total_time
                st.metric("🏃 Average Speed", f"{avg_speed:.1f} km/h")
        
        with col2:
            st.markdown("### 📊 Recent Trends")
            
            # Performance trends
            if len(recent_activities) >= 5:
                recent_5 = recent_activities[:5]
                avg_power_recent = sum(activity.get('average_watts', 0) for activity in recent_5 if activity.get('average_watts', 0) > 0)
                count_with_power = sum(1 for activity in recent_5 if activity.get('average_watts', 0) > 0)
                
                if count_with_power > 0:
                    avg_power_recent = avg_power_recent / count_with_power
                    st.metric("⚡ Recent Avg Power", f"{int(avg_power_recent)} W")
            
            # Last activity info
            if recent_activities:
                last_activity = recent_activities[0]
                last_date = last_activity.get('start_date_local', '')
                if last_date:
                    try:
                        last_date_parsed = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
                        days_ago = (datetime.now() - last_date_parsed.replace(tzinfo=None)).days
                        st.metric("📅 Last Activity", f"{days_ago} days ago")
                    except:
                        st.metric("📅 Last Activity", "Recently")
        
        # Show activity list
        if recent_activities:
            with st.expander(f"📋 View Recent Activities ({len(recent_activities)} total)"):
                for i, activity in enumerate(recent_activities[:10]):  # Show first 10
                    name = activity.get('name', f'Activity {i+1}')
                    distance = activity.get('distance', 0) / 1000  # Convert to km
                    moving_time = activity.get('moving_time', 0) / 3600  # Convert to hours
                    avg_speed = (distance / moving_time) if moving_time > 0 else 0
                    
                    st.markdown(f"""
                    **{name}**  
                    📏 {distance:.1f} km • ⏱️ {moving_time:.1f}h • 🏃 {avg_speed:.1f} km/h
                    """)
    
    def _format_time_ago(self, timestamp: str) -> str:
        """Format timestamp as 'X days ago' string."""
        try:
            activity_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - activity_date.replace(tzinfo=None)
            days = delta.days
            
            if days == 0:
                return "Today"
            elif days == 1:
                return "Yesterday"
            else:
                return f"{days} days ago"
        except:
            return "Recently"