# KOMpass

KOMpass is a Strava API app to forecast rider speed given a route. Applications include setting goal paces and identifying segments to KOM ☠️

## Features
- Forecast rider speed for any given route
- Set goal paces
- Identify segments to aim for KOM
- **NEW**: Upload and analyze GPX route files from cycling apps
- **NEW**: Interactive route visualization with folium maps
- **NEW**: Save routes for future analysis

## Route Upload Feature 🚀

The new route upload feature allows you to:

### Upload Routes
- Upload GPX files from popular cycling apps like:
  - RideWithGPS
  - Strava
  - Garmin Connect
  - Wahoo ELEMNT
  - And any other app that exports GPX format

### Route Analysis
- **Distance**: Total route distance in kilometers
- **Elevation**: Gain, loss, max, and min elevation
- **Route Information**: Name, description, and creation date from GPX metadata
- **Interactive Maps**: Folium-based visualization with start/end markers

### Data Persistence
- Save processed routes for future analysis
- JSON format for easy data manipulation
- View and manage all saved routes
- Load saved routes with full visualization

### Getting Started with Route Upload

1. **Navigate to Route Upload**: Use the sidebar navigation to select "Route Upload"
2. **Upload GPX File**: Drag and drop or browse for your GPX file
3. **View Analysis**: See route statistics and interactive map visualization
4. **Save Route**: Click "Save Route for Future Analysis" to persist the data
5. **Access Saved Routes**: Navigate to "Saved Routes" to view all your uploaded routes

## Installation

Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Strava OAuth Configuration

To use Strava features, you need to configure OAuth authentication:

### 1. Create Strava Application
1. Go to [Strava API Settings](https://www.strava.com/settings/api)
2. Create a new application or use an existing one
3. Set the **Authorization Callback Domain**:
   - For production: `kompass-dev.streamlit.app`
   - For local development: `localhost`
   - ⚠️ **Important**: Do NOT include `https://` or trailing slash

### 2. Set Environment Variables
```bash
export STRAVA_CLIENT_ID=your_client_id_here
export STRAVA_CLIENT_SECRET=your_client_secret_here

# For local development:
export STREAMLIT_ENV=development
```

### 3. Verify Configuration (Optional)
Run the verification script to check your OAuth setup:
```bash
python verify_oauth_config.py
```

### 4. Troubleshooting OAuth Issues
If you're getting **403 errors** during Strava authentication:
- See the [OAuth Troubleshooting Guide](./OAUTH_TROUBLESHOOTING.md) for detailed solutions
- Ensure redirect URI domains match exactly between Strava settings and your environment
- Check that environment variables are set correctly
- Verify your Client ID and Client Secret are correct

## Running the Application

```bash
streamlit run main.py
```

## Getting Started
Coming soon.

## License
MIT License