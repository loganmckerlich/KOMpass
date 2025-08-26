#!/usr/bin/env python3
"""
Test script for KOMpass backend storage system.
Tests local storage, S3, Firebase configuration, and PII removal.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_storage_manager():
    """Test storage manager functionality."""
    print("Testing Storage Manager...")
    
    try:
        from helper.storage.storage_manager import get_storage_manager
        
        manager = get_storage_manager()
        
        # Test data
        test_data = {
            'test_key': 'test_value',
            'timestamp': datetime.now().isoformat(),
            'data': [1, 2, 3, 4, 5]
        }
        
        # Test saving data
        success = manager.save_data(test_data, 'test_user', 'routes', 'test_file.json')
        assert success, "Failed to save test data"
        print("✓ Data saving successful")
        
        # Test loading data
        loaded_data = manager.load_data('test_user', 'routes', 'test_file.json')
        assert loaded_data is not None, "Failed to load test data"
        assert loaded_data['test_key'] == 'test_value', "Data integrity check failed"
        print("✓ Data loading successful")
        
        # Test listing files
        files = manager.list_user_data('test_user', 'routes')
        assert len(files) > 0, "No files found"
        print(f"✓ Found {len(files)} user files")
        
        # Test storage info
        info = manager.get_storage_info()
        assert 'local' in info['backends_available'], "Local backend not available"
        print("✓ Storage info retrieval successful")
        
        print("Storage Manager: ALL TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"Storage Manager: TEST FAILED ✗ - {e}")
        return False

def test_pii_removal():
    """Test PII removal functionality."""
    print("\nTesting PII Removal...")
    
    try:
        from helper.processing.rider_data_processor import RiderDataProcessor
        
        # Mock OAuth client for testing
        class MockOAuthClient:
            pass
        
        processor = RiderDataProcessor(MockOAuthClient())
        
        # Test data with PII
        test_data = {
            'basic_info': {
                'id': 123456789,
                'firstname': 'John',
                'lastname': 'Doe',
                'email': 'john@example.com',
                'city': 'San Francisco',
                'sex': 'M',
                'weight': 75.0,
                'ftp': 250
            },
            'recent_activities': [
                {
                    'name': 'Secret Ride',
                    'distance': 25000,
                    'start_latlng': [37.7749, -122.4194],
                    'location_city': 'San Francisco',
                    'average_watts': 200
                }
            ]
        }
        
        # Remove PII
        sanitized = processor.remove_pii_from_rider_data(test_data)
        
        # Check PII removal
        assert 'firstname' not in sanitized['basic_info'], "First name not removed"
        assert 'lastname' not in sanitized['basic_info'], "Last name not removed"
        assert 'email' not in sanitized['basic_info'], "Email not removed"
        assert 'city' not in sanitized['basic_info'], "City not removed"
        assert 'user_hash' in sanitized['basic_info'], "User hash not generated"
        print("✓ Basic info PII removal successful")
        
        # Check activity PII removal
        activity = sanitized['recent_activities'][0]
        assert 'name' not in activity, "Activity name not removed"
        assert 'start_latlng' not in activity, "GPS coordinates not removed"
        assert 'location_city' not in activity, "Location city not removed"
        assert 'distance' in activity, "Distance incorrectly removed"
        assert 'average_watts' in activity, "Power data incorrectly removed"
        print("✓ Activity PII removal successful")
        
        # Check metadata
        assert sanitized['anonymization']['pii_removed'] == True, "PII removal flag not set"
        print("✓ Anonymization metadata successful")
        
        print("PII Removal: ALL TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"PII Removal: TEST FAILED ✗ - {e}")
        return False

def test_configuration():
    """Test configuration loading."""
    print("\nTesting Configuration...")
    
    try:
        from helper.config.config import get_config
        
        config = get_config()
        
        # Test S3 config
        assert hasattr(config, 's3'), "S3 config not available"
        assert hasattr(config.s3, 'enabled'), "S3 enabled flag not available"
        assert hasattr(config.s3, 'bucket_name'), "S3 bucket name not available"
        print("✓ S3 configuration structure valid")
        
        # Test Firebase config
        assert hasattr(config, 'firebase'), "Firebase config not available"
        assert hasattr(config.firebase, 'enabled'), "Firebase enabled flag not available"
        assert hasattr(config.firebase, 'project_id'), "Firebase project ID not available"
        print("✓ Firebase configuration structure valid")
        
        # Test validation
        validation = config.validate_configuration()
        assert isinstance(validation, dict), "Configuration validation failed"
        print("✓ Configuration validation successful")
        
        print("Configuration: ALL TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"Configuration: TEST FAILED ✗ - {e}")
        return False

def test_firebase_backend():
    """Test Firebase storage backend if available."""
    print("\nTesting Firebase Backend...")
    
    try:
        from helper.storage.firebase_storage import FirebaseStorageBackend, FIREBASE_AVAILABLE
        from helper.config.config import get_config
        
        if not FIREBASE_AVAILABLE:
            print("⚠️  Firebase SDK not available - skipping Firebase tests")
            return True
        
        config = get_config()
        
        if not config.firebase.enabled:
            print("⚠️  Firebase disabled - skipping Firebase tests")
            return True
        
        if not config.firebase.is_configured():
            print("⚠️  Firebase not configured - skipping Firebase tests")
            return True
        
        # Test Firebase backend
        backend = FirebaseStorageBackend(config.firebase)
        
        if not backend.is_available():
            print("⚠️  Firebase backend not available - skipping Firebase tests")
            return True
        
        print("✓ Firebase backend initialization successful")
        
        # Test basic operations
        test_data = {'test': 'firebase_data', 'timestamp': datetime.now().isoformat()}
        
        # Test save
        success = backend.save_file(test_data, 'test_user', 'routes', 'firebase_test.json')
        if success:
            print("✓ Firebase save operation successful")
        else:
            print("❌ Firebase save operation failed")
            return False
        
        # Test load
        loaded = backend.load_file('test_user', 'routes', 'firebase_test.json')
        if loaded and loaded.get('test') == 'firebase_data':
            print("✓ Firebase load operation successful")
        else:
            print("❌ Firebase load operation failed")
            return False
        
        # Test list
        files = backend.list_files('test_user', 'routes')
        if any(f['filename'] == 'firebase_test.json' for f in files):
            print("✓ Firebase list operation successful")
        else:
            print("❌ Firebase list operation failed")
            return False
        
        # Test delete
        success = backend.delete_file('test_user', 'routes', 'firebase_test.json')
        if success:
            print("✓ Firebase delete operation successful")
        else:
            print("❌ Firebase delete operation failed")
            return False
        
        print("Firebase Backend: ALL TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"Firebase Backend: TEST FAILED ✗ - {e}")
        return False

def main():
    """Run all tests."""
    print("KOMpass Backend Storage Test Suite")
    print("=" * 40)
    
    results = []
    
    # Run tests
    results.append(test_configuration())
    results.append(test_storage_manager())
    results.append(test_pii_removal())
    results.append(test_firebase_backend())
    
    # Summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY")
    print("=" * 40)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"ALL TESTS PASSED: {passed}/{total} ✓")
        print("\n✨ Backend storage system is working correctly!")
        return 0
    else:
        print(f"TESTS FAILED: {passed}/{total} ✗")
        print("\n❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    exit(main())