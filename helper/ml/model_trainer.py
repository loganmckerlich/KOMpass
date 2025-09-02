"""
Model Trainer - Handles ML model training for speed prediction.

This module coordinates model training using rider and route data,
including data preparation, model selection, training, and validation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import joblib
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import warnings

from ..config.logging_config import get_logger, log_function_entry, log_function_exit
from ..storage.storage_manager import get_storage_manager

logger = get_logger(__name__)


class ModelTrainer:
    """Handles training of ML models for speed prediction."""
    
    def __init__(self):
        """Initialize the model trainer."""
        log_function_entry(logger, "__init__")
        
        self.storage_manager = get_storage_manager()
        self.scalers = {}
        self.training_data = {}
        self.models = {}
        
        # Suppress sklearn warnings for cleaner logs
        warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')
        
        log_function_exit(logger, "__init__")
    
    def collect_training_data(self, user_id: str) -> Dict[str, Any]:
        """
        Collect training data from user's ride history and fitness data.
        
        Args:
            user_id: User identifier for data collection
            
        Returns:
            Dictionary containing collected training data
        """
        log_function_entry(logger, "collect_training_data")
        
        training_data = {
            'features': [],
            'targets': {},
            'metadata': []
        }
        
        try:
            # Load user's fitness data history
            fitness_history = self.storage_manager.list_user_data(user_id, 'fitness')
            route_history = self.storage_manager.list_user_data(user_id, 'routes')
            
            logger.info(f"Found {len(fitness_history)} fitness records and {len(route_history)} routes for user {user_id}")
            
            # Process fitness data for rider features
            rider_features = self._extract_rider_features_from_history(user_id, fitness_history)
            
            # Process route data for route features and actual performance
            for route_file in route_history[:50]:  # Limit to recent 50 routes for performance
                try:
                    route_data = self.storage_manager.load_user_data(user_id, 'routes', route_file)
                    if route_data and 'analysis' in route_data:
                        # Extract features and actual performance
                        sample = self._create_training_sample(rider_features, route_data)
                        if sample:
                            training_data['features'].append(sample['features'])
                            for effort_level, speed in sample['targets'].items():
                                if effort_level not in training_data['targets']:
                                    training_data['targets'][effort_level] = []
                                training_data['targets'][effort_level].append(speed)
                            training_data['metadata'].append(sample['metadata'])
                            
                except Exception as e:
                    logger.warning(f"Failed to process route {route_file}: {e}")
            
            logger.info(f"Collected {len(training_data['features'])} training samples")
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
        
        log_function_exit(logger, "collect_training_data")
        return training_data
    
    def train_models(self, training_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train ML models for speed prediction.
        
        Args:
            training_data: Dictionary containing features and targets
            
        Returns:
            Dictionary containing training results and model metrics
        """
        log_function_entry(logger, "train_models")
        
        results = {
            'models_trained': [],
            'metrics': {},
            'training_timestamp': datetime.now().isoformat(),
            'sample_count': len(training_data.get('features', []))
        }
        
        if len(training_data.get('features', [])) < 10:
            logger.warning("Insufficient training data - need at least 10 samples")
            results['error'] = "Insufficient training data"
            return results
        
        try:
            X = np.array(training_data['features'])
            
            # Train models for each effort level
            for effort_level, targets in training_data['targets'].items():
                if len(targets) < 10:
                    logger.warning(f"Insufficient data for {effort_level} - skipping")
                    continue
                
                logger.info(f"Training model for {effort_level}")
                
                y = np.array(targets)
                model_result = self._train_single_model(X, y, effort_level)
                
                if model_result['success']:
                    self.models[effort_level] = model_result['model']
                    self.scalers[effort_level] = model_result['scaler']
                    results['models_trained'].append(effort_level)
                    results['metrics'][effort_level] = model_result['metrics']
                    
                    # Save model to storage
                    self._save_model(effort_level, model_result['model'], model_result['scaler'])
        
        except Exception as e:
            logger.error(f"Error in model training: {e}")
            results['error'] = str(e)
        
        # Save training metadata
        self._save_training_metadata(results)
        
        log_function_exit(logger, "train_models")
        return results
    
    def _extract_rider_features_from_history(self, user_id: str, fitness_history: List[str]) -> Dict[str, Any]:
        """Extract rider features from fitness data history."""
        features = {
            'ftp': 200,
            'weight_kg': 70,
            'experience_years': 1,
            'recent_avg_power': 180,
            'training_hours_per_week': 5,
            'overall_fitness_score': 50
        }
        
        try:
            # Load most recent fitness data
            if fitness_history:
                latest_fitness = self.storage_manager.load_user_data(user_id, 'fitness', fitness_history[0])
                if latest_fitness:
                    # Extract key metrics from fitness data
                    performance_features = latest_fitness.get('performance_features', {})
                    training_features = latest_fitness.get('training_features', {})
                    basic_features = latest_fitness.get('basic_features', {})
                    
                    features.update({
                        'ftp': performance_features.get('estimated_ftp', 200),
                        'weight_kg': basic_features.get('weight_kg', 70),
                        'recent_avg_power': performance_features.get('weighted_power_avg', 180),
                        'training_hours_per_week': training_features.get('hours_per_week', 5),
                        'overall_fitness_score': latest_fitness.get('composite_scores', {}).get('overall_fitness_score', 50)
                    })
                    
                    # Calculate experience years from account creation
                    if 'created_at' in basic_features:
                        try:
                            created_date = datetime.fromisoformat(basic_features['created_at'].replace('Z', '+00:00'))
                            experience_years = (datetime.now() - created_date.replace(tzinfo=None)).days / 365.25
                            features['experience_years'] = max(0.1, experience_years)
                        except:
                            pass
        
        except Exception as e:
            logger.warning(f"Error extracting rider features: {e}")
        
        return features
    
    def _create_training_sample(self, rider_features: Dict[str, Any], route_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a training sample from rider and route data."""
        try:
            analysis = route_data.get('analysis', {})
            
            # Extract route features
            route_features = {
                'distance_km': analysis.get('distance_km', 0),
                'total_elevation_gain': analysis.get('total_elevation_gain', 0),
                'avg_gradient_percent': analysis.get('avg_gradient_percent', 0),
                'max_gradient_percent': analysis.get('max_gradient_percent', 0),
                'elevation_variability': analysis.get('elevation_variability', 0),
                'estimated_power_requirement': analysis.get('power_analysis', {}).get('estimated_power_requirement', 200)
            }
            
            # Skip if route is too short or incomplete
            if route_features['distance_km'] < 5:
                return None
            
            # Combine features
            combined_features = []
            combined_features.extend([
                rider_features['ftp'],
                rider_features['weight_kg'],
                rider_features['experience_years'],
                rider_features['recent_avg_power'],
                rider_features['training_hours_per_week'],
                rider_features['overall_fitness_score']
            ])
            combined_features.extend([
                route_features['distance_km'],
                route_features['total_elevation_gain'],
                route_features['avg_gradient_percent'],
                route_features['max_gradient_percent'],
                route_features['elevation_variability'],
                route_features['estimated_power_requirement']
            ])
            
            # Extract target speeds (if available from actual performance data)
            targets = {}
            
            # For now, generate synthetic targets based on zone predictions
            # In a real scenario, this would come from actual ride performance data
            zone_speeds = analysis.get('zone_speed_predictions', {})
            if zone_speeds:
                for zone, speed_data in zone_speeds.items():
                    if 'speed_kmh' in speed_data:
                        effort_level = 'zone2' if 'zone_2' in zone.lower() else 'threshold'
                        targets[effort_level] = speed_data['speed_kmh']
            
            # If no zone speeds available, estimate from distance and elevation
            if not targets:
                base_speed = 35.0  # km/h
                gradient_factor = max(0.6, 1.0 - route_features['avg_gradient_percent'] / 100 * 1.5)
                estimated_speed = base_speed * gradient_factor
                targets = {
                    'zone2': estimated_speed * 0.85,
                    'threshold': estimated_speed * 1.0
                }
            
            return {
                'features': combined_features,
                'targets': targets,
                'metadata': {
                    'route_id': route_data.get('filename', 'unknown'),
                    'distance_km': route_features['distance_km'],
                    'elevation_gain': route_features['total_elevation_gain'],
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.warning(f"Error creating training sample: {e}")
            return None
    
    def _train_single_model(self, X: np.ndarray, y: np.ndarray, effort_level: str) -> Dict[str, Any]:
        """Train a single model for a specific effort level."""
        result = {'success': False}
        
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Try different models and select the best
            models_to_try = {
                'random_forest': RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1),
                'gradient_boosting': GradientBoostingRegressor(n_estimators=50, random_state=42),
                'linear': LinearRegression()
            }
            
            best_model = None
            best_score = -np.inf
            best_model_name = None
            
            for model_name, model in models_to_try.items():
                try:
                    # Cross-validation
                    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=min(5, len(X_train)//2), scoring='r2')
                    avg_score = np.mean(cv_scores)
                    
                    if avg_score > best_score:
                        best_score = avg_score
                        best_model = model
                        best_model_name = model_name
                        
                except Exception as e:
                    logger.warning(f"Model {model_name} failed: {e}")
            
            if best_model is None:
                raise Exception("No models could be trained successfully")
            
            # Train the best model on full training set
            best_model.fit(X_train_scaled, y_train)
            
            # Evaluate on test set
            y_pred = best_model.predict(X_test_scaled)
            
            metrics = {
                'r2_score': r2_score(y_test, y_pred),
                'mse': mean_squared_error(y_test, y_pred),
                'mae': mean_absolute_error(y_test, y_pred),
                'cv_score': best_score,
                'model_type': best_model_name,
                'training_samples': len(X_train),
                'test_samples': len(X_test)
            }
            
            result.update({
                'success': True,
                'model': best_model,
                'scaler': scaler,
                'metrics': metrics
            })
            
            logger.info(f"Model trained for {effort_level}: R² = {metrics['r2_score']:.3f}, MAE = {metrics['mae']:.2f} km/h")
            
        except Exception as e:
            logger.error(f"Error training model for {effort_level}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _save_model(self, effort_level: str, model: Any, scaler: Any):
        """Save trained model and scaler to storage."""
        try:
            # Save model
            model_filename = f"speed_model_{effort_level}.joblib"
            self.storage_manager.save_data(model, None, 'models', model_filename)
            
            # Save scaler
            scaler_filename = f"scaler_{effort_level}.joblib"
            self.storage_manager.save_data(scaler, None, 'models', scaler_filename)
            
            logger.info(f"Saved model and scaler for {effort_level}")
            
        except Exception as e:
            logger.error(f"Error saving model for {effort_level}: {e}")
    
    def _save_training_metadata(self, training_results: Dict[str, Any]):
        """Save training metadata."""
        try:
            metadata = {
                'last_training': training_results['training_timestamp'],
                'models': {}
            }
            
            for effort_level in training_results.get('models_trained', []):
                if effort_level in training_results.get('metrics', {}):
                    metadata['models'][effort_level] = {
                        'metrics': training_results['metrics'][effort_level],
                        'confidence': min(0.9, max(0.4, training_results['metrics'][effort_level].get('r2_score', 0.5)))
                    }
            
            self.storage_manager.save_data(metadata, None, 'models', 'model_metadata.json')
            logger.info("Saved training metadata")
            
        except Exception as e:
            logger.error(f"Error saving training metadata: {e}")
    
    def add_strava_activities_to_training_data(self, user_id: str, access_token: str, rider_features: Dict[str, Any], limit: int = 30) -> Dict[str, Any]:
        """
        Convert recent Strava activities to training data and store them.
        
        Args:
            user_id: User identifier
            access_token: Strava access token
            rider_features: Rider fitness features to pair with activities
            limit: Number of recent activities to process (default 30)
            
        Returns:
            Dictionary with processing results
        """
        log_function_entry(logger, "add_strava_activities_to_training_data")
        
        results = {
            'processed': 0,
            'skipped_duplicates': 0,
            'errors': 0,
            'activity_ids': [],
            'error_messages': []
        }
        
        try:
            # Import oauth client from auth manager
            from ..auth.auth_manager import get_auth_manager
            auth_manager = get_auth_manager()
            oauth_client = auth_manager.get_oauth_client()
            
            if not oauth_client:
                raise Exception("OAuth client not available")
            
            # Get recent activities
            logger.info(f"Fetching recent {limit} activities for training data")
            activities = oauth_client.get_activities(access_token, per_page=limit)
            
            # Filter cycling activities
            cycling_activities = [
                activity for activity in activities 
                if activity.get('type') in ['Ride', 'VirtualRide', 'EBikeRide']
            ]
            
            logger.info(f"Found {len(cycling_activities)} cycling activities to process")
            
            # Get list of already processed activity IDs to avoid duplicates
            processed_activities = self._get_processed_activity_ids(user_id)
            
            # Process each activity
            for activity in cycling_activities:
                activity_id = activity.get('id')
                if not activity_id:
                    continue
                    
                # Skip if already processed
                if str(activity_id) in processed_activities:
                    results['skipped_duplicates'] += 1
                    logger.debug(f"Skipping already processed activity {activity_id}")
                    continue
                
                try:
                    # Convert activity to training data
                    training_sample = self._convert_activity_to_training_data(
                        activity, access_token, oauth_client, rider_features
                    )
                    
                    if training_sample:
                        # Store training sample
                        success = self._store_training_sample(user_id, activity_id, training_sample)
                        if success:
                            results['processed'] += 1
                            results['activity_ids'].append(activity_id)
                            logger.info(f"Added activity {activity_id} to training data")
                        else:
                            results['errors'] += 1
                            results['error_messages'].append(f"Failed to store activity {activity_id}")
                    else:
                        results['errors'] += 1
                        results['error_messages'].append(f"Failed to convert activity {activity_id}")
                        
                except Exception as e:
                    results['errors'] += 1
                    error_msg = f"Error processing activity {activity_id}: {str(e)}"
                    results['error_messages'].append(error_msg)
                    logger.warning(error_msg)
            
            logger.info(f"Training data collection completed: {results['processed']} processed, "
                       f"{results['skipped_duplicates']} skipped, {results['errors']} errors")
                       
        except Exception as e:
            logger.error(f"Error in add_strava_activities_to_training_data: {e}")
            results['error_messages'].append(f"General error: {str(e)}")
        
        log_function_exit(logger, "add_strava_activities_to_training_data")
        return results
    
    def _get_processed_activity_ids(self, user_id: str) -> set:
        """Get set of already processed activity IDs for a user."""
        try:
            # Load training data metadata
            metadata_files = self.storage_manager.list_user_data(user_id, 'training_data')
            processed_ids = set()
            
            for file_info in metadata_files:
                filename = file_info.get('filename', '')
                if filename.startswith('activity_') and filename.endswith('.json'):
                    # Extract activity ID from filename: activity_{id}_training.json
                    try:
                        activity_id = filename.replace('activity_', '').replace('_training.json', '')
                        processed_ids.add(activity_id)
                    except:
                        pass
            
            logger.debug(f"Found {len(processed_ids)} already processed activities for user {user_id}")
            return processed_ids
            
        except Exception as e:
            logger.warning(f"Error getting processed activity IDs: {e}")
            return set()
    
    def _convert_activity_to_training_data(self, activity: Dict, access_token: str, oauth_client, rider_features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert a single Strava activity to training data format.
        
        Args:
            activity: Strava activity data
            access_token: Strava access token
            oauth_client: OAuth client for API calls
            rider_features: Rider fitness features
            
        Returns:
            Training data sample or None if conversion failed
        """
        try:
            activity_id = activity.get('id')
            
            # Get basic activity metrics
            distance_m = activity.get('distance', 0)  # meters
            moving_time_s = activity.get('moving_time', 0)  # seconds
            total_elevation_gain_m = activity.get('total_elevation_gain', 0)  # meters
            average_speed_ms = activity.get('average_speed', 0)  # m/s
            
            # Skip activities that are too short or lack basic data
            if distance_m < 5000 or moving_time_s < 300:  # Less than 5km or 5 minutes
                logger.debug(f"Skipping short activity {activity_id}: {distance_m}m, {moving_time_s}s")
                return None
            
            # Convert to standard units
            distance_km = distance_m / 1000
            moving_time_h = moving_time_s / 3600
            average_speed_kmh = (average_speed_ms * 3.6) if average_speed_ms > 0 else (distance_km / moving_time_h)
            
            # Calculate route features
            route_features = {
                'distance_km': distance_km,
                'total_elevation_gain': total_elevation_gain_m,
                'avg_gradient_percent': (total_elevation_gain_m / distance_m * 100) if distance_m > 0 else 0,
                'moving_time_hours': moving_time_h,
                'average_speed_kmh': average_speed_kmh
            }
            
            # Combine with rider features to create training sample
            combined_features = []
            combined_features.extend([
                rider_features.get('ftp', 200),
                rider_features.get('weight_kg', 70),
                rider_features.get('experience_years', 1),
                rider_features.get('recent_avg_power', 180),
                rider_features.get('training_hours_per_week', 5),
                rider_features.get('overall_fitness_score', 50)
            ])
            combined_features.extend([
                route_features['distance_km'],
                route_features['total_elevation_gain'],
                route_features['avg_gradient_percent'],
                moving_time_h,
                average_speed_kmh
            ])
            
            # Create training sample
            training_sample = {
                'features': combined_features,
                'targets': {
                    'actual_speed_kmh': average_speed_kmh,
                    'actual_time_hours': moving_time_h
                },
                'metadata': {
                    'activity_id': activity_id,
                    'activity_name': activity.get('name', f"Activity {activity_id}"),
                    'start_date': activity.get('start_date'),
                    'route_features': route_features,
                    'rider_features': rider_features,
                    'source': 'strava_activity',
                    'created_at': datetime.now().isoformat()
                }
            }
            
            logger.debug(f"Converted activity {activity_id} to training sample: {distance_km:.1f}km, {average_speed_kmh:.1f}km/h")
            return training_sample
            
        except Exception as e:
            logger.error(f"Error converting activity {activity.get('id', 'unknown')} to training data: {e}")
            return None
    
    def _store_training_sample(self, user_id: str, activity_id: int, training_sample: Dict[str, Any]) -> bool:
        """
        Store a training sample for a user.
        
        Args:
            user_id: User identifier
            activity_id: Strava activity ID
            training_sample: Training data sample
            
        Returns:
            Success boolean
        """
        try:
            filename = f"activity_{activity_id}_training.json"
            success = self.storage_manager.save_data(training_sample, user_id, 'training_data', filename)
            
            if success:
                logger.debug(f"Stored training sample for activity {activity_id}")
            else:
                logger.error(f"Failed to store training sample for activity {activity_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error storing training sample for activity {activity_id}: {e}")
            return False

    def get_training_status(self) -> Dict[str, Any]:
        """Get current training status and model information."""
        try:
            metadata = self.storage_manager.load_data(None, 'models', 'model_metadata.json')
            if metadata:
                return metadata
        except:
            pass
        
        return {
            'last_training': None,
            'models': {},
            'status': 'No models trained yet'
        }