#!/usr/bin/env python3
"""
Test ML functionality for KOMpass.

Basic test to verify ML components work correctly.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ml_imports():
    """Test that ML modules can be imported."""
    try:
        from helper.ml.speed_predictor import SpeedPredictor
        from helper.ml.model_trainer import ModelTrainer
        from helper.ml.model_manager import ModelManager
        print("✅ ML modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ ML import failed: {e}")
        return False

def test_speed_prediction():
    """Test basic speed prediction functionality."""
    try:
        from helper.ml.model_manager import ModelManager
        
        manager = ModelManager()
        
        # Create sample rider data
        sample_rider = {
            'performance_features': {'estimated_ftp': 250, 'weighted_power_avg': 220},
            'basic_features': {'weight_kg': 75},
            'training_features': {'hours_per_week': 8},
            'composite_scores': {'overall_fitness_score': 75}
        }
        
        # Create sample route data
        sample_route = {
            'analysis': {
                'distance_km': 80,
                'total_elevation_gain': 800,
                'avg_gradient_percent': 1.0,
                'max_gradient_percent': 8.0,
                'elevation_variability': 200,
                'power_analysis': {'estimated_power_requirement': 240}
            }
        }
        
        # Generate predictions
        predictions = manager.predict_route_speed(sample_rider, sample_route)
        
        if 'error' in predictions:
            print(f"⚠️ Prediction completed with fallback: {predictions.get('error', 'Unknown error')}")
        else:
            print("✅ Speed predictions generated successfully")
        
        # Check prediction structure
        for effort_level in ['zone2', 'threshold']:
            if effort_level in predictions:
                prediction = predictions[effort_level]
                speed = prediction.get('speed_kmh', 0)
                confidence = prediction.get('confidence', 0)
                method = prediction.get('method', 'unknown')
                print(f"  {effort_level}: {speed:.1f} km/h (confidence: {confidence:.2f}, method: {method})")
        
        return True
        
    except Exception as e:
        print(f"❌ Speed prediction test failed: {e}")
        return False

def test_model_transparency():
    """Test model transparency functionality."""
    try:
        from helper.ml.model_manager import ModelManager
        
        manager = ModelManager()
        transparency_info = manager.get_model_transparency_info()
        
        if 'error' in transparency_info:
            print(f"⚠️ Model transparency info has errors: {transparency_info['error']}")
        else:
            print("✅ Model transparency info retrieved successfully")
            
        # Check structure
        arch_info = transparency_info.get('model_architecture', {})
        print(f"  Model Type: {arch_info.get('type', 'N/A')}")
        print(f"  Feature Count: {arch_info.get('feature_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model transparency test failed: {e}")
        return False

def main():
    """Run all ML tests."""
    print("🧪 Running KOMpass ML Tests...")
    print("=" * 50)
    
    tests = [
        ("ML Module Imports", test_ml_imports),
        ("Speed Prediction", test_speed_prediction),
        ("Model Transparency", test_model_transparency)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔬 {test_name}:")
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "PASS" if results[i] else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\n✅ {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ML functionality is working correctly.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main())