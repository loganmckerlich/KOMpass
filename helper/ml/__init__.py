"""
Machine Learning Module for KOMpass

This module provides ML-based speed prediction capabilities including:
- Model training from rider and route data
- Speed prediction for different effort levels
- Model persistence and retraining
- Model performance metrics and transparency
"""

from .speed_predictor import SpeedPredictor
from .model_trainer import ModelTrainer
from .model_manager import ModelManager

__all__ = ['SpeedPredictor', 'ModelTrainer', 'ModelManager']