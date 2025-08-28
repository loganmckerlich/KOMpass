# Rider Side Data Implementation

This document describes the comprehensive rider data implementation for KOMpass, which automatically collects and processes extensive fitness metrics from the Strava API when a rider logs in.

## Overview

The rider data system fetches, processes, and engineers features from multiple Strava API endpoints to create a comprehensive fitness profile for each rider. This data is used for:

1. **Performance Analysis**: Understanding rider capabilities and trends
2. **Route Recommendations**: Matching routes to rider fitness levels
3. **Machine Learning**: Feature engineering for predictive models
4. **Progress Tracking**: Monitoring fitness improvements over time

## Data Sources

### 1. Basic Athlete Information (`/athlete`)
- Personal details (name, weight, FTP)
- Account information (creation date, followers, etc.)
- Profile data for UI display

### 2. Athlete Statistics (`/athlete/stats`)
- Lifetime activity totals
- Distance, elevation, and time records
- Activity counts by sport type

### 3. Power and Heart Rate Zones (`/athlete/zones`)
- Training zones for power and heart rate
- Zone boundaries for intensity analysis
- Threshold values for performance metrics

### 4. Recent Activities (`/athlete/activities`)
- Last 90 days of activity data
- Power, heart rate, and performance metrics
- Activity-by-activity detailed data

## Processed Metrics

### Power Analysis
- **Recent Power Metrics** (30-day window)
  - Average power
  - Maximum power
  - Power trend (improving/declining)
  - Power consistency (standard deviation)
  - Weighted power average

- **Lifetime Statistics**
  - Total rides
  - Total distance
  - Total elevation gain
  - Total moving time

### Fitness Metrics
- **Activity Frequency**
  - Activities per week
  - Riding days per week
  
- **Training Consistency Score** (0-1)
  - Based on gap variance between activities
  - Higher score = more consistent training
  
- **Fitness Trend Analysis**
  - 7-day rolling averages
  - Recent vs. older period comparison
  - Trend direction and magnitude

- **Intensity Distribution**
  - Easy/moderate/hard training distribution
  - Based on heart rate percentiles
  - Average heart rate across activities

### Training Load Analysis
- **Weekly Training Hours**
  - Average weekly training time
  - Maximum weekly volume
  - Current week hours

- **Training Intensity Factor**
  - Weighted intensity based on power and duration
  - Normalized against threshold power

- **Recovery Metrics**
  - Average rest days between activities
  - Maximum rest periods
  - Recovery consistency

- **Training Stress Balance (TSB)**
  - Acute vs. chronic training load
  - Simplified TSB calculation
  - Recovery/stress indicators

- **Peak Training Identification**
  - Highest volume training periods
  - Peak weekly hours and distance
  - Training periodization insights

## Feature Engineering for ML

The system generates ML-ready features including:

### Rider Characteristics
- `rider_weight_kg`: Body weight
- `rider_ftp`: Functional Threshold Power
- `rider_experience_years`: Years since Strava account creation

### Power Features
- `recent_avg_power`: Average power last 30 days
- `power_consistency`: Power output consistency
- `power_trend_improving`: Binary trend indicator

### Training Features
- `activity_frequency_per_week`: Weekly activity rate
- `training_consistency_score`: Consistency metric (0-1)
- `avg_heart_rate`: Average heart rate across activities

### Load Features
- `avg_weekly_training_hours`: Average weekly volume
- `training_stress_balance`: TSB metric
- `recovery_consistency`: Recovery pattern consistency

## Caching and Performance

### Session State Caching
- Rider data cached in `st.session_state["rider_fitness_data"]`
- 1-hour TTL on computation-heavy functions
- Intelligent refresh on authentication

### API Rate Limiting
- Respectful API usage with delays between calls
- Batch processing for efficiency
- Error handling for API failures

### Memory Management
- Strategic caching of expensive calculations
- Cleanup on logout
- Efficient data structures

## Usage Flow

1. **User Authenticates**: Login via Strava OAuth
2. **Data Collection Triggered**: Automatic fetch on successful auth
3. **Processing Pipeline**: Multi-step data processing and analysis
4. **Feature Engineering**: ML-ready feature extraction
5. **UI Display**: Rich visualization of metrics and trends
6. **Caching**: Store results for subsequent requests

## Error Handling

- **Graceful Degradation**: Partial data collection if some endpoints fail
- **API Failures**: Proper error logging and user feedback
- **Missing Data**: Handles incomplete or missing metrics
- **Rate Limiting**: Respects Strava API limits

## Future Enhancements

1. **Advanced Metrics**: VO2 max estimation, power curves
2. **Trend Forecasting**: Predictive fitness modeling
3. **Comparative Analysis**: Peer benchmarking
4. **Training Recommendations**: AI-powered suggestions
5. **Integration**: Connect with other fitness platforms

## API Scope Requirements

The implementation requires the following Strava OAuth scopes:
- `read`: Basic profile information
- `activity:read_all`: Access to all activity data
- `profile:read_all`: Extended profile information

This comprehensive rider data system provides the foundation for advanced route analysis, performance prediction, and personalized cycling recommendations in KOMpass.