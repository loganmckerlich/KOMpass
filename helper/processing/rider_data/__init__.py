"""
Rider Data Processor - Main orchestrator for rider data processing.

This module coordinates all rider data operations by using the specialized 
components for fetching, analysis, validation, and feature engineering.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime

from .data_fetcher import RiderDataFetcher
from .fitness_analyzer import FitnessMetricsAnalyzer
from .data_manager import RiderDataManager
from .feature_engineer import FeatureEngineer
from ...config.logging_config import get_logger, log_function_entry, log_function_exit


logger = get_logger(__name__)


class RiderDataProcessor:
    """Main orchestrator for comprehensive rider data processing."""
    
    def __init__(self, oauth_client):
        """
        Initialize the rider data processor with all components.
        
        Args:
            oauth_client: StravaOAuth instance for API calls
        """
        self.oauth_client = oauth_client
        self.data_fetcher = RiderDataFetcher(oauth_client)
        self.fitness_analyzer = FitnessMetricsAnalyzer()
        self.data_manager = RiderDataManager()
        self.feature_engineer = FeatureEngineer()
    
    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def fetch_comprehensive_rider_data(_self, access_token: str) -> Dict[str, Any]:
        """
        Fetch and process comprehensive rider data.
        
        Args:
            access_token: Valid Strava access token
            
        Returns:
            Dictionary containing all processed rider data
        """
        log_function_entry(logger, "fetch_comprehensive_rider_data")
        
        try:
            # 1. Fetch raw data
            logger.info("Fetching raw rider data from Strava")
            raw_data = _self.data_fetcher.fetch_comprehensive_rider_data(access_token)
            
            # 2. Calculate fitness metrics
            logger.info("Calculating fitness metrics")
            raw_data["fitness_metrics"] = _self.fitness_analyzer.calculate_fitness_metrics(
                raw_data.get("recent_activities", []), 
                raw_data.get("zones")
            )
            
            # 3. Analyze power metrics
            logger.info("Analyzing power metrics")
            raw_data["power_analysis"] = _self.fitness_analyzer.analyze_power_metrics(
                raw_data.get("stats"), 
                raw_data.get("recent_activities", [])
            )
            
            # 4. Analyze training load
            logger.info("Analyzing training load")
            raw_data["training_load"] = _self.fitness_analyzer.analyze_training_load(
                raw_data.get("recent_activities", [])
            )
            
            # 5. Estimate VO2 max
            logger.info("Estimating VO2 max")
            raw_data["vo2_analysis"] = _self.fitness_analyzer.estimate_vo2_max(
                raw_data.get("stats"),
                raw_data.get("recent_activities", [])
            )
            
            # 6. Add processing timestamp
            raw_data["processing_completed_at"] = datetime.now().isoformat()
            
            logger.info("Comprehensive rider data processing completed successfully")
            
        except Exception as e:
            logger.error(f"Error in comprehensive rider data processing: {e}")
            raw_data = {
                "error": str(e),
                "fetch_timestamp": datetime.now().isoformat()
            }
        
        log_function_exit(logger, "fetch_comprehensive_rider_data")
        return raw_data
    
    def get_feature_engineering_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features for machine learning from rider data.
        
        Args:
            rider_data: Complete rider data dictionary
            
        Returns:
            Dictionary containing engineered features
        """
        return self.feature_engineer.get_feature_engineering_data(rider_data)
    
    def validate_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate rider data completeness and quality.
        
        Args:
            rider_data: Rider data to validate
            
        Returns:
            Validation results
        """
        return self.data_manager.validate_rider_data(rider_data)
    
    def save_rider_data(self, rider_data: Dict[str, Any], user_id: str) -> bool:
        """
        Save rider data to storage.
        
        Args:
            rider_data: Rider data to save
            user_id: User identifier
            
        Returns:
            Success boolean
        """
        return self.data_manager.save_rider_data(rider_data, user_id)
    
    def load_rider_data(self, user_id: str, filename: str = None) -> Optional[Dict[str, Any]]:
        """
        Load rider data from storage.
        
        Args:
            user_id: User identifier
            filename: Specific filename (optional)
            
        Returns:
            Loaded rider data or None
        """
        return self.data_manager.load_rider_data(user_id, filename)
    
    def remove_pii_from_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove PII from rider data.
        
        Args:
            rider_data: Raw rider data
            
        Returns:
            Cleaned rider data
        """
        return self.data_manager.remove_pii_from_rider_data(rider_data)