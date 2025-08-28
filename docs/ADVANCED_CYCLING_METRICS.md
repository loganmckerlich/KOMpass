# Advanced Cycling Metrics Implementation

This document outlines the comprehensive advanced cycling metrics system implemented for KOMpass, specifically designed to address Logan's requirements for detailed rider data collection and zone-specific speed prediction.

## Overview

The enhanced rider data collection system now provides extensive cycling analytics that enables personalized route recommendations and performance predictions. The system automatically triggers when a rider logs in via Strava OAuth.

## Key Features Implemented

### 1. Advanced Cycling Metrics

#### Critical Power Curve Analysis
- **Critical Power (CP)**: Theoretical power sustainable indefinitely
- **W' (W-prime)**: Anaerobic work capacity above CP
- **Power Records**: Analysis of peak efforts across different durations
- **Power-to-Weight Ratios**: Performance normalized by body weight
- **Performance Classification**: Elite/Professional/Competitive/Recreational levels

#### VO2 Max Estimation
- **Hawley & Noakes Formula**: VO2max = 10.8 * (Power/Weight) + 7
- **Coggan Formula**: Adjusted for 5-minute power efforts
- **Classification Levels**: Elite (70+), Excellent (60+), Good (50+), Fair (40+)
- **Sustained Effort Analysis**: Power endurance from recent activities

#### Lactate Threshold Analysis
- **Functional Threshold Power (FTP)**: Primary threshold metric
- **Power Zone Boundaries**: 7-zone system (Recovery to Neuromuscular)
- **Zone Speed Estimates**: **Critical for Logan's use case**
- **FTP Trend Analysis**: Historical progression tracking

### 2. Zone-Specific Speed Prediction (Logan's Primary Requirement)

#### Implementation Details
```python
def _estimate_zone_speeds(self, ftp: float) -> Dict[str, Dict[str, float]]:
    """
    Estimate riding speeds at different power zones.
    This enables predicting how long rides will take at different intensities.
    """
```

#### Zone Speed Predictions Include:
- **Zone 1 (Recovery)**: ~55% FTP - Easy spinning
- **Zone 2 (Endurance)**: ~75% FTP - **Primary aerobic base pace**
- **Zone 3 (Tempo)**: ~90% FTP - Steady sustainable effort
- **Zone 4 (Threshold)**: ~100% FTP - **FTP/threshold pace**
- **Zone 5 (VO2 Max)**: ~115% FTP - High-intensity intervals
- **Zone 6 (Anaerobic)**: ~135% FTP - Sprint efforts

#### Distance Time Predictions
For each zone, the system calculates estimated ride times for:
- 10km, 20km, 40km, 80km, 100km, 160km distances
- Formatted as HH:MM for easy planning
- Confidence levels based on available calibration data

### 3. Distance-Specific Performance Analysis

#### Short Distance Performance (<30km)
- Sprint power and anaerobic capacity
- Peak power capabilities
- High-intensity interval performance
- Neuromuscular power analysis

#### Medium Distance Performance (30-80km)
- Tempo and threshold power sustainability
- Zone-specific performance tracking
- Power-to-weight ratios for climbing

#### Long Distance Performance (80km+)
- Endurance power sustainability
- Fatigue resistance scoring
- Power decay modeling
- Ultra-endurance capabilities (160km+)

#### Performance Comparison
- Power decay percentage across distances
- Strongest distance category identification
- Endurance profile classification

### 4. Advanced Performance Metrics

#### Power Profile Classification
- **Sprinter**: High peak power relative to FTP (>2.5x ratio)
- **Time Trialist/Pursuit**: Strong sustained power (2.0-2.5x ratio)
- **All-rounder**: Balanced profile (1.8-2.0x ratio)
- **Climber/Endurance**: Power endurance specialist (<1.8x ratio)

#### Aerobic Efficiency Analysis
- Power-per-heart rate ratios
- Efficiency trend analysis
- Training adaptation indicators

#### Anaerobic Capacity Analysis
- Peak power capabilities
- Anaerobic power reserve
- Short effort consistency

#### Fatigue Resistance Analysis
- Power sustainability over long efforts
- Endurance classification
- Recovery capabilities

#### Training Stress Analysis
- **Training Stress Score (TSS)**: Quantified training load
- **Chronic Training Load (CTL)**: 42-day rolling average
- **Acute Training Load (ATL)**: 7-day rolling average
- **Training Stress Balance (TSB)**: CTL - ATL
- TSB interpretation for training guidance

