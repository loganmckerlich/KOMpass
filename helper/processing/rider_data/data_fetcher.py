"""
Rider Data Fetcher - Handles data collection from Strava API.

This module is responsible for fetching raw data from Strava including:
- Basic athlete information
- Activity statistics and power records
- Heart rate and power zones
- Recent activities for analysis
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class RiderDataFetcher:
    """Handles fetching rider data from Strava API."""
    
    def __init__(self, oauth_client):
        """Initialize the data fetcher with OAuth client."""
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
            
            logger.info(f"Successfully fetched rider data with {len(rider_data['recent_activities'])} activities")
            
        except Exception as e:
            logger.error(f"Error fetching rider data: {e}")
            raise
        
        log_function_exit(logger, "fetch_comprehensive_rider_data")
        return rider_data
    
    def _fetch_recent_activities_comprehensive(self, access_token: str, days_back: int = 90) -> List[Dict]:
        """
        Fetch recent activities with comprehensive data for analysis.
        
        Args:
            access_token: Valid Strava access token
            days_back: Number of days to look back for activities
            
        Returns:
            List of activity dictionaries with detailed metrics
        """
        log_function_entry(logger, "_fetch_recent_activities_comprehensive")
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Fetch activities from API
            activities = self.oauth_client.get_activities(
                access_token,
                after=int(start_date.timestamp()),
                before=int(end_date.timestamp()),
                per_page=200  # Get more activities for better analysis
            )
            
            # Filter to cycling activities only
            cycling_activities = [
                activity for activity in activities 
                if activity.get('type') in ['Ride', 'VirtualRide', 'EBikeRide']
            ]
            
            logger.info(f"Fetched {len(cycling_activities)} cycling activities from last {days_back} days")
            
            log_function_exit(logger, "_fetch_recent_activities_comprehensive")
            return cycling_activities
            
        except Exception as e:
            logger.error(f"Error fetching recent activities: {e}")
            log_function_exit(logger, "_fetch_recent_activities_comprehensive")
            raise