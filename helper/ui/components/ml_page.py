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
        """Render the main ML page focused on speed predictions."""
        log_function_entry(logger, "render_ml_page")
        
        st.markdown("# 🎯 Speed Predictions")
        st.markdown("Get AI-powered speed predictions for your routes based on your personal fitness data and route characteristics.")
        
        # Check authentication (should always be true in new workflow, but double-check)
        if not self.auth_manager.is_authenticated():
            st.error("🔒 Authentication required. Please log in to access speed predictions.")
            return
        
        # Check for auto-training status and show feedback
        self._render_training_status()
        
        # Get rider data
        rider_data = st.session_state.get("rider_fitness_data")
        if not rider_data:
            st.warning("⚠️ Loading your fitness data...")
            st.info("💡 We're analyzing your recent Strava activities to personalize predictions.")
            return
        
        # Main prediction interface
        self._render_prediction_interface(rider_data)
        
        log_function_exit(logger, "render_ml_page")
    
    def _render_training_status(self):
        """Render training status notifications."""
        auto_training_status = st.session_state.get('auto_training_status')
        
        if auto_training_status:
            status = auto_training_status.get('status', '')
            message = auto_training_status.get('message', '')
            
            if status == 'training_started':
                st.success(f"🤖 {message}")
                if st.session_state.get('training_data_update', {}).get('processed', 0) > 0:
                    processed = st.session_state['training_data_update']['processed']
                    st.info(f"📊 Processed {processed} recent activities for training")
            
            elif status == 'training_not_needed':
                st.info(f"✅ {message}")
            
            elif status in ['training_failed', 'training_error']:
                st.warning(f"⚠️ {message}")
            
            # Training in progress check
            if self.model_manager.is_training_in_progress():
                st.info("🔄 Model training in progress... Predictions will improve once complete.")
    
    def _render_prediction_interface(self, rider_data: Dict[str, Any]):
        """Render the main prediction interface."""
        st.markdown("## 🗺️ Route Input")
        
        # Route input options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            input_method = st.radio(
                "How would you like to input your route?",
                [
                    "📁 Upload GPX file",
                    "🚴 Use saved Strava route",
                    "⚡ Quick route parameters"
                ],
                help="Choose your preferred method for route analysis"
            )
        
        with col2:
            if st.button("🔄 Refresh Models", help="Update prediction models with latest data"):
                self._refresh_models()
        
        # Handle different input methods
        route_data = None
        
        if input_method == "📁 Upload GPX file":
            route_data = self._handle_gpx_upload()
        
        elif input_method == "🚴 Use saved Strava route":
            route_data = self._handle_strava_route_selection()
        
        elif input_method == "⚡ Quick route parameters":
            route_data = self._handle_quick_parameters()
        
        # Show predictions if we have route data
        if route_data:
            st.markdown("---")
            self._render_predictions(route_data, rider_data)
    
    def _handle_gpx_upload(self) -> Optional[Dict[str, Any]]:
        """Handle GPX file upload for predictions."""
        uploaded_file = st.file_uploader(
            "Upload your route GPX file",
            type=['gpx'],
            help="Upload a GPX file to get personalized speed predictions"
        )
        
        if uploaded_file is not None:
            try:
                # Process the GPX file (placeholder - real implementation would use route processor)
                st.success(f"✅ Route uploaded: {uploaded_file.name}")
                
                # For demo purposes, return mock route data
                return {
                    'filename': uploaded_file.name,
                    'source': 'gpx_upload',
                    'analysis': {
                        'distance_km': 42.5,
                        'total_elevation_gain': 650,
                        'avg_gradient_percent': 1.8,
                        'max_gradient_percent': 12.3,
                        'elevation_variability': 180,
                        'terrain_type': 'mixed',
                        'power_analysis': {
                            'estimated_power_requirement': 245
                        }
                    }
                }
                
            except Exception as e:
                st.error(f"❌ Error processing GPX file: {str(e)}")
                return None
        
        return None
    
    def _handle_strava_route_selection(self) -> Optional[Dict[str, Any]]:
        """Handle selection of saved Strava routes."""
        # This would integrate with Strava route fetching
        st.info("🚧 Strava route integration coming soon!")
        
        # Placeholder for saved routes
        if st.button("📊 Use Demo Route"):
            return {
                'filename': 'demo_strava_route.gpx',
                'source': 'strava_route',
                'analysis': {
                    'distance_km': 38.2,
                    'total_elevation_gain': 420,
                    'avg_gradient_percent': 1.2,
                    'max_gradient_percent': 8.7,
                    'elevation_variability': 125,
                    'terrain_type': 'rolling',
                    'power_analysis': {
                        'estimated_power_requirement': 220
                    }
                }
            }
        
        return None
    
    def _handle_quick_parameters(self) -> Optional[Dict[str, Any]]:
        """Handle quick route parameter input."""
        st.markdown("### Quick Route Setup")
        
        col1, col2 = st.columns(2)
        
        with col1:
            distance = st.number_input(
                "Distance (km)",
                min_value=1.0,
                max_value=300.0,
                value=25.0,
                step=0.5
            )
            
            elevation_gain = st.number_input(
                "Total Elevation Gain (m)",
                min_value=0,
                max_value=5000,
                value=200,
                step=10
            )
        
        with col2:
            avg_gradient = st.number_input(
                "Average Gradient (%)",
                min_value=0.0,
                max_value=15.0,
                value=1.0,
                step=0.1
            )
            
            max_gradient = st.number_input(
                "Maximum Gradient (%)",
                min_value=0.0,
                max_value=25.0,
                value=5.0,
                step=0.5
            )
        
        if st.button("🎯 Generate Predictions"):
            return {
                'filename': 'quick_route_parameters',
                'source': 'manual_input',
                'analysis': {
                    'distance_km': distance,
                    'total_elevation_gain': elevation_gain,
                    'avg_gradient_percent': avg_gradient,
                    'max_gradient_percent': max_gradient,
                    'elevation_variability': elevation_gain / max(1, distance) * 10,  # Rough estimate
                    'terrain_type': 'custom',
                    'power_analysis': {
                        'estimated_power_requirement': 200 + (elevation_gain / distance) * 30  # Rough estimate
                    }
                }
            }
        
        return None
    
    def _render_predictions(self, route_data: Dict[str, Any], rider_data: Dict[str, Any]):
        """Render speed predictions for the given route."""
        st.markdown("## 🎯 Speed Predictions")
        
        # Get predictions from model
        try:
            user_id = self._get_user_id()
            predictions = self.model_manager.predict_speeds(
                user_id=user_id,
                route_data=route_data,
                rider_data=rider_data
            )
            
            if predictions and predictions.get('status') == 'success':
                self._display_prediction_results(predictions, route_data)
            else:
                # Show demo predictions if model not ready
                self._display_demo_predictions(route_data)
                
        except Exception as e:
            logger.error(f"Error getting predictions: {e}")
            st.warning("⚠️ Prediction models are still training. Showing demo predictions.")
            self._display_demo_predictions(route_data)
    
    def _display_prediction_results(self, predictions: Dict[str, Any], route_data: Dict[str, Any]):
        """Display actual prediction results."""
        analysis = route_data.get('analysis', {})
        pred_data = predictions.get('predictions', {})
        
        # Route summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📏 Distance", f"{analysis.get('distance_km', 0):.1f} km")
        
        with col2:
            st.metric("⛰️ Elevation", f"{analysis.get('total_elevation_gain', 0):.0f} m")
        
        with col3:
            st.metric("📈 Avg Grade", f"{analysis.get('avg_gradient_percent', 0):.1f}%")
        
        with col4:
            st.metric("⚡ Est. Power", f"{analysis.get('power_analysis', {}).get('estimated_power_requirement', 0):.0f} W")
        
        st.markdown("---")
        
        # Speed predictions
        st.markdown("### 🏃 Predicted Speeds")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Zone 2 (Endurance) prediction
            zone2_speed = pred_data.get('zone2_speed', 0)
            zone2_time = (analysis.get('distance_km', 0) / zone2_speed * 60) if zone2_speed > 0 else 0
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <h4>🟢 Zone 2 (Endurance)</h4>
                <p style="font-size: 1.5rem; margin: 0;"><strong>{:.1f} km/h</strong></p>
                <p style="margin: 0;">Estimated time: {:.0f}:{:02.0f}</p>
            </div>
            """.format(zone2_speed, zone2_time // 60, zone2_time % 60), unsafe_allow_html=True)
        
        with col2:
            # Threshold prediction
            threshold_speed = pred_data.get('threshold_speed', 0)
            threshold_time = (analysis.get('distance_km', 0) / threshold_speed * 60) if threshold_speed > 0 else 0
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #F59E0B, #D97706); color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                <h4>🟡 Threshold</h4>
                <p style="font-size: 1.5rem; margin: 0;"><strong>{:.1f} km/h</strong></p>
                <p style="margin: 0;">Estimated time: {:.0f}:{:02.0f}</p>
            </div>
            """.format(threshold_speed, threshold_time // 60, threshold_time % 60), unsafe_allow_html=True)
        
        # Confidence and model info
        if 'confidence' in predictions:
            confidence = predictions['confidence']
            st.markdown(f"**Model Confidence:** {confidence:.1%}")
        
        if 'model_info' in predictions:
            with st.expander("ℹ️ Model Information"):
                model_info = predictions['model_info']
                st.json(model_info)
    
    def _display_demo_predictions(self, route_data: Dict[str, Any]):
        """Display demo predictions when models aren't ready."""
        st.info("🎮 **Demo Predictions** - Your models are training! These predictions will improve as training completes.")
        
        analysis = route_data.get('analysis', {})
        distance = analysis.get('distance_km', 25)
        elevation = analysis.get('total_elevation_gain', 200)
        
        # Simple demo calculation based on route characteristics
        base_speed_z2 = 28.0  # Base endurance speed
        base_speed_threshold = 35.0  # Base threshold speed
        
        # Adjust for elevation (rough estimate)
        elevation_factor = max(0.7, 1 - (elevation / distance) * 0.01)
        
        zone2_speed = base_speed_z2 * elevation_factor
        threshold_speed = base_speed_threshold * elevation_factor
        
        # Route summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📏 Distance", f"{distance:.1f} km")
        
        with col2:
            st.metric("⛰️ Elevation", f"{elevation:.0f} m")
        
        with col3:
            st.metric("📈 Avg Grade", f"{analysis.get('avg_gradient_percent', 0):.1f}%")
        
        with col4:
            st.metric("⚡ Est. Power", f"{analysis.get('power_analysis', {}).get('estimated_power_requirement', 200):.0f} W")
        
        st.markdown("---")
        
        # Demo speed predictions
        st.markdown("### 🏃 Demo Speed Predictions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            zone2_time = (distance / zone2_speed * 60)
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #10B981, #059669); color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; opacity: 0.8;">
                <h4>🟢 Zone 2 (Endurance)</h4>
                <p style="font-size: 1.5rem; margin: 0;"><strong>{:.1f} km/h</strong></p>
                <p style="margin: 0;">Estimated time: {:.0f}:{:02.0f}</p>
                <small>Demo prediction</small>
            </div>
            """.format(zone2_speed, zone2_time // 60, zone2_time % 60), unsafe_allow_html=True)
        
        with col2:
            threshold_time = (distance / threshold_speed * 60)
            
            st.markdown("""
            <div style="background: linear-gradient(135deg, #F59E0B, #D97706); color: white; padding: 1rem; border-radius: 8px; margin: 0.5rem 0; opacity: 0.8;">
                <h4>🟡 Threshold</h4>
                <p style="font-size: 1.5rem; margin: 0;"><strong>{:.1f} km/h</strong></p>
                <p style="margin: 0;">Estimated time: {:.0f}:{:02.0f}</p>
                <small>Demo prediction</small>
            </div>
            """.format(threshold_speed, threshold_time // 60, threshold_time % 60), unsafe_allow_html=True)
    
    def _refresh_models(self):
        """Refresh/retrain models with latest data."""
        user_id = self._get_user_id()
        
        if user_id:
            with st.spinner("🔄 Refreshing models..."):
                try:
                    result = self.model_manager.initiate_model_training(user_id, async_training=False)
                    
                    if result.get('status') == 'training_completed':
                        st.success("✅ Models updated successfully!")
                    elif result.get('status') == 'insufficient_data':
                        st.warning("⚠️ Need more training data. Upload more routes or activities.")
                    else:
                        st.error(f"❌ Model refresh failed: {result.get('message', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Error refreshing models: {str(e)}")
        else:
            st.error("❌ User ID not available for model refresh")
    
    def _get_user_id(self) -> Optional[str]:
        """Get user ID from athlete info."""
        athlete_info = self.auth_manager.get_athlete_info()
        if athlete_info:
            return str(athlete_info.get('id', ''))
        return None
