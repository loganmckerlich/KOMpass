#!/usr/bin/env python3
"""
Test script to verify that traffic and weather analysis can be disabled.
"""

import os
import sys
import tempfile
import shutil

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_config_loading():
    """Test that configuration loads feature flags correctly."""
    print("Testing configuration loading...")
    
    # Test default configuration (features disabled)
    from helper.config.config import get_config
    config = get_config()
    
    assert config.app.enable_traffic_analysis == False, "Traffic analysis should be disabled by default"
    assert config.app.enable_weather_analysis == False, "Weather analysis should be disabled by default"
    
    print("✅ Default configuration test passed")

def test_environment_variable_override():
    """Test that environment variables can override feature flags."""
    print("Testing environment variable override...")
    
    # Test environment variable override
    os.environ["ENABLE_TRAFFIC_ANALYSIS"] = "true"
    os.environ["ENABLE_WEATHER_ANALYSIS"] = "true"
    
    # Re-import to get fresh config
    import importlib
    from helper.config import config
    importlib.reload(config)
    
    new_config = config.get_config()
    assert new_config.app.enable_traffic_analysis == True, "Traffic analysis should be enabled via env var"
    assert new_config.app.enable_weather_analysis == True, "Weather analysis should be enabled via env var"
    
    # Clean up environment variables
    del os.environ["ENABLE_TRAFFIC_ANALYSIS"]
    del os.environ["ENABLE_WEATHER_ANALYSIS"]
    
    print("✅ Environment variable override test passed")

def test_route_processor_respects_flags():
    """Test that route processor respects traffic analysis flag."""
    print("Testing route processor...")
    
    from helper.processing.route_processor import RouteProcessor
    
    # Create a simple test GPX content
    test_gpx = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Route</name>
    <trkseg>
      <trkpt lat="49.2827" lon="-123.1207">
        <ele>50</ele>
      </trkpt>
      <trkpt lat="49.2837" lon="-123.1217">
        <ele>55</ele>
      </trkpt>
      <trkpt lat="49.2847" lon="-123.1227">
        <ele>60</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""
    
    processor = RouteProcessor()
    
    # Test parsing
    route_data = processor.parse_gpx_file(test_gpx)
    assert route_data is not None, "Route data should be parsed successfully"
    assert len(route_data['tracks']) > 0, "Should have at least one track"
    
    # Test statistics calculation with traffic analysis disabled (default)
    import hashlib
    route_data_hash = hashlib.md5(str(route_data).encode()).hexdigest()
    stats = processor.calculate_route_statistics(
        route_data_hash, 
        route_data, 
        include_traffic_analysis=False, 
        show_progress=False
    )
    
    assert stats is not None, "Statistics should be calculated"
    assert 'total_distance_km' in stats, "Should include basic statistics"
    assert 'traffic_analysis' in stats, "Should include traffic analysis field"
    assert not stats['traffic_analysis'].get('analysis_available', False), "Traffic analysis should not be available"
    
    print("✅ Route processor test passed")

def test_weather_analyzer_loads():
    """Test that weather analyzer can be imported and initialized."""
    print("Testing weather analyzer...")
    
    from helper.processing.weather_analyzer import WeatherAnalyzer
    
    analyzer = WeatherAnalyzer()
    assert analyzer is not None, "Weather analyzer should initialize"
    assert hasattr(analyzer, 'get_comprehensive_weather_analysis'), "Should have weather analysis method"
    
    print("✅ Weather analyzer test passed")

def test_ui_components_load():
    """Test that UI components load with the configuration."""
    print("Testing UI components...")
    
    from helper.ui.ui_components import get_ui_components
    
    ui = get_ui_components()
    assert ui is not None, "UI components should initialize"
    assert hasattr(ui, 'config'), "Should have config attribute"
    assert hasattr(ui.config, 'app'), "Should have app config"
    assert hasattr(ui.config.app, 'enable_traffic_analysis'), "Should have traffic analysis flag"
    assert hasattr(ui.config.app, 'enable_weather_analysis'), "Should have weather analysis flag"
    
    print("✅ UI components test passed")

def main():
    """Run all tests."""
    print("=== Feature Flags Test Suite ===")
    print("Testing that traffic and weather analysis can be disabled\n")
    
    try:
        test_config_loading()
        test_environment_variable_override() 
        test_route_processor_respects_flags()
        test_weather_analyzer_loads()
        test_ui_components_load()
        
        print("\n🎉 All tests passed!")
        print("✅ Traffic analysis is disabled by default")
        print("✅ Weather analysis is disabled by default") 
        print("✅ Features can be re-enabled via environment variables")
        print("✅ Route analysis continues to work without external assumptions")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)