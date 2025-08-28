"""
Data Validator and Storage Manager - Handles rider data validation and persistence.

This module provides:
- Data validation and completeness checks
- PII removal for data privacy
- Storage and retrieval operations
- Data history management
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

from ...config.logging_config import get_logger, log_function_entry, log_function_exit
from ...storage.storage_manager import get_storage_manager


logger = get_logger(__name__)


class RiderDataManager:
    """Manages rider data validation, storage, and retrieval."""
    
    def __init__(self):
        """Initialize the data manager."""
        self.storage_manager = get_storage_manager()
    
    def validate_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate rider data completeness and quality.
        
        Args:
            rider_data: Raw rider data from API
            
        Returns:
            Dictionary containing validation results and cleaned data
        """
        log_function_entry(logger, "validate_rider_data")
        
        validation_result = {
            "is_valid": True,
            "completeness_score": 0.0,
            "missing_fields": [],
            "data_quality_issues": [],
            "validated_data": rider_data.copy()
        }
        
        try:
            # Check required top-level fields
            required_fields = ["basic_info", "stats", "zones", "recent_activities"]
            for field in required_fields:
                if field not in rider_data or rider_data[field] is None:
                    validation_result["missing_fields"].append(field)
            
            # Calculate completeness score
            validation_result["completeness_score"] = self._calculate_completeness_score(rider_data)
            
            # Check data quality
            quality_issues = self._check_data_quality(rider_data)
            validation_result["data_quality_issues"] = quality_issues
            
            # Mark as invalid if critical issues found
            if len(validation_result["missing_fields"]) > 2 or validation_result["completeness_score"] < 0.3:
                validation_result["is_valid"] = False
            
            logger.info(f"Data validation completed: {validation_result['completeness_score']:.2f} completeness")
            
        except Exception as e:
            logger.error(f"Error during data validation: {e}")
            validation_result["is_valid"] = False
            validation_result["data_quality_issues"].append(f"Validation error: {str(e)}")
        
        log_function_exit(logger, "validate_rider_data")
        return validation_result
    
    def remove_pii_from_rider_data(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove personally identifiable information from rider data.
        
        Args:
            rider_data: Raw rider data containing PII
            
        Returns:
            Cleaned rider data with PII removed/anonymized
        """
        log_function_entry(logger, "remove_pii_from_rider_data")
        
        cleaned_data = rider_data.copy()
        
        try:
            # Clean basic_info
            if "basic_info" in cleaned_data and cleaned_data["basic_info"]:
                basic_info = cleaned_data["basic_info"].copy()
                
                # Remove or hash sensitive fields
                pii_fields = ["firstname", "lastname", "email", "profile", "profile_medium"]
                for field in pii_fields:
                    if field in basic_info:
                        if field in ["firstname", "lastname"]:
                            # Replace with anonymized version
                            basic_info[field] = f"User_{hashlib.md5(str(basic_info[field]).encode()).hexdigest()[:8]}"
                        else:
                            # Remove completely
                            del basic_info[field]
                
                cleaned_data["basic_info"] = basic_info
            
            # Clean activity data
            if "recent_activities" in cleaned_data and cleaned_data["recent_activities"]:
                cleaned_activities = []
                for activity in cleaned_data["recent_activities"]:
                    cleaned_activity = activity.copy()
                    
                    # Remove location and route data
                    location_fields = ["start_latlng", "end_latlng", "map", "location_city", 
                                     "location_state", "location_country", "start_latitude", 
                                     "start_longitude", "end_latitude", "end_longitude"]
                    for field in location_fields:
                        if field in cleaned_activity:
                            del cleaned_activity[field]
                    
                    # Anonymize activity names that might contain personal info
                    if "name" in cleaned_activity:
                        cleaned_activity["name"] = f"Activity_{cleaned_activity.get('id', 'unknown')}"
                    
                    cleaned_activities.append(cleaned_activity)
                
                cleaned_data["recent_activities"] = cleaned_activities
            
            # Add anonymization timestamp
            cleaned_data["pii_removed_at"] = datetime.now().isoformat()
            
            logger.info("PII removal completed successfully")
            
        except Exception as e:
            logger.error(f"Error removing PII: {e}")
            # Return original data if cleaning fails
            cleaned_data = rider_data.copy()
            cleaned_data["pii_removal_error"] = str(e)
        
        log_function_exit(logger, "remove_pii_from_rider_data")
        return cleaned_data
    
    def save_rider_data(self, rider_data: Dict[str, Any], user_id: str) -> bool:
        """
        Save rider data to storage with automatic PII removal.
        
        Args:
            rider_data: Rider data to save
            user_id: Unique identifier for the user
            
        Returns:
            Boolean indicating success
        """
        log_function_entry(logger, "save_rider_data")
        
        try:
            # Remove PII before saving
            cleaned_data = self.remove_pii_from_rider_data(rider_data)
            
            # Add metadata
            cleaned_data["saved_at"] = datetime.now().isoformat()
            cleaned_data["user_id"] = user_id
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rider_data_{user_id}_{timestamp}.json"
            
            # Save to storage
            success = self.storage_manager.save_data(cleaned_data, filename, "rider_data")
            
            if success:
                logger.info(f"Rider data saved successfully: {filename}")
            else:
                logger.error(f"Failed to save rider data: {filename}")
            
            log_function_exit(logger, "save_rider_data")
            return success
            
        except Exception as e:
            logger.error(f"Error saving rider data: {e}")
            log_function_exit(logger, "save_rider_data")
            return False
    
    def load_rider_data(self, user_id: str, filename: str = None) -> Optional[Dict[str, Any]]:
        """
        Load rider data from storage.
        
        Args:
            user_id: User identifier
            filename: Specific filename to load (optional, loads latest if not specified)
            
        Returns:
            Loaded rider data or None if not found
        """
        log_function_entry(logger, "load_rider_data")
        
        try:
            if filename:
                # Load specific file
                data = self.storage_manager.load_data(filename, "rider_data")
            else:
                # Load latest file for user
                files = self.get_rider_data_history(user_id)
                if not files:
                    logger.info(f"No rider data found for user: {user_id}")
                    log_function_exit(logger, "load_rider_data")
                    return None
                
                # Get most recent file
                latest_file = max(files, key=lambda x: x.get("modified_date", ""))
                data = self.storage_manager.load_data(latest_file["filename"], "rider_data")
            
            if data:
                logger.info(f"Rider data loaded successfully for user: {user_id}")
            else:
                logger.warning(f"Failed to load rider data for user: {user_id}")
            
            log_function_exit(logger, "load_rider_data")
            return data
            
        except Exception as e:
            logger.error(f"Error loading rider data: {e}")
            log_function_exit(logger, "load_rider_data")
            return None
    
    def get_rider_data_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get history of saved rider data files for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of file metadata dictionaries
        """
        log_function_entry(logger, "get_rider_data_history")
        
        try:
            # List all files in rider_data directory
            all_files = self.storage_manager.list_files("rider_data")
            
            # Filter files for this user
            user_files = [
                file_info for file_info in all_files
                if file_info["filename"].startswith(f"rider_data_{user_id}_")
            ]
            
            # Sort by modification date (newest first)
            user_files.sort(key=lambda x: x.get("modified_date", ""), reverse=True)
            
            logger.info(f"Found {len(user_files)} rider data files for user: {user_id}")
            
            log_function_exit(logger, "get_rider_data_history")
            return user_files
            
        except Exception as e:
            logger.error(f"Error getting rider data history: {e}")
            log_function_exit(logger, "get_rider_data_history")
            return []
    
    def _calculate_completeness_score(self, rider_data: Dict[str, Any]) -> float:
        """Calculate data completeness score (0.0 to 1.0)."""
        total_fields = 0
        present_fields = 0
        
        # Check basic_info completeness
        if "basic_info" in rider_data and rider_data["basic_info"]:
            basic_fields = ["id", "username", "resource_state", "created_at", "updated_at"]
            total_fields += len(basic_fields)
            present_fields += sum(1 for field in basic_fields if field in rider_data["basic_info"])
        
        # Check stats completeness
        if "stats" in rider_data and rider_data["stats"]:
            total_fields += 1
            present_fields += 1
        
        # Check zones completeness
        if "zones" in rider_data and rider_data["zones"]:
            total_fields += 1
            present_fields += 1
        
        # Check activities completeness
        if "recent_activities" in rider_data:
            total_fields += 1
            if rider_data["recent_activities"] and len(rider_data["recent_activities"]) > 0:
                present_fields += 1
        
        # Check for processed metrics
        processed_fields = ["fitness_metrics", "power_analysis", "training_load"]
        for field in processed_fields:
            total_fields += 1
            if field in rider_data and rider_data[field]:
                present_fields += 1
        
        return present_fields / total_fields if total_fields > 0 else 0.0
    
    def _check_data_quality(self, rider_data: Dict[str, Any]) -> List[str]:
        """Check for data quality issues."""
        issues = []
        
        # Check if activities are recent
        if "recent_activities" in rider_data and rider_data["recent_activities"]:
            activities = rider_data["recent_activities"]
            if len(activities) < 5:
                issues.append("Limited activity data (< 5 activities)")
            
            # Check for data consistency
            power_activities = [a for a in activities if a.get("average_watts", 0) > 0]
            if len(power_activities) == 0:
                issues.append("No power data available in activities")
        
        # Check basic info consistency
        if "basic_info" in rider_data and rider_data["basic_info"]:
            basic_info = rider_data["basic_info"]
            if not basic_info.get("id"):
                issues.append("Missing athlete ID")
        
        return issues