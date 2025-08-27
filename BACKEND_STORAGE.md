# Backend Storage Documentation

## Overview

KOMpass includes a comprehensive backend storage system that supports local and Amazon S3 storage with user data isolation, PII removal, and free tier compliance.

S3 is **recommended** for Streamlit Community Cloud deployments when cloud storage is desired.

## Architecture

### Storage Manager
- **File**: `helper/storage/storage_manager.py`
- **Purpose**: Unified interface for local and S3 storage backends
- **Features**: Automatic fallback, user data isolation, caching

### S3 Storage Backend
- **File**: `helper/storage/s3_storage.py`
- **Purpose**: Amazon S3 integration with proper error handling
- **Features**: Free tier compliance, file size limits, metadata tracking

### Configuration
- **File**: `helper/config/config.py` (extended)
- **Purpose**: Storage configuration management
- **Features**: Environment variable support, validation

## Data Organization

### S3 Bucket Structure
```
kompass-data/
├── models/           # Global ML models (accessible to all users)
├── training_data/    # Global training datasets
└── users/
    └── {user_id}/
        ├── routes/   # User-specific saved routes
        └── fitness/  # User fitness data (PII removed)
```

### Local Storage Structure
```
saved_routes/
├── routes/
│   ├── {filename}.json                    # Anonymous routes
│   └── {user_id}/
│       └── {filename}.json               # User-specific routes
├── fitness/
│   └── {user_id}/
│       └── fitness_data_{timestamp}.json # User fitness data
├── models/
│   └── {model_files}                     # Global ML models
└── training_data/
    └── {training_files}                  # Global training data
```

## Configuration

### Amazon S3 Storage (Recommended)

```bash
# Enable S3 storage
S3_STORAGE_ENABLED=true

# AWS Configuration
AWS_S3_BUCKET=your-kompass-bucket-name
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_REGION=us-east-1

# Storage Limits (free tier compliance)
S3_MAX_FILE_SIZE_MB=50
S3_MAX_USER_STORAGE_MB=100
```

### Local Development
For local development, simply set `S3_STORAGE_ENABLED=false` or omit the S3 environment variables. The system will automatically use local storage.

## Usage

### Route Storage
```python
from helper.storage.storage_manager import get_storage_manager

manager = get_storage_manager()

# Save user-specific route
success = manager.save_data(route_data, user_id, 'routes', 'my_route.json')

# Load user-specific route
route_data = manager.load_data(user_id, 'routes', 'my_route.json')

# List user routes
user_routes = manager.list_user_data(user_id, 'routes')
```

### Rider Data Storage (with PII removal)
```python
from helper.processing.rider_data_processor import RiderDataProcessor

processor = RiderDataProcessor(oauth_client)

# Save rider data (PII automatically removed)
success = processor.save_rider_data(rider_data, user_id)

# Load rider data
saved_data = processor.load_rider_data(user_id)

# Get rider data history
history = processor.get_rider_data_history(user_id)
```

## PII Removal

The system automatically removes personally identifiable information before storing rider data:

### Removed from Basic Info
- `firstname`, `lastname`
- `profile`, `profile_medium`
- `city`, `state`, `country`
- `email`, `premium`
- Account metadata

### Removed from Activities
- Activity names
- GPS coordinates (`start_latlng`, `end_latlng`)
- Location information
- Photos and maps
- Gear information

### Preserved Data
- Performance metrics (power, heart rate, speed)
- Training data (distance, time, elevation)
- Anonymized user hash for consistency
- Statistical information

## Testing

Run the backend storage test suite:

```bash
python test_backend_storage.py
```

Tests cover:
- Configuration loading (S3)
- Storage manager functionality
- PII removal
- Local storage operations
- S3 integration (when configured)

## Setup Demos

### S3 Setup
```bash
# Test S3 configuration
python demo_s3_setup.py
```

## Free Tier Compliance

### AWS S3 Free Tier
- **Storage**: 5GB free
- **GET Requests**: 20,000/month free
- **PUT Requests**: 2,000/month free
- **Credit card required**

The system includes:
- **File Size Limit**: 50MB per file (configurable)
- **User Storage Limit**: 100MB per user (configurable)
- **Request Optimization**: Efficient operations
- **Cleanup Policies**: Automatic old data management (future feature)

## Error Handling

- **Cloud Storage Unavailable**: Automatic fallback to local storage
- **Network Issues**: Graceful degradation
- **Permission Errors**: Clear error messages
- **File Size Limits**: Validation before upload
- **Storage Quotas**: User storage monitoring
- **Backend Priority**: S3 > Local (when configured)

## Migration

### Existing Routes
Legacy routes in the `saved_routes/` directory are automatically accessible through the storage manager for backward compatibility.

### Data Migration
To migrate existing data or switch between backends:

1. **S3 to Local**: Configure S3 backend, data will be accessible from both
2. **Local to S3**: Configure S3 backend, new data saves to S3 (preferred)
3. Use the storage manager to explicitly migrate specific files if needed

## Security

- **User Isolation**: Data is stored with user-specific prefixes
- **PII Removal**: Automatic anonymization of sensitive data
- **Access Control**: User can only access their own data
- **Credential Management**: AWS credentials via environment variables
- **Data Integrity**: JSON validation and error checking