### 5. Comprehensive Feature Engineering

#### 46+ ML-Ready Features Generated:
- **Power Metrics**: Recent avg power, critical power, peak power
- **Training Metrics**: Activity frequency, consistency, weekly hours
- **Performance Scores**: Power, endurance, training quality scores
- **Physiological**: VO2 max, power-to-weight ratios, efficiency
- **Zone Analysis**: Zone balance, time-in-zone distribution
- **Distance Performance**: Power across distance categories
- **Composite Scores**: Overall performance index

#### Example Features:
```python
{
    "recent_avg_power": 244.5,
    "critical_power_watts": 265.0,
    "estimated_vo2_max": 58.3,
    "power_performance_score": 82.1,
    "endurance_performance_score": 78.9,
    "overall_performance_index": 81.7,
    "zone_balance_score": 0.847,
    "power_decay_percentage": 15.2
}
```

## Enhanced Strava API Integration

### New API Endpoints Added:
1. **Activity Streams** (`/activities/{id}/streams`): Detailed power/HR data
2. **Detailed Activity** (`/activities/{id}`): Comprehensive activity analysis
3. **KOM Achievements** (`/athlete/koms`): Performance achievements

### Enhanced Scope:
```python
"scope": "read,activity:read_all,profile:read_all"
```

## UI Enhancement

### Tabbed Interface:
1. **⚡ Power & Performance**: Core power metrics and critical power curve
2. **🎯 Zone Analysis**: **Zone speed predictions with ride time estimates**
3. **📈 Advanced Metrics**: Power profile, training stress, efficiency
4. **🏁 Distance Performance**: Performance across distance categories
5. **🤖 ML Features**: Feature engineering preview

### Zone Speed Predictions Display:
- Each power zone shows predicted speed and ride time estimates
- Distance predictions for common cycling distances
- Confidence levels based on calibration data quality
- Model quality indicators

## Use Cases Enabled

### 1. Route Planning (Logan's Primary Need)
**Question**: "How long will this 80km route take at Zone 2 vs Threshold?"

**Answer**: 
- Zone 2 (Endurance): 2:40 at 30.0 km/h
- Zone 4 (Threshold): 2:00 at 40.0 km/h

### 2. Training Prescription
- Identify power profile strengths/weaknesses
- Optimize training zone distribution
- Track training stress and recovery

### 3. Performance Prediction
- Estimate capabilities across different distances
- Predict performance decline in long events
- Assess readiness for specific challenges

### 4. Personalized Recommendations
- Route difficulty matching based on rider capabilities
- Training recommendations based on profile gaps
- Recovery guidance from training stress analysis

## Technical Implementation

### Data Processing Pipeline:
1. **OAuth Authentication**: Enhanced scope for comprehensive data access
2. **Data Collection**: Multiple API endpoints with rate limiting
3. **Analytics Processing**: Advanced cycling metrics calculation
4. **Feature Engineering**: ML-ready feature generation
5. **UI Rendering**: Tabbed interface with comprehensive display
6. **Caching**: 1-hour TTL for expensive computations

### Error Handling:
- Graceful degradation when API endpoints fail
- Partial data collection continues if some endpoints fail
- User-friendly error messages and recovery options

### Performance Optimization:
- Streamlit caching for expensive calculations
- Efficient API batching with rate limiting
- Modular architecture for selective computation

## Future Enhancements

### Calibration and Validation:
- Real-world speed validation against actual ride data
- Environmental factor adjustments (wind, gradient, temperature)
- Route-specific power requirements

### Enhanced Modeling:
- Machine learning models for speed prediction
- Terrain-adjusted power requirements
- Weather impact on performance

### Integration Opportunities:
- Route planning with zone-specific time estimates
- Training load optimization
- Performance tracking and trend analysis

## Summary

This implementation provides a comprehensive foundation for advanced cycling analytics in KOMpass. The zone-specific speed prediction capability directly addresses Logan's requirement for estimating ride times at different effort levels, while the extensive feature engineering enables sophisticated route recommendations and performance analysis.

The system transforms raw Strava data into actionable insights, providing riders with detailed understanding of their capabilities across different distances and intensities, ultimately enabling more informed route planning and training decisions.