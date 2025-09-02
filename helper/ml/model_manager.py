"""
Model Manager - Coordinates ML operations for KOMpass.

This module provides high-level coordination of ML operations including:
- Model lifecycle management
- Training coordination and scheduling
- Model performance monitoring
- Integration with the main application
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import threading

from .speed_predictor import SpeedPredictor
from .model_trainer import ModelTrainer
from ..config.logging_config import get_logger, log_function_entry, log_function_exit
from ..storage.storage_manager import get_storage_manager

logger = get_logger(__name__)


class ModelManager:
    """High-level coordinator for ML operations."""
    
    def __init__(self):
        """Initialize the model manager."""
        log_function_entry(logger, "__init__")
        
        self.predictor = SpeedPredictor()
        self.trainer = ModelTrainer()
        self.storage_manager = get_storage_manager()
        
        # Track training state
        self._training_in_progress = False
        self._last_training_check = None
        
        log_function_exit(logger, "__init__")
    
    def predict_route_speed(self, rider_data: Dict[str, Any], route_data: Dict[str, Any], 
                           effort_levels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Predict speeds for a route using rider and route data.
        
        Args:
            rider_data: Rider fitness and characteristics data
            route_data: Route analysis data
            effort_levels: List of effort levels to predict (default: ["zone2", "threshold"])
            
        Returns:
            Dictionary containing speed predictions for each effort level
        """
        log_function_entry(logger, "predict_route_speed")
        
        if effort_levels is None:
            effort_levels = ["zone2", "threshold"]
        
        try:
            # Extract rider features
            rider_features = self._extract_rider_features(rider_data)
            
            # Extract route features
            route_features = self._extract_route_features(route_data)
            
            # Check if automatic training is needed
            user_id = rider_data.get('user_id', 'anonymous')
            if user_id != 'anonymous':
                self._maybe_auto_train(user_id)
            
            # Get predictions for each effort level
            predictions = {}
            for effort_level in effort_levels:
                prediction = self.predictor.predict_speed(rider_features, route_features, effort_level)
                predictions[effort_level] = prediction
            
            # Add overall metadata
            predictions['_metadata'] = {
                'prediction_timestamp': datetime.now().isoformat(),
                'rider_id': rider_data.get('user_id', 'anonymous'),
                'route_name': route_data.get('filename', 'unknown'),
                'model_info': self.predictor.get_model_info()
            }
            
            logger.info(f"Generated speed predictions for {len(effort_levels)} effort levels")
            
        except Exception as e:
            logger.error(f"Error in route speed prediction: {e}")
            predictions = {
                'error': str(e),
                '_metadata': {
                    'prediction_timestamp': datetime.now().isoformat(),
                    'status': 'failed'
                }
            }
        
        log_function_exit(logger, "predict_route_speed")
        return predictions
    
    def initiate_model_training(self, user_id: str, async_training: bool = True) -> Dict[str, Any]:
        """
        Initiate model training for a user.
        
        Args:
            user_id: User identifier
            async_training: Whether to run training asynchronously
            
        Returns:
            Dictionary containing training initiation status
        """
        log_function_entry(logger, "initiate_model_training")
        
        if self._training_in_progress:
            return {
                'status': 'training_already_in_progress',
                'message': 'Model training is already running',
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            if async_training:
                # Start training in background thread
                training_thread = threading.Thread(
                    target=self._run_training_process,
                    args=(user_id,),
                    daemon=True
                )
                training_thread.start()
                
                result = {
                    'status': 'training_initiated',
                    'message': 'Model training started in background',
                    'async': True,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                # Run training synchronously
                result = self._run_training_process(user_id)
                result['async'] = False
            
        except Exception as e:
            logger.error(f"Error initiating model training: {e}")
            result = {
                'status': 'training_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        
        log_function_exit(logger, "initiate_model_training")
        return result
    
    def check_training_need(self, user_id: str) -> Dict[str, Any]:
        """
        Check if model training is needed for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing training need assessment
        """
        try:
            # Check when models were last trained
            training_status = self.trainer.get_training_status()
            last_training = training_status.get('last_training')
            
            # Check user data freshness
            user_fitness_files = self.storage_manager.list_user_data(user_id, 'fitness')
            user_route_files = self.storage_manager.list_user_data(user_id, 'routes')
            
            needs_training = False
            reasons = []
            
            # Check if no models exist
            if not training_status.get('models'):
                needs_training = True
                reasons.append('No trained models found')
            
            # Check if models are old (>30 days)
            if last_training:
                try:
                    last_training_date = datetime.fromisoformat(last_training)
                    if (datetime.now() - last_training_date) > timedelta(days=30):
                        needs_training = True
                        reasons.append('Models are older than 30 days')
                except:
                    pass
            
            # Check if user has new data
            if len(user_fitness_files) > 0 or len(user_route_files) > 5:
                if not last_training or len(user_route_files) > 10:
                    needs_training = True
                    reasons.append('Sufficient new user data available')
            
            return {
                'needs_training': needs_training,
                'reasons': reasons,
                'last_training': last_training,
                'user_data_count': {
                    'fitness_files': len(user_fitness_files),
                    'route_files': len(user_route_files)
                },
                'training_in_progress': self._training_in_progress
            }
            
        except Exception as e:
            logger.error(f"Error checking training need: {e}")
            return {
                'needs_training': True,
                'reasons': ['Error checking training status'],
                'error': str(e)
            }
    
    def get_model_transparency_info(self) -> Dict[str, Any]:
        """
        Get model transparency information including architecture and performance.
        
        Returns:
            Dictionary containing model transparency information
        """
        try:
            model_info = self.predictor.get_model_info()
            training_status = self.trainer.get_training_status()
            
            transparency_info = {
                'model_architecture': {
                    'type': 'Ensemble Learning (Random Forest + Gradient Boosting)',
                    'feature_count': 12,
                    'features': [
                        'Rider FTP (Functional Threshold Power)',
                        'Rider Weight',
                        'Experience Years',
                        'Recent Average Power',
                        'Training Hours per Week',
                        'Overall Fitness Score',
                        'Route Distance',
                        'Total Elevation Gain',
                        'Average Gradient',
                        'Maximum Gradient',
                        'Elevation Variability',
                        'Estimated Power Requirement'
                    ],
                    'target_variables': ['Zone 2 Speed', 'Threshold Speed'],
                    'preprocessing': 'StandardScaler normalization'
                },
                'model_performance': {},
                'training_info': {
                    'last_training': training_status.get('last_training'),
                    'models_available': model_info.get('loaded_models', []),
                    'total_models': len(model_info.get('loaded_models', []))
                },
                'prediction_methodology': {
                    'ml_prediction': 'Uses trained models when available',
                    'fallback_prediction': 'Physics-based calculations using power-to-weight ratio and route characteristics',
                    'confidence_scoring': 'Based on model validation performance and prediction consistency'
                }
            }
            
            # Add model-specific performance metrics
            for model_name, model_data in training_status.get('models', {}).items():
                if 'metrics' in model_data:
                    metrics = model_data['metrics']
                    transparency_info['model_performance'][model_name] = {
                        'r2_score': round(metrics.get('r2_score', 0), 3),
                        'mean_absolute_error_kmh': round(metrics.get('mae', 0), 2),
                        'model_type': metrics.get('model_type', 'unknown'),
                        'training_samples': metrics.get('training_samples', 0),
                        'confidence': round(model_data.get('confidence', 0), 2)
                    }
            
            return transparency_info
            
        except Exception as e:
            logger.error(f"Error getting model transparency info: {e}")
            return {
                'error': str(e),
                'model_architecture': {'type': 'Information unavailable'},
                'model_performance': {},
                'training_info': {}
            }
    
    def _extract_rider_features(self, rider_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized rider features from rider data."""
        features = {}
        
        try:
            # Handle different data structures
            if 'performance_features' in rider_data:
                perf = rider_data['performance_features']
                features['ftp'] = perf.get('estimated_ftp', 200)
                features['recent_avg_power'] = perf.get('weighted_power_avg', 180)
            
            if 'basic_features' in rider_data:
                basic = rider_data['basic_features']
                features['weight_kg'] = basic.get('weight_kg', 70)
                
                # Calculate experience
                if 'created_at' in basic:
                    try:
                        created_date = datetime.fromisoformat(basic['created_at'].replace('Z', '+00:00'))
                        features['experience_years'] = max(0.1, (datetime.now() - created_date.replace(tzinfo=None)).days / 365.25)
                    except:
                        features['experience_years'] = 1
            
            if 'training_features' in rider_data:
                training = rider_data['training_features']
                features['training_hours_per_week'] = training.get('hours_per_week', 5)
            
            if 'composite_scores' in rider_data:
                scores = rider_data['composite_scores']
                features['overall_fitness_score'] = scores.get('overall_fitness_score', 50)
            
            # Set defaults for missing values
            defaults = {
                'ftp': 200,
                'weight_kg': 70,
                'experience_years': 1,
                'recent_avg_power': 180,
                'training_hours_per_week': 5,
                'overall_fitness_score': 50
            }
            
            for key, default_value in defaults.items():
                if key not in features:
                    features[key] = default_value
            
        except Exception as e:
            logger.warning(f"Error extracting rider features: {e}")
            # Return safe defaults
            features = {
                'ftp': 200,
                'weight_kg': 70,
                'experience_years': 1,
                'recent_avg_power': 180,
                'training_hours_per_week': 5,
                'overall_fitness_score': 50
            }
        
        return features
    
    def _extract_route_features(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized route features from route data."""
        features = {}
        
        try:
            analysis = route_data.get('analysis', {})
            
            features.update({
                'distance_km': analysis.get('distance_km', 50),
                'total_elevation_gain': analysis.get('total_elevation_gain', 500),
                'avg_gradient_percent': analysis.get('avg_gradient_percent', 2),
                'max_gradient_percent': analysis.get('max_gradient_percent', 8),
                'elevation_variability': analysis.get('elevation_variability', 100),
                'estimated_power_requirement': analysis.get('power_analysis', {}).get('estimated_power_requirement', 220)
            })
            
        except Exception as e:
            logger.warning(f"Error extracting route features: {e}")
            # Return safe defaults
            features = {
                'distance_km': 50,
                'total_elevation_gain': 500,
                'avg_gradient_percent': 2,
                'max_gradient_percent': 8,
                'elevation_variability': 100,
                'estimated_power_requirement': 220
            }
        
        return features
    
    def _run_training_process(self, user_id: str) -> Dict[str, Any]:
        """Run the complete model training process."""
        self._training_in_progress = True
        
        try:
            logger.info(f"Starting model training process for user {user_id}")
            
            # Collect training data
            training_data = self.trainer.collect_training_data(user_id)
            
            if len(training_data.get('features', [])) < 10:
                return {
                    'status': 'insufficient_data',
                    'message': 'Need at least 10 training samples',
                    'sample_count': len(training_data.get('features', [])),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Train models
            training_results = self.trainer.train_models(training_data)
            
            # Reload predictor models
            self.predictor._load_models()
            
            result = {
                'status': 'training_completed',
                'message': f"Training completed for {len(training_results.get('models_trained', []))} models",
                'training_results': training_results,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("Model training process completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in training process: {e}")
            return {
                'status': 'training_failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            self._training_in_progress = False
    
    def _maybe_auto_train(self, user_id: str):
        """
        Check if automatic training should be initiated and start it if needed.
        
        Args:
            user_id: User identifier
        """
        try:
            # Skip if training is already in progress
            if self._training_in_progress:
                return
            
            # Check if we have any trained models
            model_info = self.predictor.get_model_info()
            if model_info.get('has_ml_models', False):
                # Models exist, no need for automatic training
                return
            
            # Check if training is needed and data is available
            training_need = self.check_training_need(user_id)
            if not training_need.get('needs_training', False):
                return
            
            # Check if we have sufficient data for training
            user_data_count = training_need.get('user_data_count', {})
            if user_data_count.get('route_files', 0) < 5:
                logger.info(f"Auto-training skipped: insufficient route data ({user_data_count.get('route_files', 0)} routes)")
                return
            
            # Initiate automatic training in background
            logger.info(f"Auto-training initiated for user {user_id}: no ML models found and sufficient data available")
            result = self.initiate_model_training(user_id, async_training=True)
            
            if result.get('status') == 'training_initiated':
                logger.info("Automatic model training started successfully")
            else:
                logger.warning(f"Automatic training failed to start: {result.get('error', 'unknown error')}")
                
        except Exception as e:
            logger.error(f"Error in automatic training check: {e}")

    def is_training_in_progress(self) -> bool:
        """Check if training is currently in progress."""
        return self._training_in_progress