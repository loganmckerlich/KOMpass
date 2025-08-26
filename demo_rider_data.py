#!/usr/bin/env python3
"""
Demo script for rider data functionality.
This script simulates the rider data collection and processing without requiring actual Strava credentials.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from helper.processing.rider_data_processor import RiderDataProcessor
import json


def create_mock_oauth_client():
    """Create a mock OAuth client for testing."""
    class MockOAuthClient:
        def get_athlete(self, access_token):
            return {
                "id": 12345,
                "firstname": "Demo",
                "lastname": "Rider",
                "username": "demo_rider",
                "weight": 75.0,
                "ftp": 280,
                "created_at": "2020-01-01T00:00:00Z"
            }
        
        def get_athlete_stats(self, access_token):
            return {
                "all_ride_totals": {
                    "count": 450,
                    "distance": 45000000,  # meters
                    "elevation_gain": 120000,  # meters
                    "moving_time": 1800000  # seconds
                }
            }
        
        def get_athlete_zones(self, access_token):
            return {
                "heart_rate": {
                    "zones": [
                        {"min": 0, "max": 142},
                        {"min": 142, "max": 155},
                        {"min": 155, "max": 169},
                        {"min": 169, "max": 183},
                        {"min": 183, "max": 220}
                    ]
                },
                "power": {
                    "zones": [
                        {"min": 0, "max": 168},
                        {"min": 168, "max": 224},
                        {"min": 224, "max": 252},
                        {"min": 252, "max": 280},
                        {"min": 280, "max": 336},
                        {"min": 336, "max": 420},
                        {"min": 420, "max": 999}
                    ]
                }
            }
        
        def get_athlete_activities(self, access_token, page=1, per_page=30, after_timestamp=None):
            # Generate mock activities for the last 90 days
            activities = []
            base_date = datetime.now()
            
            for i in range(min(50, per_page)):  # Limit to 50 for demo
                activity_date = base_date - timedelta(days=i*2)  # Activity every 2 days
                
                activities.append({
                    "id": f"mock_activity_{i}",
                    "type": "Ride",
                    "start_date_local": activity_date.isoformat(),
                    "distance": 45000 + (i * 1000),  # 45-95km rides
                    "moving_time": 5400 + (i * 300),  # 1.5-4 hour rides
                    "total_elevation_gain": 600 + (i * 50),  # 600-3000m elevation
                    "average_watts": 220 + (i % 60),  # 220-280W avg power
                    "average_heartrate": 155 + (i % 25),  # 155-180 avg HR
                    "max_watts": 450 + (i % 100),  # Max power variation
                    "weighted_average_watts": 240 + (i % 50)
                })
            
            return activities
    
    return MockOAuthClient()


def demo_rider_data_processor():
    """Demonstrate the rider data processor functionality."""
    print("🚴‍♂️ KOMpass Rider Data Demo")
    print("=" * 50)
    
    # Create mock OAuth client and processor
    mock_oauth = create_mock_oauth_client()
    processor = RiderDataProcessor(mock_oauth)
    
    print("\n📊 Fetching comprehensive rider data...")
    
    # Fetch comprehensive rider data
    rider_data = processor.fetch_comprehensive_rider_data("mock_access_token")
    
    print(f"✅ Successfully collected rider data with {len(rider_data)} categories")
    
    # Display key metrics
    print("\n⚡ Power Analysis:")
    if rider_data.get("power_analysis"):
        power_analysis = rider_data["power_analysis"]
        
        if power_analysis.get("recent_power_metrics"):
            recent_power = power_analysis["recent_power_metrics"]
            print(f"  • Average Power (30 days): {recent_power.get('avg_power_last_30_days', 0):.0f}W")
            print(f"  • Max Power (30 days): {recent_power.get('max_power_last_30_days', 0):.0f}W")
            print(f"  • Power Trend: {recent_power.get('power_trend', {}).get('trend_direction', 'N/A')}")
        
        if power_analysis.get("lifetime_stats"):
            lifetime = power_analysis["lifetime_stats"]
            print(f"  • Total Rides: {lifetime.get('total_rides', 0):,}")
            print(f"  • Total Distance: {lifetime.get('total_distance_km', 0):.0f} km")
    
    print("\n💪 Fitness Metrics:")
    if rider_data.get("fitness_metrics"):
        fitness = rider_data["fitness_metrics"]
        print(f"  • Total Activities: {fitness.get('total_activities', 0)}")
        
        freq = fitness.get("activity_frequency", {})
        print(f"  • Activities per Week: {freq.get('activities_per_week', 0):.1f}")
        
        print(f"  • Training Consistency: {fitness.get('training_consistency', 0):.1%}")
    
    print("\n📈 Training Load:")
    if rider_data.get("training_load"):
        load = rider_data["training_load"]
        
        weekly_hours = load.get("weekly_training_hours", {})
        print(f"  • Avg Weekly Hours: {weekly_hours.get('avg_weekly_hours', 0):.1f}h")
        
        tsb = load.get("training_stress_balance", {})
        print(f"  • Training Stress Balance: {tsb.get('training_stress_balance', 0):.1f}")
    
    # Generate ML features
    print("\n🤖 ML Feature Engineering:")
    ml_features = processor.get_feature_engineering_data(rider_data)
    print(f"  • Generated {len(ml_features)} features for ML applications")
    
    # Display some key features
    key_features = [
        "recent_avg_power", "activity_frequency_per_week", "training_consistency_score",
        "avg_weekly_training_hours", "power_trend_improving"
    ]
    
    for feature in key_features:
        if feature in ml_features and ml_features[feature] is not None:
            value = ml_features[feature]
            print(f"    - {feature.replace('_', ' ').title()}: {value}")
    
    print(f"\n📊 Data Summary:")
    print(f"  • Basic Info: {'✅' if rider_data.get('basic_info') else '❌'}")
    print(f"  • Stats: {'✅' if rider_data.get('stats') else '❌'}")
    print(f"  • Zones: {'✅' if rider_data.get('zones') else '❌'}")
    print(f"  • Recent Activities: {'✅' if rider_data.get('recent_activities') else '❌'}")
    print(f"  • Fitness Metrics: {'✅' if rider_data.get('fitness_metrics') else '❌'}")
    print(f"  • Power Analysis: {'✅' if rider_data.get('power_analysis') else '❌'}")
    print(f"  • Training Load: {'✅' if rider_data.get('training_load') else '❌'}")
    
    # Save demo data to file
    demo_file = "/tmp/demo_rider_data.json"
    with open(demo_file, 'w') as f:
        json.dump(rider_data, f, indent=2, default=str)
    
    print(f"\n💾 Demo data saved to: {demo_file}")
    print("\n🎯 This demonstrates the comprehensive rider data collection")
    print("   that will be triggered automatically when a rider logs in!")


if __name__ == "__main__":
    demo_rider_data_processor()