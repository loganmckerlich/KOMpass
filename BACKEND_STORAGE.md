# Backend Storage Documentation

## Overview

KOMpass now includes a comprehensive backend storage system that supports local, Amazon S3, and Firebase/Firestore storage with user data isolation, PII removal, and free tier compliance.

Firebase is **highly recommended** for Streamlit Community Cloud deployments due to its generous free tier and easy setup.

## Architecture

### Storage Manager
- **File**: `helper/storage/storage_manager.py`
- **Purpose**: Unified interface for local, S3, and Firebase storage backends
- **Features**: Automatic fallback, user data isolation, caching

### Firebase Storage Backend (Recommended)
- **File**: `helper/storage/firebase_storage.py`
- **Purpose**: Google Firebase/Firestore integration with generous free tier
- **Features**: 1GB free storage, 50k reads/day, no credit card required

### S3 Storage Backend
- **File**: `helper/storage/s3_storage.py`
- **Purpose**: Amazon S3 integration with proper error handling
- **Features**: Free tier compliance, file size limits, metadata tracking

### Configuration
- **File**: `helper/config/config.py` (extended)
- **Purpose**: Storage configuration management
- **Features**: Environment variable support, validation

## Data Organization

### Firebase Storage Structure (Recommended)
```
Firebase Firestore Collections:
├── users/{user_id}/routes/{doc_id}      # User route metadata
├── users/{user_id}/fitness/{doc_id}     # User fitness metadata
├── models/{doc_id}                      # Global ML model metadata
└── training_data/{doc_id}               # Global training metadata

Firebase Storage Bucket:
├── users/{user_id}/routes/{filename}    # User route files
├── users/{user_id}/fitness/{filename}   # User fitness files (PII removed)
├── models/{filename}                    # Global ML model files
└── training_data/{filename}             # Global training files
```

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

### Firebase Storage (Recommended for Streamlit Cloud)

Firebase offers several advantages over Amazon S3:
- **More generous free tier**: 1GB storage + 50k reads/day vs S3's 5GB + 20k requests/month
- **No credit card required** for free tier
- **Easier setup** for Streamlit Community Cloud
- **Real-time capabilities** for future features
- **Better for structured data** like routes and fitness metrics

```bash
# Enable Firebase storage
FIREBASE_STORAGE_ENABLED=true

# Firebase Configuration
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
FIREBASE_SERVICE_ACCOUNT_KEY=path/to/serviceAccountKey.json
# Or use JSON string for Streamlit secrets:
# FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# Storage Limits
FIREBASE_MAX_FILE_SIZE_MB=50
FIREBASE_MAX_USER_STORAGE_MB=100
```

### Amazon S3 Storage (Alternative)

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
For local development, simply set both `FIREBASE_STORAGE_ENABLED=false` and `S3_STORAGE_ENABLED=false` or omit the cloud storage environment variables. The system will automatically use local storage.

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
- Configuration loading (S3 + Firebase)
- Storage manager functionality
- PII removal
- Local storage operations
- S3 integration (when configured)
- Firebase integration (when configured)

## Setup Demos

### Firebase Setup
```bash
# View setup guide
python demo_firebase_setup.py --setup

# Test Firebase configuration
python demo_firebase_setup.py
```

### S3 Setup
```bash
# Test S3 configuration
python demo_s3_setup.py
```

## Free Tier Compliance

### Firebase Free Tier (Recommended)
- **Storage**: 1GB free
- **Reads**: 50,000/day free  
- **Writes**: 20,000/day free
- **No credit card required**
- **Real-time database capabilities**

### AWS S3 Free Tier (Alternative)
- **Storage**: 5GB free
- **GET Requests**: 20,000/month free
- **PUT Requests**: 2,000/month free
- **Credit card required**

Both systems include:
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
- **Backend Priority**: Firebase > S3 > Local (if multiple configured)

## Migration

### Existing Routes
Legacy routes in the `saved_routes/` directory are automatically accessible through the storage manager for backward compatibility.

### Data Migration
To migrate existing data or switch between backends:

1. **Firebase to S3**: Configure both backends, data will be accessible from both
2. **S3 to Firebase**: Configure both backends, new data saves to Firebase (preferred)
3. **Local to Cloud**: Configure cloud backend, existing local data remains accessible
4. Use the storage manager to explicitly migrate specific files if needed

## Security

- **User Isolation**: Data is stored with user-specific prefixes
- **PII Removal**: Automatic anonymization of sensitive data
- **Access Control**: User can only access their own data
- **Credential Management**: AWS credentials via environment variables
- **Data Integrity**: JSON validation and error checking