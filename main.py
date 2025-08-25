import streamlit as st
from strava_connect import get_athlete
from route_processor import RouteProcessor
from weather_analyzer import WeatherAnalyzer
import streamlit.components.v1 as components
import tempfile
import os
from datetime import datetime, timedelta

def read_readme(file_path="README.md"):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading README.md: {e}"

st.title("KOMpass - Route Analysis & Planning")

# Create sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", ["Home", "Route Upload", "Saved Routes"])

if page == "Home":
    st.header("Welcome to KOMpass")
    readme_content = read_readme()
    st.markdown(readme_content)

    # Strava Athlete Info Section
    st.header("Strava Athlete Information")
    try:
        athlete = get_athlete()
        st.write(f"**Name:** {athlete.get('firstname')} {athlete.get('lastname')}")
        st.write(f"**Username:** {athlete.get('username')}")
        st.write(f"**Country:** {athlete.get('country')}")
        st.write(f"**Sex:** {athlete.get('sex')}")
        st.write(f"**Profile:** {athlete.get('profile')}")
    except Exception as e:
        st.error(f"Error fetching athlete info: {e}")

elif page == "Route Upload":
    st.header("📁 Upload Route File")
    st.markdown("Upload GPX files from ride tracking apps like RideWithGPS, Strava, Garmin Connect, etc.")
    
    # Initialize route processor and weather analyzer
    processor = RouteProcessor()
    weather_analyzer = WeatherAnalyzer()
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a GPX file",
        type=['gpx'],
        help="Upload a GPX file containing your route data"
    )
    
    if uploaded_file is not None:
        try:
            # Read file content
            gpx_content = uploaded_file.read().decode('utf-8')
            
            st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")
            
            # Process the route
            with st.spinner("Processing route data..."):
                route_data = processor.parse_gpx_file(gpx_content)
                stats = processor.calculate_route_statistics(route_data)
            
            # Display route information
            st.subheader("📊 Basic Route Statistics")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Distance", f"{stats['total_distance_km']} km")
                st.metric("Total Points", stats['total_points'])
            
            with col2:
                if stats['total_elevation_gain_m'] > 0:
                    st.metric("Elevation Gain", f"{stats['total_elevation_gain_m']} m")
                if stats['max_elevation_m'] is not None:
                    st.metric("Max Elevation", f"{stats['max_elevation_m']:.1f} m")
            
            with col3:
                if stats['total_elevation_loss_m'] > 0:
                    st.metric("Elevation Loss", f"{stats['total_elevation_loss_m']} m")
                if stats['min_elevation_m'] is not None:
                    st.metric("Min Elevation", f"{stats['min_elevation_m']:.1f} m")
            
            # Advanced Performance Metrics
            if 'gradient_analysis' in stats and stats['gradient_analysis']:
                st.subheader("⛰️ Gradient Analysis")
                gradient = stats['gradient_analysis']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Avg Gradient", f"{gradient.get('average_gradient_percent', 0)}%")
                    st.metric("Max Gradient", f"{gradient.get('max_gradient_percent', 0)}%")
                
                with col2:
                    st.metric("Steep Climbs", f"{gradient.get('steep_climbs_percent', 0)}%")
                    st.metric("Moderate Climbs", f"{gradient.get('moderate_climbs_percent', 0)}%")
                
                with col3:
                    st.metric("Flat Sections", f"{gradient.get('flat_sections_percent', 0)}%")
                    st.metric("Descents", f"{gradient.get('descents_percent', 0)}%")
                
                with col4:
                    if 'ml_features' in stats:
                        st.metric("Difficulty Index", f"{stats['ml_features'].get('difficulty_index', 0):.3f}")
                        st.metric("Elevation Variation", f"{stats['ml_features'].get('elevation_variation_index', 0)} m/km")
            
            # Climbing Analysis
            if 'climb_analysis' in stats and stats['climb_analysis'].get('climb_count', 0) > 0:
                st.subheader("🚴‍♂️ Climbing Analysis")
                climb = stats['climb_analysis']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Number of Climbs", climb.get('climb_count', 0))
                    st.metric("Total Climb Distance", f"{climb.get('total_climb_distance_km', 0)} km")
                
                with col2:
                    st.metric("Avg Climb Length", f"{climb.get('average_climb_length_m', 0):.0f} m")
                    st.metric("Avg Climb Gradient", f"{climb.get('average_climb_gradient', 0)}%")
                
                with col3:
                    st.metric("Max Climb Gradient", f"{climb.get('max_climb_gradient', 0)}%")
                    st.metric("Climb Difficulty Score", f"{climb.get('climb_difficulty_score', 0)}")
            
            # Route Complexity
            if 'complexity_analysis' in stats and stats['complexity_analysis']:
                st.subheader("🛣️ Route Complexity")
                complexity = stats['complexity_analysis']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Significant Turns", complexity.get('significant_turns_count', 0))
                    st.metric("Moderate Turns", complexity.get('moderate_turns_count', 0))
                
                with col2:
                    st.metric("Avg Direction Change", f"{complexity.get('average_direction_change_deg', 0)}°")
                    st.metric("Route Straightness", f"{complexity.get('route_straightness_index', 0):.3f}")
                
                with col3:
                    st.metric("Complexity Score", f"{complexity.get('complexity_score', 0)}")
                    if 'ml_features' in stats:
                        st.metric("Route Compactness", f"{stats['ml_features'].get('route_compactness', 0)}")
            
            # Terrain Classification (replacing Performance Predictions)
            if 'terrain_analysis' in stats and stats['terrain_analysis']:
                st.subheader("🏔️ Terrain Classification")
                terrain = stats['terrain_analysis']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Terrain Type", terrain.get('terrain_type', 'Unknown'))
                    if 'power_analysis' in stats:
                        st.metric("Avg Power", f"{stats['power_analysis'].get('average_power_watts', 0)} W")
                
                with col2:
                    if 'power_analysis' in stats:
                        power = stats['power_analysis']
                        st.metric("Est. Energy", f"{power.get('total_energy_kj', 0)} kJ")
                        st.metric("Energy/km", f"{power.get('energy_per_km_kj', 0)} kJ/km")
                
                with col3:
                    terrain_dist = terrain.get('terrain_distribution', {})
                    st.metric("Flat Sections", f"{terrain_dist.get('flat_percent', 0):.1f}%")
                    st.metric("Steep Climbs", f"{terrain_dist.get('steep_climbs_percent', 0):.1f}%")
            
            # Power Analysis Details
            if 'power_analysis' in stats and stats['power_analysis'].get('power_zones'):
                st.subheader("⚡ Power Zone Distribution")
                power = stats['power_analysis']
                zones = power['power_zones']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Endurance Zone", f"{zones.get('endurance_percent', 0)}%", help="<200W")
                
                with col2:
                    st.metric("Tempo Zone", f"{zones.get('tempo_percent', 0)}%", help="200-300W")
                
                with col3:
                    st.metric("Threshold Zone", f"{zones.get('threshold_percent', 0)}%", help=">300W")
            
            # Traffic Stop Analysis
            if 'traffic_analysis' in stats and stats['traffic_analysis'].get('analysis_available'):
                st.subheader("🚦 Traffic Stop Analysis")
                traffic = stats['traffic_analysis']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Traffic Lights", traffic.get('traffic_lights_detected', 0))
                    st.metric("Major Road Crossings", traffic.get('major_road_crossings', 0))
                
                with col2:
                    st.metric("Total Potential Stops", traffic.get('total_potential_stops', 0))
                    st.metric("Stop Density", f"{traffic.get('stop_density_per_km', 0)} stops/km")
                
                with col3:
                    st.metric("Avg Distance Between Stops", f"{traffic.get('average_distance_between_stops_km', 0)} km")
                    st.metric("Est. Time Penalty", f"{traffic.get('estimated_time_penalty_minutes', 0)} min")
                
                # Additional traffic info
                if traffic.get('infrastructure_summary'):
                    summary = traffic['infrastructure_summary']
                    st.info(f"🚦 Found {summary.get('total_traffic_lights_in_area', 0)} traffic lights and "
                           f"{summary.get('total_major_roads_in_area', 0)} major roads in route area. "
                           f"Identified {summary.get('route_intersections_found', 0)} potential stops on your route.")
            
            elif 'traffic_analysis' in stats and not stats['traffic_analysis'].get('analysis_available'):
                st.subheader("🚦 Traffic Stop Analysis")
                reason = stats['traffic_analysis'].get('reason', 'Unknown error')
                st.warning(f"⚠️ Traffic analysis unavailable: {reason}")
                if 'Unable to calculate' in reason:
                    st.info("💡 Traffic stop analysis requires an internet connection to query OpenStreetMap data.")
            
            # ML Features Summary
            if 'ml_features' in stats:
                st.subheader("🤖 ML Training Features")
                ml = stats['ml_features']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Route Density", f"{ml.get('route_density_points_per_km', 0)} pts/km")
                    st.metric("Difficulty Index", f"{ml.get('difficulty_index', 0):.3f}")
                
                with col2:
                    st.metric("Route Compactness", f"{ml.get('route_compactness', 0)}")
                    st.metric("Elevation Range", f"{ml.get('elevation_range_m', 0)} m")
                
                with col3:
                    if ml.get('stop_density_per_km') is not None:
                        st.metric("Stop Density", f"{ml.get('stop_density_per_km', 0)} stops/km")
                    if ml.get('traffic_complexity_factor') is not None:
                        st.metric("Traffic Complexity", f"{ml.get('traffic_complexity_factor', 0):.3f}")
                
                with col4:
                    if ml.get('estimated_stop_time_penalty_min') is not None:
                        st.metric("Stop Time Penalty", f"{ml.get('estimated_stop_time_penalty_min', 0)} min")
                    st.metric("Elevation Variation", f"{ml.get('elevation_variation_index', 0)} m/km")
            
            # Weather Analysis Section
            st.subheader("🌤️ Weather Analysis & Planning")
            
            # Weather input controls
            col1, col2 = st.columns(2)
            
            with col1:
                # Departure date picker
                departure_date = st.date_input(
                    "Planned Departure Date",
                    value=datetime.now().date(),
                    min_value=datetime.now().date(),
                    max_value=datetime.now().date() + timedelta(days=7),
                    help="Weather forecasts are available up to 7 days in advance"
                )
            
            with col2:
                # Departure time picker
                departure_time = st.time_input(
                    "Planned Departure Time",
                    value=datetime.now().time().replace(minute=0, second=0, microsecond=0),
                    help="Enter your planned start time"
                )
            
            # Combine date and time
            departure_datetime = datetime.combine(departure_date, departure_time)
            
            # Weather analysis button
            if st.button("🌤️ Analyze Weather Conditions"):
                with st.spinner("Analyzing weather conditions along your route..."):
                    # Collect all route points
                    all_points = []
                    for track in route_data.get('tracks', []):
                        for segment in track.get('segments', []):
                            all_points.extend(segment)
                    for route in route_data.get('routes', []):
                        all_points.extend(route.get('points', []))
                    
                    if all_points:
                        # Get comprehensive weather analysis (no speed estimates needed)
                        weather_analysis = weather_analyzer.get_comprehensive_weather_analysis(
                            all_points, departure_datetime, 2.0  # Default 2-hour duration estimate
                        )
                        
                        if weather_analysis.get('analysis_available'):
                            # Weather summary
                            st.success("✅ Weather analysis completed!")
                            
                            # Display key weather metrics
                            col1, col2, col3, col4 = st.columns(4)
                            
                            # Wind analysis
                            wind_data = weather_analysis.get('wind_analysis', {})
                            if wind_data.get('analysis_available'):
                                with col1:
                                    st.metric(
                                        "Avg Wind Impact", 
                                        f"{wind_data.get('avg_headwind_component_kmh', 0)} km/h",
                                        help="Positive = headwind, Negative = tailwind"
                                    )
                                    st.metric(
                                        "Max Headwind", 
                                        f"{wind_data.get('max_headwind_kmh', 0)} km/h"
                                    )
                            
                            # Rain analysis
                            rain_data = weather_analysis.get('precipitation_analysis', {})
                            if rain_data.get('analysis_available'):
                                with col2:
                                    st.metric(
                                        "Max Rain Chance", 
                                        f"{rain_data.get('max_precipitation_probability', 0)}%"
                                    )
                                    st.metric(
                                        "Expected Rain", 
                                        f"{rain_data.get('expected_total_precipitation_mm', 0)} mm"
                                    )
                            
                            # Temperature analysis
                            temp_data = weather_analysis.get('temperature_analysis', {})
                            if temp_data.get('analysis_available'):
                                with col3:
                                    st.metric(
                                        "Temperature Range", 
                                        f"{temp_data.get('min_temperature_c', 0)}° - {temp_data.get('max_temperature_c', 0)}°C"
                                    )
                                    st.metric(
                                        "Heat Stress Periods", 
                                        f"{temp_data.get('high_heat_periods', 0)}"
                                    )
                            
                            # Weather recommendations
                            recommendations = weather_analysis.get('recommendations', [])
                            if recommendations:
                                st.subheader("🎯 Weather Recommendations")
                                for rec in recommendations:
                                    if "warning" in rec.lower() or "extreme" in rec.lower() or "high chance" in rec.lower():
                                        st.warning(rec)
                                    elif "good" in rec.lower() or "favorable" in rec.lower():
                                        st.success(rec)
                                    else:
                                        st.info(rec)
                            
                            # Detailed weather breakdown
                            if st.expander("📊 Detailed Weather Analysis"):
                                
                                # Wind details
                                if wind_data.get('analysis_available'):
                                    st.write("**🌪️ Wind Conditions**")
                                    wind_summary = wind_data.get('wind_impact_summary', '')
                                    if wind_summary:
                                        st.write(f"• {wind_summary}")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        st.write(f"• Strong headwind sections: {wind_data.get('strong_headwind_sections', 0)}")
                                    with col2:
                                        st.write(f"• Tailwind sections: {wind_data.get('tailwind_sections', 0)}")
                                    with col3:
                                        st.write(f"• Max tailwind: {wind_data.get('max_tailwind_kmh', 0)} km/h")
                                
                                # Rain details
                                if rain_data.get('analysis_available'):
                                    st.write("**🌧️ Precipitation Conditions**")
                                    rain_summary = rain_data.get('rain_risk_summary', '')
                                    if rain_summary:
                                        st.write(f"• {rain_summary}")
                                    st.write(f"• High rain risk periods: {rain_data.get('high_rain_risk_periods', 0)}")
                                
                                # Temperature details
                                if temp_data.get('analysis_available'):
                                    st.write("**🌡️ Temperature Conditions**")
                                    heat_summary = temp_data.get('heat_stress_summary', '')
                                    if heat_summary:
                                        st.write(f"• {heat_summary}")
                                    st.write(f"• Average temperature: {temp_data.get('avg_temperature_c', 0)}°C")
                                    st.write(f"• Temperature variation: {temp_data.get('temperature_range_c', 0)}°C")
                                
                                # Additional weather metrics for ML training data
                                if weather_analysis.get('analysis_available'):
                                    st.write("**📊 Additional Weather Metrics**")
                                    if weather_analysis.get('uv_index_data'):
                                        uv_data = weather_analysis['uv_index_data']
                                        st.write(f"• Max UV Index: {uv_data.get('max_uv_index', 0)}")
                                        st.write(f"• Average UV Index: {uv_data.get('avg_uv_index', 0):.1f}")
                        
                        else:
                            error_reason = weather_analysis.get('reason', 'Unknown error')
                            st.warning(f"⚠️ Weather analysis unavailable: {error_reason}")
                            
                            if "API" in error_reason or "request" in error_reason.lower():
                                st.info("💡 Weather analysis requires an internet connection to access forecast data.")
                    else:
                        st.error("❌ Unable to analyze weather - insufficient route or speed data")
            
            else:
                st.info("📅 Select your departure date and time above, then click 'Analyze Weather Conditions' to get detailed weather forecasts for your ride.")
            
            # Display route metadata
            if route_data.get('metadata'):
                st.subheader("📋 Route Information")
                metadata = route_data['metadata']
                if metadata.get('name'):
                    st.write(f"**Name:** {metadata['name']}")
                if metadata.get('description'):
                    st.write(f"**Description:** {metadata['description']}")
                if metadata.get('time'):
                    st.write(f"**Created:** {metadata['time']}")
            
            # Create and display map
            st.subheader("🗺️ Route Visualization")
            with st.spinner("Generating map..."):
                route_map = processor.create_route_map(route_data, stats)
                
                # Save map to temporary HTML file and display
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                    route_map.save(tmp_file.name)
                    with open(tmp_file.name, 'r') as f:
                        map_html = f.read()
                    
                    # Display the map
                    components.html(map_html, height=500, scrolling=True)
                    
                    # Clean up temp file
                    os.unlink(tmp_file.name)
            
            # Save route option
            st.subheader("💾 Save Route")
            if st.button("Save Route for Future Analysis"):
                with st.spinner("Saving route..."):
                    saved_path = processor.save_route(route_data, stats)
                    st.success(f"✅ Route saved successfully!")
                    st.info(f"Saved to: {saved_path}")
                    
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please ensure you've uploaded a valid GPX file.")

