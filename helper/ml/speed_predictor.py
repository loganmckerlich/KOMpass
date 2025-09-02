"""
Speed Predictor - Core ML inference component for KOMpass.

This module handles speed prediction using trained ML models for rider-route combinations.
Predicts speeds for different effort levels (Zone 2, Threshold) based on rider capabilities
and route characteristics.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import joblib
import os

from ..config.logging_config import get_logger, log_function_entry, log_function_exit
from ..storage.storage_manager import get_storage_manager

logger = get_logger(__name__)


class SpeedPredictor:
    """Handles ML-based speed prediction for rider-route combinations."""
    
    def __init__(self):
        """Initialize the speed predictor."""
        log_function_entry(logger, "__init__")
        
        self.storage_manager = get_storage_manager()
        self.models = {}
        self.model_metadata = {}
        self._load_models()
        
        log_function_exit(logger, "__init__")
    
    def _load_models(self):
        """Load trained models from storage."""
        log_function_entry(logger, "_load_models")
        
        try:
            # Try to load existing models
            # For models, user_id should be None (global data)
            try:
                model_files = self.storage_manager.list_user_data(None, 'models')
            except Exception:
                # Fallback to checking local directory directly
                import os
                models_dir = os.path.join(self.storage_manager.local_data_dir, 'models')
                if os.path.exists(models_dir):
                    model_files = [f for f in os.listdir(models_dir) if f.endswith('.joblib')]
                else:
                    model_files = []
            
            for model_file in model_files:
                if isinstance(model_file, str) and model_file.endswith('.joblib'):
                    filename = model_file
                elif isinstance(model_file, dict):
                    filename = model_file.get('filename', '')
                else:
                    continue
                
                if filename.endswith('.joblib') and 'speed_model_' in filename:
                    effort_level = filename.replace('.joblib', '').replace('speed_model_', '')
                    
                    try:
                        model_data = self.storage_manager.load_data(None, 'models', filename)
                        if model_data:
                            self.models[effort_level] = model_data
                            logger.info(f"Loaded model for effort level: {effort_level}")
                    except Exception as e:
                        logger.warning(f"Failed to load model {filename}: {e}")
            
            # Load model metadata if available
            try:
                metadata = self.storage_manager.load_data(None, 'models', 'model_metadata.json')
                if metadata:
                    self.model_metadata = metadata
                    logger.info("Loaded model metadata")
            except Exception as e:
                logger.warning(f"No model metadata found: {e}")
                
            if not self.models:
                logger.warning("No trained models found - predictions will use fallback calculations")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            
        log_function_exit(logger, "_load_models")
    
    def predict_speed(self, rider_features: Dict[str, Any], route_features: Dict[str, Any], 
                     effort_level: str = "zone2") -> Dict[str, Any]:
        """
        Predict speed for a given rider-route combination.
        
        Args:
            rider_features: Dictionary of rider characteristics and fitness metrics
            route_features: Dictionary of route characteristics (distance, elevation, etc.)
            effort_level: Target effort level ("zone2", "threshold", "max")
            
        Returns:
            Dictionary containing speed prediction and confidence metrics
        """
        log_function_entry(logger, "predict_speed")
        
        try:
            # Prepare feature vector
            feature_vector = self._prepare_feature_vector(rider_features, route_features)
            
            # Check if we have a trained model for this effort level
            if effort_level in self.models:
                # Use ML model prediction
                prediction = self._predict_with_model(feature_vector, effort_level)
            else:
                # Fall back to rule-based prediction
                prediction = self._predict_with_rules(rider_features, route_features, effort_level)
            
            # Add metadata
            prediction.update({
                'effort_level': effort_level,
                'prediction_timestamp': datetime.now().isoformat(),
                'model_used': effort_level in self.models,
                'feature_count': len(feature_vector) if isinstance(feature_vector, dict) else feature_vector.shape[0] if hasattr(feature_vector, 'shape') else 0
            })
            
            logger.info(f"Speed prediction completed for {effort_level}: {prediction.get('speed_kmh', 0):.1f} km/h")
            
        except Exception as e:
            logger.error(f"Error in speed prediction: {e}")
            prediction = {
                'speed_kmh': 25.0,  # Safe fallback
                'confidence': 0.1,
                'error': str(e),
                'effort_level': effort_level,
                'prediction_timestamp': datetime.now().isoformat(),
                'model_used': False
            }
        
        log_function_exit(logger, "predict_speed")
        return prediction
    
    def predict_multiple_efforts(self, rider_features: Dict[str, Any], route_features: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Predict speeds for multiple effort levels.
        
        Args:
            rider_features: Dictionary of rider characteristics
            route_features: Dictionary of route characteristics
            
        Returns:
            Dictionary mapping effort levels to prediction results
        """
        log_function_entry(logger, "predict_multiple_efforts")
        
        effort_levels = ["zone2", "threshold"]
        predictions = {}
        
        for effort_level in effort_levels:
            predictions[effort_level] = self.predict_speed(rider_features, route_features, effort_level)
        
        log_function_exit(logger, "predict_multiple_efforts")
        return predictions
    
    def _prepare_feature_vector(self, rider_features: Dict[str, Any], route_features: Dict[str, Any]) -> np.ndarray:
        """Prepare feature vector for ML model."""
        features = []
        
        # Rider features
        features.extend([
            rider_features.get('ftp', 200),
            rider_features.get('weight_kg', 70),
            rider_features.get('experience_years', 1),
            rider_features.get('recent_avg_power', 180),
            rider_features.get('training_hours_per_week', 5),
            rider_features.get('overall_fitness_score', 50)
        ])
        
        # Route features
        features.extend([
            route_features.get('distance_km', 50),
            route_features.get('total_elevation_gain', 500),
            route_features.get('avg_gradient_percent', 2),
            route_features.get('max_gradient_percent', 8),
            route_features.get('elevation_variability', 100),
            route_features.get('estimated_power_requirement', 220)
        ])
        
        return np.array(features).reshape(1, -1)
    
    def _predict_with_model(self, feature_vector: np.ndarray, effort_level: str) -> Dict[str, Any]:
        """Use trained ML model for prediction."""
        try:
            model = self.models[effort_level]
            speed_prediction = model.predict(feature_vector)[0]
            
            # Get prediction confidence if model supports it
            confidence = 0.8  # Default confidence
            if hasattr(model, 'predict_proba'):
                try:
                    # For regression, we'll estimate confidence based on training performance
                    confidence = self.model_metadata.get(effort_level, {}).get('confidence', 0.8)
                except:
                    pass
            
            return {
                'speed_kmh': max(15.0, min(60.0, float(speed_prediction))),  # Reasonable bounds
                'confidence': confidence,
                'method': 'ml_model'
            }
            
        except Exception as e:
            logger.error(f"ML model prediction failed: {e}")
            raise
    
    def _predict_with_rules(self, rider_features: Dict[str, Any], route_features: Dict[str, Any], 
                           effort_level: str) -> Dict[str, Any]:
        """Fallback rule-based speed prediction."""
        logger.info(f"Using rule-based prediction for {effort_level}")
        
        # Get rider FTP and weight
        ftp = rider_features.get('ftp', 200)
        weight_kg = rider_features.get('weight_kg', 70)
        
        # Calculate power-to-weight ratio
        power_to_weight = ftp / weight_kg
        
        # Route characteristics
        distance_km = route_features.get('distance_km', 50)
        elevation_gain = route_features.get('total_elevation_gain', 500)
        avg_gradient = route_features.get('avg_gradient_percent', 2)
        
        # Base speed calculation based on effort level
        if effort_level == "zone2":
            target_power = ftp * 0.75  # Zone 2 = ~75% FTP
            base_speed = 32.0  # Base speed for zone 2
        elif effort_level == "threshold":
            target_power = ftp * 1.0   # Threshold = 100% FTP
            base_speed = 40.0  # Base speed for threshold
        else:
            target_power = ftp * 0.85  # Default to tempo
            base_speed = 36.0
        
        # Adjust for route difficulty
        gradient_factor = max(0.5, 1.0 - (avg_gradient / 100) * 2)  # Reduce speed for climbing
        distance_factor = max(0.8, 1.0 - (distance_km - 50) / 200)  # Slight reduction for very long routes
        
        # Final speed calculation
        predicted_speed = base_speed * gradient_factor * distance_factor * (power_to_weight / 3.0)
        
        # Apply reasonable bounds
        predicted_speed = max(15.0, min(55.0, predicted_speed))
        
        return {
            'speed_kmh': predicted_speed,
            'confidence': 0.6,  # Lower confidence for rule-based
            'method': 'rule_based',
            'factors': {
                'gradient_factor': gradient_factor,
                'distance_factor': distance_factor,
                'power_to_weight': power_to_weight
            }
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            'loaded_models': list(self.models.keys()),
            'model_metadata': self.model_metadata,
            'has_ml_models': len(self.models) > 0,
            'fallback_available': True
        }