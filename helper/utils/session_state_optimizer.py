"""
Session State Optimizer for KOMpass
Provides utilities to manage and clean up session state efficiently.
"""

import streamlit as st
import sys
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class SessionStateOptimizer:
    """Manages session state cleanup and optimization."""
    
    # Define which keys should be preserved during cleanup
    ESSENTIAL_KEYS = {
        # Authentication (small, essential)
        'authenticated', 'access_token', 'refresh_token', 'expires_at',
        'athlete_info',  # Small athlete profile data
        
        # Keep only the latest analysis (not all timestamped versions)
        'latest_analysis_dataframe',
        'latest_weather_analysis',
        
        # Keep recent activities list (moderate size, useful)
        'recent_strava_activities',
        'saved_routes_list',
    }
    
    # Keys that should be limited in number (LRU-style)
    LIMITED_KEYS = {
        'route_data_': 2,        # Keep only 2 most recent route datasets
        'route_stats_': 2,       # Keep only 2 most recent route statistics  
        'strava_route_data_': 2, # Keep only 2 most recent Strava routes
        'strava_route_stats_': 2, # Keep only 2 most recent Strava stats
        'route_map_': 1,         # Keep only 1 most recent route map (maps are expensive)
    }
    
    @staticmethod
    def get_session_state_size() -> Dict[str, Any]:
        """Get information about session state memory usage."""
        try:
            total_keys = len(st.session_state.keys()) if hasattr(st.session_state, 'keys') else 0
            
            # Estimate sizes of different key categories
            large_objects = []
            medium_objects = []
            total_estimated_size = 0
            
            for key in st.session_state.keys():
                try:
                    obj = st.session_state[key]
                    # Rough size estimation
                    obj_size = sys.getsizeof(obj)
                    total_estimated_size += obj_size
                    
                    if obj_size > 1024 * 1024:  # > 1MB
                        large_objects.append((key, obj_size))
                    elif obj_size > 100 * 1024:  # > 100KB
                        medium_objects.append((key, obj_size))
                        
                except Exception as e:
                    logger.warning(f"Could not estimate size for key {key}: {e}")
                    
            return {
                'total_keys': total_keys,
                'estimated_total_size_mb': total_estimated_size / (1024 * 1024),
                'large_objects': large_objects,
                'medium_objects': medium_objects,
            }
            
        except Exception as e:
            logger.error(f"Error analyzing session state: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def cleanup_old_analysis_dataframes():
        """Remove old timestamped analysis dataframes, keep only latest."""
        removed_keys = []
        
        try:
            keys_to_remove = []
            for key in st.session_state.keys():
                # Remove old timestamped analysis dataframes (keep only latest_analysis_dataframe)
                if key.startswith('analysis_dataframe_') and key != 'latest_analysis_dataframe':
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                try:
                    del st.session_state[key]
                    removed_keys.append(key)
                    logger.debug(f"Removed old analysis dataframe: {key}")
                except Exception as e:
                    logger.warning(f"Could not remove key {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during analysis dataframe cleanup: {e}")
            
        return removed_keys
    
    @staticmethod
    def cleanup_large_objects():
        """Remove non-essential large objects from session state."""
        removed_keys = []
        
        try:
            keys_to_remove = []
            
            for key in st.session_state.keys():
                # Remove cached maps (they can be regenerated)
                if key.startswith('route_map_'):
                    keys_to_remove.append(key)
                
                # Remove old timestamped analysis dataframes
                elif key.startswith('analysis_dataframe_') and key != 'latest_analysis_dataframe':
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                try:
                    del st.session_state[key]
                    removed_keys.append(key)
                    logger.debug(f"Removed large object: {key}")
                except Exception as e:
                    logger.warning(f"Could not remove key {key}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during large object cleanup: {e}")
            
        return removed_keys
    
    @staticmethod  
    def apply_lru_limits():
        """Apply LRU-style limits to session state keys."""
        removed_keys = []
        
        try:
            for prefix, limit in SessionStateOptimizer.LIMITED_KEYS.items():
                # Find all keys with this prefix
                matching_keys = [k for k in st.session_state.keys() if k.startswith(prefix)]
                
                if len(matching_keys) > limit:
                    # Sort by key name (which often includes timestamps) and remove oldest
                    matching_keys.sort()
                    keys_to_remove = matching_keys[:-limit]  # Remove all but the last 'limit' items
                    
                    for key in keys_to_remove:
                        try:
                            del st.session_state[key]
                            removed_keys.append(key)
                            logger.debug(f"Removed old cached item: {key}")
                        except Exception as e:
                            logger.warning(f"Could not remove key {key}: {e}")
                            
        except Exception as e:
            logger.error(f"Error during LRU cleanup: {e}")
            
        return removed_keys
    
    @staticmethod
    def optimize_rider_fitness_data():
        """Optimize rider fitness data to store only essential metrics."""
        optimized = False
        
        try:
            rider_data = st.session_state.get('rider_fitness_data')
            if rider_data and isinstance(rider_data, dict):
                # Extract only essential fitness metrics
                essential_metrics = {}
                
                # Keep high-level summary data only
                if 'summary' in rider_data:
                    essential_metrics['summary'] = rider_data['summary']
                    
                # Keep recent performance trends (not full history)
                if 'recent_activities' in rider_data:
                    recent = rider_data['recent_activities']
                    if isinstance(recent, list) and len(recent) > 10:
                        # Keep only last 10 activities
                        essential_metrics['recent_activities'] = recent[-10:]
                    else:
                        essential_metrics['recent_activities'] = recent
                        
                # Keep current fitness metrics
                if 'current_fitness' in rider_data:
                    essential_metrics['current_fitness'] = rider_data['current_fitness']
                    
                # Replace the full data with essential metrics only
                st.session_state['rider_fitness_data'] = essential_metrics
                optimized = True
                logger.info("Optimized rider fitness data storage")
                
        except Exception as e:
            logger.error(f"Error optimizing rider fitness data: {e}")
            
        return optimized
    
    @staticmethod
    def full_cleanup():
        """Perform a comprehensive cleanup of session state."""
        logger.info("Starting comprehensive session state cleanup")
        
        results = {
            'analysis_dataframes_removed': SessionStateOptimizer.cleanup_old_analysis_dataframes(),
            'large_objects_removed': SessionStateOptimizer.cleanup_large_objects(),
            'lru_items_removed': SessionStateOptimizer.apply_lru_limits(),
            'rider_data_optimized': SessionStateOptimizer.optimize_rider_fitness_data(),
        }
        
        total_removed = (len(results['analysis_dataframes_removed']) + 
                        len(results['large_objects_removed']) + 
                        len(results['lru_items_removed']))
                        
        logger.info(f"Session state cleanup completed: {total_removed} items removed, "
                   f"rider data optimized: {results['rider_data_optimized']}")
        
        return results


def get_session_state_optimizer() -> SessionStateOptimizer:
    """Get the session state optimizer singleton."""
    return SessionStateOptimizer()