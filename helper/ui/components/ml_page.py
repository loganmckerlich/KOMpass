"""
ML Page Component - Provides machine learning functionality interface.

This component handles:
- Speed prediction interface
- Model training interface
- Model transparency and information display
- Integration with route upload workflow
"""

import streamlit as st
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

from ...ml.model_manager import ModelManager
from ...config.logging_config import get_logger, log_function_entry, log_function_exit
from ...auth.auth_manager import get_auth_manager

logger = get_logger(__name__)


class MLPage:
    """Handles machine learning page rendering and functionality."""
    
    def __init__(self):
        """Initialize ML page component."""
        log_function_entry(logger, "__init__")
        self.model_manager = ModelManager()
        self.auth_manager = get_auth_manager()
        log_function_exit(logger, "__init__")
    
    def render_ml_page(self):
        """Render the main ML page."""
        log_function_entry(logger, "render_ml_page")
        
        st.markdown("# 🤖 Machine Learning Speed Predictions")
        st.markdown("Use AI to predict your speed on any route based on your fitness profile and route characteristics.")
        
        # Check authentication
        if not self.auth_manager.is_authenticated():
            st.info("🔒 Please log in with Strava to access ML predictions and personalized training.")
            self._render_demo_section()
            return
        
        # Get rider data
        rider_data = st.session_state.get("rider_fitness_data")
        if not rider_data:
            st.warning("⚠️ No rider fitness data available. Please ensure your Strava data has been loaded.")
            self._render_demo_section()
            return
        
        # Main ML interface
        tab1, tab2, tab3 = st.tabs(["🎯 Speed Predictions", "🔧 Model Training", "📊 Model Info"])
        
        with tab1:
            self._render_prediction_tab(rider_data)
        
        with tab2:
            self._render_training_tab()
        
        with tab3:
            self._render_model_info_tab()
        
        log_function_exit(logger, "render_ml_page")
    
    def _render_prediction_tab(self, rider_data: Dict[str, Any]):
        """Render the speed prediction interface."""
        st.markdown("## 🎯 Route Speed Predictions")
        st.markdown("Get AI-powered speed predictions for your routes at different effort levels.")
        
        # Route selection options
        col1, col2 = st.columns([2, 1])
        
        with col1:
            prediction_method = st.radio(
                "Choose prediction method:",
                ["Upload new route", "Use saved route", "Quick route parameters"],
                horizontal=True
            )
        
        with col2:
            effort_levels = st.multiselect(
                "Effort levels to predict:",
                ["zone2", "threshold"],
                default=["zone2", "threshold"]
            )
        
        route_data = None
        
        if prediction_method == "Upload new route":
            route_data = self._handle_route_upload()
        
        elif prediction_method == "Use saved route":
            route_data = self._handle_saved_route_selection()
        
        elif prediction_method == "Quick route parameters":
            route_data = self._handle_quick_route_input()
        
        # Generate predictions if we have route data
        if route_data and effort_levels:
            if st.button("🚀 Generate Speed Predictions", type="primary"):
                with st.spinner("Generating AI predictions..."):
                    predictions = self.model_manager.predict_route_speed(
                        rider_data, route_data, effort_levels
                    )
                    self._display_predictions(predictions, route_data)
    
    def _render_training_tab(self, ):
        """Render the model training interface."""
        st.markdown("## 🔧 Model Training")
        st.markdown("Train personalized AI models using your ride history.")
        
        # Get current user ID
        athlete_info = st.session_state.get("athlete_info", {})
        user_id = str(athlete_info.get("id", "unknown"))
        
        if user_id == "unknown":
            st.error("Unable to identify user for training. Please ensure you're logged in.")
            return
        
        # Check training status
        training_need = self.model_manager.check_training_need(user_id)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Training Status")
            
            if training_need.get('training_in_progress', False):
                st.info("🔄 Model training is currently in progress...")
            elif training_need.get('needs_training', False):
                st.warning("📈 Model training is recommended")
                for reason in training_need.get('reasons', []):
                    st.write(f"• {reason}")
            else:
                st.success("✅ Models are up to date")
            
            # Training statistics
            data_count = training_need.get('user_data_count', {})
            st.metric("Available fitness records", data_count.get('fitness_files', 0))
            st.metric("Available route records", data_count.get('route_files', 0))
        
        with col2:
            st.markdown("### Training Controls")
            
            if not training_need.get('training_in_progress', False):
                if st.button("🚀 Start Model Training", type="primary"):
                    self._initiate_training(user_id)
                
                if training_need.get('last_training'):
                    st.write(f"Last training: {training_need['last_training']}")
                else:
                    st.write("No previous training found")
            
            # Training options
            st.markdown("### Training Options")
            async_training = st.checkbox("Run training in background", value=True, 
                                       help="Allows you to continue using the app while training")
            
    def _render_model_info_tab(self):
        """Render model transparency and information."""
        st.markdown("## 📊 Model Information & Transparency")
        st.markdown("Learn about the AI models powering your speed predictions.")
        
        try:
            transparency_info = self.model_manager.get_model_transparency_info()
            
            # Model Architecture
            st.markdown("### 🏗️ Model Architecture")
            arch_info = transparency_info.get('model_architecture', {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Model Type:** {arch_info.get('type', 'N/A')}")
                st.write(f"**Features Used:** {arch_info.get('feature_count', 0)}")
                st.write(f"**Preprocessing:** {arch_info.get('preprocessing', 'N/A')}")
            
            with col2:
                training_info = transparency_info.get('training_info', {})
                st.write(f"**Models Available:** {training_info.get('total_models', 0)}")
                st.write(f"**Last Training:** {training_info.get('last_training', 'Never')}")
            
            # Feature details
            with st.expander("📝 Model Features (Click to expand)"):
                features = arch_info.get('features', [])
                if features:
                    feature_df = pd.DataFrame({
                        'Feature': features,
                        'Category': ['Rider'] * 6 + ['Route'] * 6
                    })
                    st.dataframe(feature_df, use_container_width=True)
            
            # Model Performance
            st.markdown("### 📈 Model Performance")
            performance = transparency_info.get('model_performance', {})
            
            if performance:
                perf_data = []
                for model_name, metrics in performance.items():
                    perf_data.append({
                        'Effort Level': model_name.title(),
                        'Accuracy (R²)': f"{metrics.get('r2_score', 0):.3f}",
                        'Average Error (km/h)': f"{metrics.get('mean_absolute_error_kmh', 0):.2f}",
                        'Model Type': metrics.get('model_type', 'N/A'),
                        'Training Samples': metrics.get('training_samples', 0),
                        'Confidence': f"{metrics.get('confidence', 0):.2f}"
                    })
                
                if perf_data:
                    perf_df = pd.DataFrame(perf_data)
                    st.dataframe(perf_df, use_container_width=True)
            else:
                st.info("No trained models available yet. Train models to see performance metrics.")
            
            # Prediction Methodology
            with st.expander("🔬 Prediction Methodology (Click to expand)"):
                methodology = transparency_info.get('prediction_methodology', {})
                st.markdown(f"**ML Prediction:** {methodology.get('ml_prediction', 'N/A')}")
                st.markdown(f"**Fallback Method:** {methodology.get('fallback_prediction', 'N/A')}")
                st.markdown(f"**Confidence Scoring:** {methodology.get('confidence_scoring', 'N/A')}")
        
        except Exception as e:
            logger.error(f"Error rendering model info: {e}")
            st.error("Failed to load model information. Please try again.")
    
    def _render_demo_section(self):
        """Render demo section for unauthenticated users."""
        st.markdown("## 🎮 Demo: Speed Prediction")
        st.markdown("See how AI speed prediction works with sample data.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Sample Rider")
            st.write("• FTP: 250W")
            st.write("• Weight: 75kg") 
            st.write("• Experience: 3 years")
            st.write("• Training: 8 hours/week")
        
        with col2:
            st.markdown("### Sample Route")
            distance = st.slider("Distance (km)", 20, 150, 80)
            elevation = st.slider("Elevation gain (m)", 0, 2000, 800)
            
        if st.button("🎯 Generate Demo Prediction"):
            # Create demo data
            demo_rider = {
                'performance_features': {'estimated_ftp': 250, 'weighted_power_avg': 220},
                'basic_features': {'weight_kg': 75},
                'training_features': {'hours_per_week': 8},
                'composite_scores': {'overall_fitness_score': 75}
            }
            
            demo_route = {
                'analysis': {
                    'distance_km': distance,
                    'total_elevation_gain': elevation,
                    'avg_gradient_percent': elevation / (distance * 10),
                    'max_gradient_percent': elevation / (distance * 5),
                    'elevation_variability': elevation * 0.3,
                    'power_analysis': {'estimated_power_requirement': 240}
                }
            }
            
            predictions = self.model_manager.predict_route_speed(demo_rider, demo_route)
            self._display_predictions(predictions, demo_route, is_demo=True)
    
    def _handle_route_upload(self) -> Optional[Dict[str, Any]]:
        """Handle route file upload for prediction."""
        uploaded_file = st.file_uploader(
            "Upload GPX file",
            type=['gpx'],
            help="Upload a GPX file to get speed predictions"
        )
        
        if uploaded_file is not None:
            # Process the uploaded route
            # For now, return a placeholder - in real implementation,
            # this would use the route processor
            st.success(f"Route uploaded: {uploaded_file.name}")
            return {
                'filename': uploaded_file.name,
                'analysis': {
                    'distance_km': 75,  # Placeholder
                    'total_elevation_gain': 900,
                    'avg_gradient_percent': 1.2,
                    'max_gradient_percent': 8.5,
                    'elevation_variability': 200,
                    'power_analysis': {'estimated_power_requirement': 230}
                }
            }
        
        return None
    
    def _handle_saved_route_selection(self) -> Optional[Dict[str, Any]]:
        """Handle selection of saved route."""
        st.info("Saved route selection - Feature coming soon!")
        return None
    
    def _handle_quick_route_input(self) -> Optional[Dict[str, Any]]:
        """Handle quick route parameter input."""
        st.markdown("### Quick Route Setup")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            distance = st.number_input("Distance (km)", min_value=5, max_value=300, value=75)
        
        with col2:
            elevation = st.number_input("Elevation gain (m)", min_value=0, max_value=5000, value=800)
        
        with col3:
            difficulty = st.selectbox("Route type", ["Flat", "Rolling", "Hilly", "Mountainous"])
        
        # Calculate route characteristics based on inputs
        if difficulty == "Flat":
            avg_gradient = 0.5
            max_gradient = 3
        elif difficulty == "Rolling":
            avg_gradient = 1.5
            max_gradient = 6
        elif difficulty == "Hilly":
            avg_gradient = 3.0
            max_gradient = 10
        else:  # Mountainous
            avg_gradient = 5.0
            max_gradient = 15
        
        return {
            'filename': f"Quick Route ({distance}km, {elevation}m)",
            'analysis': {
                'distance_km': distance,
                'total_elevation_gain': elevation,
                'avg_gradient_percent': avg_gradient,
                'max_gradient_percent': max_gradient,
                'elevation_variability': elevation * 0.4,
                'power_analysis': {'estimated_power_requirement': 200 + elevation / 10}
            }
        }
    
    def _display_predictions(self, predictions: Dict[str, Any], route_data: Dict[str, Any], is_demo: bool = False):
        """Display speed prediction results."""
        st.markdown("### 🎯 Prediction Results")
        
        if 'error' in predictions:
            st.error(f"Prediction failed: {predictions['error']}")
            return
        
        # Route summary
        analysis = route_data.get('analysis', {})
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Distance", f"{analysis.get('distance_km', 0):.1f} km")
        with col2:
            st.metric("Elevation Gain", f"{analysis.get('total_elevation_gain', 0):.0f} m")
        with col3:
            st.metric("Avg Gradient", f"{analysis.get('avg_gradient_percent', 0):.1f}%")
        with col4:
            st.metric("Max Gradient", f"{analysis.get('max_gradient_percent', 0):.1f}%")
        
        # Speed predictions
        st.markdown("### Speed & Time Predictions")
        
        prediction_data = []
        for effort_level, prediction in predictions.items():
            if effort_level.startswith('_'):  # Skip metadata
                continue
            
            speed = prediction.get('speed_kmh', 0)
            confidence = prediction.get('confidence', 0)
            method = prediction.get('method', 'unknown')
            
            # Calculate time
            distance = analysis.get('distance_km', 0)
            time_hours = distance / speed if speed > 0 else 0
            time_str = f"{int(time_hours)}:{int((time_hours % 1) * 60):02d}"
            
            prediction_data.append({
                'Effort Level': effort_level.replace('zone2', 'Zone 2 (Endurance)').replace('threshold', 'Threshold'),
                'Predicted Speed': f"{speed:.1f} km/h",
                'Estimated Time': time_str,
                'Confidence': f"{confidence:.1%}",
                'Method': method.replace('_', ' ').title()
            })
        
        if prediction_data:
            pred_df = pd.DataFrame(prediction_data)
            st.dataframe(pred_df, use_container_width=True)
        
        # Additional insights
        metadata = predictions.get('_metadata', {})
        if metadata.get('model_info', {}).get('has_ml_models', False):
            st.success("✅ Predictions generated using trained AI models")
        else:
            st.info("ℹ️ Predictions generated using physics-based calculations (no trained models yet)")
        
        if is_demo:
            st.info("🎮 This is a demo prediction. Log in with Strava for personalized predictions based on your actual fitness data.")
    
    def _initiate_training(self, user_id: str):
        """Initiate model training process."""
        try:
            with st.spinner("Initiating model training..."):
                result = self.model_manager.initiate_model_training(user_id, async_training=True)
            
            if result.get('status') == 'training_initiated':
                st.success("🚀 Model training started! Training will continue in the background.")
                st.info("You can continue using the app while training completes. Check back in a few minutes.")
            elif result.get('status') == 'insufficient_data':
                st.warning(f"⚠️ {result.get('message', 'Insufficient data for training')}")
                st.info("Upload more routes or ensure your Strava data is properly synced to enable training.")
            else:
                st.error(f"Training failed: {result.get('error', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error initiating training: {e}")
            st.error("Failed to start training. Please try again.")