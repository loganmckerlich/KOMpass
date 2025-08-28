# Backend Storage Documentation

## Overview

KOMpass includes a comprehensive backend storage system that supports local and Amazon S3 storage with user data isolation, PII removal, FIFO management, and AWS free tier compliance.

S3 is **recommended** for Streamlit Community Cloud deployments to maximize cloud storage usage and avoid local storage limits.

## Architecture

### Storage Manager
- **File**: `helper/storage/storage_manager.py`
- **Purpose**: Unified interface for local and S3 storage backends
- **Features**: S3 priority, automatic fallback, user data isolation, data migration

### S3 Storage Backend
- **File**: `helper/storage/s3_storage.py`
- **Purpose**: Amazon S3 integration with FIFO cleanup and monitoring
- **Features**: Automatic FIFO cleanup, free tier compliance, usage monitoring

### FIFO Storage Management
- **Automatic Cleanup**: Removes oldest files when storage approaches limits
- **Threshold**: Configurable cleanup at 70% of storage limit (default)
- **Preservation**: Keeps minimum number of files per user/data type
- **Monitoring**: Real-time bucket usage tracking and alerts

### Configuration
- **File**: `helper/config/config.py` (extended)
- **Purpose**: Storage configuration with FIFO settings
- **Features**: Environment variable support, validation, FIFO tuning

## Data Organization

### S3 Bucket Structure
```
kompass-data/
├── models/           # Global ML models (accessible to all users)
├── training_data/    # Global training datasets
└── users/
    └── {user_id}/
        ├── routes/   # User-specific saved routes (FIFO managed)
        └── fitness/  # User fitness data (PII removed, FIFO managed)
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

# FIFO Management Settings
S3_CLEANUP_THRESHOLD_PERCENT=70        # Start cleanup at 70% usage
S3_AUTO_CLEANUP_ENABLED=true           # Enable automatic FIFO cleanup
S3_MIN_FILES_TO_KEEP=5                 # Minimum files to preserve per user
S3_MAX_TOTAL_STORAGE_GB=4.5            # Max bucket size (90% of 5GB free tier)
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

## FIFO Storage Management

The system includes automatic FIFO (First In, First Out) cleanup to stay within AWS free tier limits and avoid charges.

### How FIFO Works
1. **Monitoring**: Continuous tracking of user and total bucket storage usage
2. **Threshold**: Cleanup triggers at 70% of storage limit (configurable)
3. **Selection**: Removes oldest files first, preserving newest data
4. **Preservation**: Always keeps minimum number of files per user/data type
5. **Safety**: Never removes more than half of files in one cleanup cycle

### Configuration
```bash
S3_CLEANUP_THRESHOLD_PERCENT=70    # Trigger cleanup at 70% usage
S3_AUTO_CLEANUP_ENABLED=true       # Enable automatic cleanup
S3_MIN_FILES_TO_KEEP=5             # Minimum files to preserve
S3_MAX_TOTAL_STORAGE_GB=4.5        # Total bucket limit (90% of 5GB)
```

### Monitoring and Management
```bash
# Check storage status and usage
python demo_storage_management.py

# Migrate local data to S3 (maximize cloud usage)
python demo_storage_management.py --migrate

# Detailed monitoring with alerts
python demo_storage_management.py --monitor

# Configuration verification
python demo_storage_management.py --config
```

### Storage Priority
1. **S3 First**: All data saved to S3 when available
2. **Local Cleanup**: Local copies removed after successful S3 upload
3. **Maximum Cloud Usage**: Prioritizes S3 to avoid Streamlit storage limits
4. **Fallback**: Local storage only when S3 unavailable

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

# Storage management and monitoring
python demo_storage_management.py
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
- **FIFO Cleanup**: Automatic old data removal at 70% usage
- **Total Bucket Limit**: 4.5GB (90% of 5GB free tier)
- **Usage Monitoring**: Real-time storage tracking and alerts

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
The system includes automatic migration tools to move data to S3:

```python
from helper.storage.storage_manager import get_storage_manager

manager = get_storage_manager()

# Migrate all local data to S3
results = manager.migrate_local_to_s3()

# Migrate specific user data
results = manager.migrate_local_to_s3(user_id="specific_user")
```

Command line migration:
```bash
# Migrate all local data to S3
python demo_storage_management.py --migrate
```

This automatically:
- Moves existing local data to S3
- Removes local copies after successful upload
- Avoids duplicates if data already exists in S3
- Maximizes cloud storage usage

1. **S3 to Local**: Configure S3 backend, data will be accessible from both
2. **Local to S3**: Configure S3 backend, new data saves to S3 (preferred)
3. Use the storage manager to explicitly migrate specific files if needed

## Security

- **User Isolation**: Data is stored with user-specific prefixes
- **PII Removal**: Automatic anonymization of sensitive data
- **Access Control**: User can only access their own data
- **Credential Management**: AWS credentials via environment variables
- **Data Integrity**: JSON validation and error checking