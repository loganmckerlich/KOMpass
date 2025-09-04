#!/usr/bin/env python3
"""
Test script to simulate authenticated state for testing the refactored application.
This bypasses the authentication requirement to test the authenticated user interface.
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.append('/home/runner/work/KOMpass/KOMpass')

def simulate_authenticated_session():
    """Simulate an authenticated session with mock data."""
    
    # Mock authentication state
    st.session_state["authenticated"] = True
    st.session_state["access_token"] = "mock_access_token"
    st.session_state["refresh_token"] = "mock_refresh_token"
    st.session_state["expires_at"] = int((datetime.now().timestamp() + 3600))
    
    # Mock athlete info
    st.session_state["athlete_info"] = {
        "id": 12345678,
        "firstname": "Test",
        "lastname": "Cyclist",
        "email": "test@example.com",
        "created_at": "2020-01-01T00:00:00Z"
    }
    
    # Mock rider fitness data
    st.session_state["rider_fitness_data"] = {
        "basic_features": {
            "athlete_id": 12345678,
            "weight_kg": 75.0,
            "created_at": "2020-01-01T00:00:00Z"
        },
        "performance_features": {
            "estimated_ftp": 280,
            "max_power_5s": 1200,
            "max_power_1min": 450,
            "max_power_5min": 350,
            "max_power_20min": 300,
            "weighted_power_avg": 220,
            "max_power_overall": 1250,
            "power_efficiency_score": 85.5
        },
        "training_features": {
            "hours_per_week": 8.5,
            "training_intensity_score": 75.2,
            "training_consistency_score": 88.0,
            "zone1_time_percent": 60.0,
            "zone2_time_percent": 25.0,
            "zone4_time_percent": 10.0
        },
        "composite_scores": {
            "overall_fitness_score": 78.5
        },
        "recent_activities": [
            {
                "id": 1,
                "name": "Morning Ride",
                "distance": 42000,  # meters
                "moving_time": 5400,  # seconds
                "average_watts": 245,
                "start_date_local": "2024-01-01T08:00:00Z"
            },
            {
                "id": 2,
                "name": "Interval Training",
                "distance": 35000,
                "moving_time": 4200,
                "average_watts": 280,
                "start_date_local": "2023-12-30T18:00:00Z"
            },
            {
                "id": 3,
                "name": "Recovery Ride",
                "distance": 25000,
                "moving_time": 3600,
                "average_watts": 180,
                "start_date_local": "2023-12-28T10:00:00Z"
            }
        ]
    }
    
    # Mock auto-training status
    st.session_state["auto_training_status"] = {
        "status": "training_started",
        "message": "Model training started automatically",
        "timestamp": datetime.now().isoformat()
    }
    
    # Mock training data update
    st.session_state["training_data_update"] = {
        "processed": 30,
        "skipped_duplicates": 5,
        "errors": 0,
        "timestamp": datetime.now().isoformat(),
        "consolidated": True,
        "consolidated_samples": 150,
        "consolidated_filename": "consolidated_training_data.json",
        "consolidated_size_mb": 2.5
    }

def main():
    """Test the authenticated application flow."""
    # Set up Streamlit page
    st.set_page_config(
        page_title="KOMpass - Test Mode",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown("# 🧪 KOMpass Test Mode")
    st.markdown("**Testing authenticated application flow with mock data**")
    
    # Simulate authenticated session
    simulate_authenticated_session()
    
    st.success("✅ Authentication simulated successfully!")
    
    # Display mock user info
    athlete_info = st.session_state.get("athlete_info", {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("User ID", athlete_info.get("id", "N/A"))
    with col2:
        st.metric("Name", f"{athlete_info.get('firstname', '')} {athlete_info.get('lastname', '')}")
    with col3:
        st.metric("Status", "🟢 Authenticated")
    
    st.markdown("---")
    
    # Test the main application components
    st.markdown("## 🧭 Test Navigation")
    
    page_choice = st.selectbox(
        "Choose a page to test:",
        ["Speed Predictions", "User Stats", "Route Upload"]
    )
    
    if page_choice == "Speed Predictions":
        test_speed_predictions()
    elif page_choice == "User Stats":
        test_user_stats()
    elif page_choice == "Route Upload":
        test_route_upload()

def test_speed_predictions():
    """Test the speed predictions page."""
    try:
        from helper.ui.components.ml_page import MLPage
        
        st.markdown("### 🎯 Testing Speed Predictions Page")
        ml_page = MLPage()
        ml_page.render_ml_page()
        
    except Exception as e:
        st.error(f"❌ Error testing Speed Predictions: {str(e)}")
        st.exception(e)

def test_user_stats():
    """Test the user stats page."""
    try:
        from helper.ui.components.user_stats import UserStatsPage
        
        st.markdown("### 📊 Testing User Stats Page")
        user_stats = UserStatsPage()
        user_stats.render_user_stats_page()
        
    except Exception as e:
        st.error(f"❌ Error testing User Stats: {str(e)}")
        st.exception(e)

def test_route_upload():
    """Test the route upload page."""
    try:
        from helper.ui.components.route_upload import RouteUpload
        
        st.markdown("### 📁 Testing Route Upload Page")
        route_upload = RouteUpload()
        route_upload.render_route_upload_page()
        
    except Exception as e:
        st.error(f"❌ Error testing Route Upload: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()