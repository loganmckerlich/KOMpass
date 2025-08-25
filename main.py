import streamlit as st
from strava_connect import get_athlete
from route_processor import RouteProcessor
import streamlit.components.v1 as components
import tempfile
import os

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
    
    # Initialize route processor
    processor = RouteProcessor()
    
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
            st.subheader("📊 Route Statistics")
            
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
    
    # Initialize route processor
    processor = RouteProcessor()
    
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