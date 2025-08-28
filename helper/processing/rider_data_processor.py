"""
Rider Data Processor - Handles comprehensive Strava rider fitness data collection and analysis.

This module coordinates all rider data operations using specialized components:
- Data fetching from Strava API
- Fitness metrics and power analysis
- Data validation and storage
- Feature engineering for ML applications

Note: This module has been refactored into smaller, focused components in the rider_data/ subdirectory.
"""

from .rider_data import RiderDataProcessor as NewRiderDataProcessor
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class RiderDataProcessor:
    """Legacy wrapper for the refactored rider data processor."""
    
    def __init__(self, oauth_client):
        """
        Initialize rider data processor.
        
        Args:
            oauth_client: StravaOAuth instance for API calls
        """
        logger.info("Initializing refactored RiderDataProcessor")
        self._processor = NewRiderDataProcessor(oauth_client)
    
    def __getattr__(self, name):
        """Delegate all method calls to the new processor for backwards compatibility."""
        return getattr(self._processor, name)