elif page == "Saved Routes":
    st.header("🗃️ Saved Routes")
    st.markdown("View and analyze your previously uploaded routes.")
    
    # Initialize route processor and weather analyzer
    processor = RouteProcessor()
    weather_analyzer = WeatherAnalyzer()
    
    # Load saved routes
    saved_routes = processor.load_saved_routes()
    
    if not saved_routes:
        st.info("📭 No saved routes found. Upload some routes first!")
    else:
        st.write(f"Found {len(saved_routes)} saved route(s):")
        
        # Display saved routes
        for i, route_info in enumerate(saved_routes):
            with st.expander(f"📍 {route_info['name']} - {route_info['distance_km']} km"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Distance:** {route_info['distance_km']} km")
                    st.write(f"**Elevation Gain:** {route_info['elevation_gain_m']} m")
                    st.write(f"**Processed:** {route_info['processed_at'][:10]}")
                
                with col2:
                    st.write(f"**File:** {route_info['filename']}")
                
                # Load and display button
                if st.button(f"View Route Map", key=f"view_{i}"):
                    try:
                        # Load the full route data
                        saved_data = processor.load_route_data(route_info['filepath'])
                        route_data = saved_data['route_data']
                        stats = saved_data['statistics']
                        
                        # Create and display map
                        st.subheader(f"🗺️ {route_info['name']}")
                        with st.spinner("Loading map..."):
                            route_map = processor.create_route_map(route_data, stats)
                            
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as tmp_file:
                                route_map.save(tmp_file.name)
                                with open(tmp_file.name, 'r') as f:
                                    map_html = f.read()
                                
                                components.html(map_html, height=400, scrolling=True)
                                os.unlink(tmp_file.name)
                                
                    except Exception as e:
                        st.error(f"Error loading route: {str(e)}")