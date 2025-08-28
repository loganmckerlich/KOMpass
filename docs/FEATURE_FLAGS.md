# Feature Flags Documentation

This document describes the feature flags implemented to temporarily disable traffic light/intersection analysis and weather analysis in KOMpass.

## Overview

As requested in issue #64, traffic light/intersection analysis and weather analysis have been temporarily disabled to ensure route analysis focuses strictly on gathering data about the given route without external assumptions.

## Configuration

### Feature Flags

The following feature flags have been added to control analysis features:

- `enable_traffic_analysis`: Controls traffic light and intersection analysis (default: `false`)
- `enable_weather_analysis`: Controls weather forecasting and analysis (default: `false`)

### Environment Variables

Features can be re-enabled by setting environment variables:

```bash
# Enable traffic analysis
export ENABLE_TRAFFIC_ANALYSIS=true

# Enable weather analysis  
export ENABLE_WEATHER_ANALYSIS=true

# Run the application
streamlit run main.py
```

## What's Disabled

### Traffic Light/Intersection Analysis
- **What**: Analysis of traffic lights and major road intersections along the route
- **Status**: Disabled by default
- **UI Impact**: Shows message "🚦 Traffic light and intersection analysis is temporarily disabled."
- **Data Impact**: No external OpenStreetMap API calls for traffic infrastructure

### Weather Analysis
- **What**: Weather forecasting and conditions analysis for the route
- **Status**: Disabled by default  
- **UI Impact**: Shows message "🌤️ Weather analysis is temporarily disabled."
- **Data Impact**: No external weather API calls

## What Remains Enabled

The core route analysis continues to function and only gathers factual data about the route:

### GPS-Based Analysis (Always Enabled)
- ✅ **Distance calculation**: Mathematical computation from GPS coordinates
- ✅ **Elevation analysis**: From GPS elevation data points
- ✅ **Gradient calculation**: Mathematical derivatives of elevation/distance 
- ✅ **Direction analysis**: Mathematical bearing calculations from coordinates
- ✅ **Route complexity**: Based on measured direction changes
- ✅ **Terrain classification**: Statistical analysis of measured gradients
- ✅ **Climb detection**: From gradient analysis
- ✅ **Power estimates**: Physics formulas applied to route characteristics (uses standardized reference values, not assumptions)

### Data Sources
- **GPS coordinates**: Latitude/longitude from uploaded GPX files
- **GPS elevations**: Elevation data from GPX files
- **Mathematical calculations**: All analysis derived from mathematical operations on GPS data
- **Physics formulas**: Standardized power calculations based on route characteristics
- **No external APIs**: No traffic, weather, or other external data sources

## Testing

Run the included tests to verify the implementation:

```bash
# Test feature flags functionality
python test_feature_flags.py

# Test route analysis purity (no external assumptions)
python test_route_purity.py
```

## Re-enabling Features

To re-enable these features in the future:

1. **Environment variables** (temporary):
   ```bash
   export ENABLE_TRAFFIC_ANALYSIS=true
   export ENABLE_WEATHER_ANALYSIS=true
   ```

2. **Configuration defaults** (permanent):
   Update `helper/config/config.py` and change the default values:
   ```python
   enable_traffic_analysis: bool = True
   enable_weather_analysis: bool = True
   ```

## Implementation Details

### Configuration
- Feature flags added to `AppConfig` class in `helper/config/config.py`
- Environment variable support with `ENABLE_TRAFFIC_ANALYSIS` and `ENABLE_WEATHER_ANALYSIS`
- Validation and logging of feature flag status

### UI Components  
- Conditional display of analysis sections based on configuration flags
- Clear user messaging when features are disabled
- KPI metrics show "Disabled" status for disabled features

### Route Processing
- Traffic analysis controlled by `include_traffic_analysis` parameter
- Weather analysis skipped when feature flag is disabled
- Core route analysis unaffected

## Verification

The implementation ensures:
- ✅ Traffic analysis is disabled by default
- ✅ Weather analysis is disabled by default  
- ✅ Features can be re-enabled via environment variables
- ✅ Route analysis remains assumption-free
- ✅ All calculations are based solely on provided GPS data
- ✅ UI clearly indicates when features are disabled
- ✅ No external API calls when features are disabled