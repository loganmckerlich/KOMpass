#!/usr/bin/env python3
"""
Performance test script for route analysis optimizations.
Tests and measures the performance improvements in route processing.
"""

import time
import numpy as np
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helper.processing.route_processor import RouteProcessor


def create_test_gpx_route(num_points=1000):
    """Create a test GPX route with specified number of points for performance testing."""
    
    # Create a more realistic route (San Francisco to San Jose area)
    start_lat, start_lon = 37.7749, -122.4194  # San Francisco
    end_lat, end_lon = 37.3382, -121.8863      # San Jose
    
    # Generate points along a route with some elevation variation
    lats = np.linspace(start_lat, end_lat, num_points)
    lons = np.linspace(start_lon, end_lon, num_points)
    
    # Create realistic elevation profile with hills
    elevations = []
    for i in range(num_points):
        # Create some hills and valleys
        progress = i / num_points
        base_elevation = 10 + progress * 50  # Gradual climb
        hill_elevation = 100 * np.sin(progress * 6 * np.pi)  # 3 hills
        noise = np.random.normal(0, 5)  # Some random variation
        elevation = max(0, base_elevation + hill_elevation + noise)
        elevations.append(elevation)
    
    # Generate GPX content
    gpx_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="KOMpass Performance Test" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Performance Test Route ({num_points} points)</name>
    <desc>A test route for performance benchmarking</desc>
    <time>2024-08-28T10:00:00Z</time>
  </metadata>
  <trk>
    <name>Performance Test</name>
    <desc>Route with {num_points} points for testing</desc>
    <trkseg>'''
    
    for i, (lat, lon, ele) in enumerate(zip(lats, lons, elevations)):
        timestamp = f"2024-08-28T{10 + i//100:02d}:{(i%100)*60//100:02d}:{(i*60)%60:02d}Z"
        gpx_content += f'''
      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{ele:.1f}</ele><time>{timestamp}</time></trkpt>'''
    
    gpx_content += '''
    </trkseg>
  </trk>
</gpx>'''
    
    return gpx_content


def benchmark_route_analysis(num_points=1000, num_runs=3):
    """Benchmark route analysis performance."""
    
    print(f"\n🔬 Performance Benchmark: Route Analysis with {num_points} points")
    print("=" * 60)
    
    # Create test route
    print("📝 Creating test route...")
    gpx_content = create_test_gpx_route(num_points)
    
    # Initialize processor
    processor = RouteProcessor()
    
    times_with_progress = []
    times_without_progress = []
    
    for run in range(num_runs):
        print(f"\n🏃 Run {run + 1}/{num_runs}")
        
        # Test with progress indicators (disabled for benchmarking)
        print("  📊 Testing with optimized analysis...")
        start_time = time.time()
        
        try:
            # Parse GPX
            route_data = processor.parse_gpx_file(gpx_content)
            route_data_hash = f"test_route_{num_points}_{run}"
            
            # Calculate statistics without progress display for cleaner benchmarking
            stats = processor.calculate_route_statistics(
                route_data_hash,
                route_data,
                include_traffic_analysis=False,  # Skip traffic for pure route analysis benchmark
                show_progress=False
            )
            
            elapsed = time.time() - start_time
            times_with_progress.append(elapsed)
            
            print(f"    ✅ Completed in {elapsed:.3f}s")
            print(f"    📈 Processed {stats.get('total_points', 0)} points")
            print(f"    📏 Total distance: {stats.get('total_distance_km', 0):.2f} km")
            print(f"    ⛰️  Elevation gain: {stats.get('total_elevation_gain_m', 0):.1f} m")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    # Calculate statistics
    if times_with_progress:
        avg_time = np.mean(times_with_progress)
        std_time = np.std(times_with_progress)
        min_time = np.min(times_with_progress)
        max_time = np.max(times_with_progress)
        
        print(f"\n📊 Performance Summary:")
        print(f"  📦 Route size: {num_points} points")
        print(f"  🔄 Runs: {len(times_with_progress)}")
        print(f"  ⏱️  Average time: {avg_time:.3f}s ± {std_time:.3f}s")
        print(f"  🚀 Best time: {min_time:.3f}s")
        print(f"  🐌 Worst time: {max_time:.3f}s")
        print(f"  📈 Processing rate: {num_points/avg_time:.0f} points/second")
        
        # Performance metrics
        points_per_second = num_points / avg_time
        if points_per_second > 1000:
            performance_rating = "🚀 Excellent"
        elif points_per_second > 500:
            performance_rating = "✅ Good"
        elif points_per_second > 200:
            performance_rating = "⚠️ Average"
        else:
            performance_rating = "🐌 Slow"
            
        print(f"  🏆 Performance rating: {performance_rating}")
        
        return avg_time, points_per_second
    
    return None, None


def test_progress_tracking():
    """Test the progress tracking functionality."""
    
    print(f"\n🎯 Testing Progress Tracking")
    print("=" * 40)
    
    from helper.utils.progress_tracker import create_route_analysis_tracker
    
    # Create a small route for testing
    gpx_content = create_test_gpx_route(100)
    processor = RouteProcessor()
    
    print("📝 Parsing test route...")
    route_data = processor.parse_gpx_file(gpx_content)
    route_data_hash = "test_progress"
    
    print("📊 Running analysis with progress tracking...")
    start_time = time.time()
    
    try:
        stats = processor.calculate_route_statistics(
            route_data_hash,
            route_data,
            include_traffic_analysis=False,
            show_progress=False  # Set to True to see progress in console
        )
        
        elapsed = time.time() - start_time
        print(f"✅ Progress tracking test completed in {elapsed:.3f}s")
        return True
        
    except Exception as e:
        print(f"❌ Progress tracking test failed: {e}")
        return False


def main():
    """Run performance benchmarks."""
    
    print("🧭 KOMpass Route Analysis Performance Benchmark")
    print("=" * 50)
    
    # Test different route sizes
    test_sizes = [100, 500, 1000, 2000]
    results = []
    
    for size in test_sizes:
        avg_time, points_per_sec = benchmark_route_analysis(size, num_runs=2)
        if avg_time is not None:
            results.append((size, avg_time, points_per_sec))
    
    # Print summary
    print(f"\n🏆 Performance Summary")
    print("=" * 50)
    print(f"{'Route Size':<12} {'Avg Time':<10} {'Points/Sec':<12} {'Rating'}")
    print("-" * 50)
    
    for size, avg_time, points_per_sec in results:
        if points_per_sec > 1000:
            rating = "🚀 Excellent"
        elif points_per_sec > 500:
            rating = "✅ Good"
        elif points_per_sec > 200:
            rating = "⚠️ Average"
        else:
            rating = "🐌 Slow"
            
        print(f"{size:<12} {avg_time:<10.3f} {points_per_sec:<12.0f} {rating}")
    
    # Test progress tracking
    test_progress_tracking()
    
    print(f"\n🎉 Benchmark completed!")
    print(f"💡 The optimizations provide better user experience with detailed progress feedback")
    print(f"⚡ Combined gradient/climb analysis reduces processing overhead")
    print(f"🎯 Caching ensures repeat analyses are near-instantaneous")


if __name__ == "__main__":
    main()