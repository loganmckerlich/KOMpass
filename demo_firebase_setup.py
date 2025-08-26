#!/usr/bin/env python3
"""
Firebase Setup and Demo for KOMpass Backend Storage

This script demonstrates how to set up and use Firebase/Firestore storage
as an alternative to Amazon S3 for KOMpass deployments, especially for
Streamlit Community Cloud.

Firebase offers several advantages over S3:
- More generous free tier (1GB storage, 50k reads/day)
- No credit card required for free tier
- Easier setup for Streamlit Cloud
- Better suited for structured data
- Real-time capabilities

Usage:
    python demo_firebase_setup.py

Environment Variables Required:
    FIREBASE_STORAGE_ENABLED=true
    FIREBASE_PROJECT_ID=your-firebase-project-id
    FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
    FIREBASE_SERVICE_ACCOUNT_KEY=path/to/serviceAccountKey.json
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Add the helper module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helper.config.config import get_config
from helper.storage.storage_manager import get_storage_manager
from helper.config.logging_config import setup_logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_firebase_setup():
    """Check if Firebase is properly configured."""
    print("🔥 Firebase Storage Setup Check")
    print("=" * 50)
    
    config = get_config()
    
    # Check configuration
    print(f"Firebase Enabled: {config.firebase.enabled}")
    print(f"Project ID: {config.firebase.project_id}")
    print(f"Storage Bucket: {config.firebase.storage_bucket}")
    print(f"Service Account Key Path: {config.firebase.service_account_key_path}")
    print(f"Service Account Key JSON: {'Set' if config.firebase.service_account_key_json else 'Not set'}")
    print(f"Is Configured: {config.firebase.is_configured()}")
    
    if not config.firebase.enabled:
        print("❌ Firebase storage is disabled")
        print("   Set FIREBASE_STORAGE_ENABLED=true in your environment")
        return False
    
    if not config.firebase.is_configured():
        print("❌ Firebase storage is not properly configured")
        print("   Missing required environment variables:")
        if not config.firebase.project_id:
            print("   - FIREBASE_PROJECT_ID")
        if not config.firebase.storage_bucket:
            print("   - FIREBASE_STORAGE_BUCKET")
        if not config.firebase.service_account_key_path and not config.firebase.service_account_key_json:
            print("   - FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_JSON")
        return False
    
    print("✅ Firebase configuration looks good!")
    return True


def test_firebase_connection():
    """Test Firebase connection and basic operations."""
    print("\n🧪 Testing Firebase Connection")
    print("=" * 50)
    
    try:
        storage_manager = get_storage_manager()
        
        if not storage_manager.is_firebase_enabled():
            print("❌ Firebase storage is not available")
            print("   Check your configuration and Firebase credentials")
            return False
        
        print("✅ Firebase storage backend is available!")
        
        # Test basic operations
        test_user_id = "demo_user_123"
        test_data = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "Firebase demo test data"
        }
        
        # Test save
        print(f"📤 Testing save operation...")
        success = storage_manager.save_data(
            data=test_data,
            user_id=test_user_id,
            data_type="routes",
            filename="firebase_test.json"
        )
        
        if success:
            print("✅ Save operation successful!")
        else:
            print("❌ Save operation failed!")
            return False
        
        # Test load
        print(f"📥 Testing load operation...")
        loaded_data = storage_manager.load_data(
            user_id=test_user_id,
            data_type="routes",
            filename="firebase_test.json"
        )
        
        if loaded_data:
            print("✅ Load operation successful!")
            print(f"   Loaded data: {loaded_data}")
        else:
            print("❌ Load operation failed!")
            return False
        
        # Test list
        print(f"📋 Testing list operation...")
        user_files = storage_manager.list_user_data(test_user_id, "routes")
        print(f"✅ Found {len(user_files)} files for user")
        
        for file_info in user_files:
            print(f"   - {file_info['filename']} ({file_info['size_mb']} MB, {file_info['backend']})")
        
        # Test delete
        print(f"🗑️  Testing delete operation...")
        success = storage_manager.delete_data(
            user_id=test_user_id,
            data_type="routes",
            filename="firebase_test.json"
        )
        
        if success:
            print("✅ Delete operation successful!")
        else:
            print("❌ Delete operation failed!")
            return False
        
        print("🎉 All Firebase operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Firebase test failed: {e}")
        return False


def get_storage_info():
    """Display storage backend information."""
    print("\n📊 Storage Backend Information")
    print("=" * 50)
    
    try:
        storage_manager = get_storage_manager()
        info = storage_manager.get_storage_info()
        
        print(f"Preferred Backend: {info['preferred_backend']}")
        print(f"Available Backends: {', '.join(info['backends_available'])}")
        print()
        
        print("Firebase Status:")
        print(f"  Enabled: {info['firebase_enabled']}")
        print(f"  Configured: {info['firebase_configured']}")
        if info['firebase_enabled']:
            print(f"  Project: {info.get('firebase_project', 'N/A')}")
            print(f"  Bucket: {info.get('firebase_bucket', 'N/A')}")
        
        print("\nS3 Status:")
        print(f"  Enabled: {info['s3_enabled']}")
        print(f"  Configured: {info['s3_configured']}")
        if info['s3_enabled']:
            print(f"  Bucket: {info.get('s3_bucket', 'N/A')}")
            print(f"  Region: {info.get('s3_region', 'N/A')}")
        
        print(f"\nLocal Storage: {info['local_directory']}")
        
    except Exception as e:
        print(f"❌ Failed to get storage info: {e}")


def firebase_setup_guide():
    """Display Firebase setup guide."""
    print("\n📖 Firebase Setup Guide")
    print("=" * 50)
    
    print("""
Firebase offers a more generous free tier than AWS S3 and is perfect for
Streamlit Community Cloud deployments. Here's how to set it up:

1. 🚀 Create Firebase Project
   - Go to https://console.firebase.google.com/
   - Click "Create a project"
   - Follow the setup wizard

2. 🔧 Enable Storage
   - In your Firebase project, go to "Storage"
   - Click "Get started"
   - Choose "Start in production mode" for security

3. 🔑 Create Service Account
   - Go to Project Settings > Service accounts
   - Click "Generate new private key"
   - Download the JSON file

4. 🌐 For Streamlit Community Cloud
   Option A: Upload JSON file to your repo (NOT RECOMMENDED for security)
   Option B: Use Streamlit secrets (RECOMMENDED)
   
   In your Streamlit app secrets, add:
   ```
   [firebase]
   project_id = "your-project-id"
   storage_bucket = "your-project-id.appspot.com"
   service_account_key = '''
   {
     "type": "service_account",
     "project_id": "your-project-id",
     ...rest of your service account key JSON...
   }
   '''
   ```

5. 📝 Environment Variables
   Set these in your .env file or Streamlit secrets:
   ```
   FIREBASE_STORAGE_ENABLED=true
   FIREBASE_PROJECT_ID=your-firebase-project-id
   FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
   FIREBASE_SERVICE_ACCOUNT_JSON='{...service account key JSON...}'
   ```

6. ✨ Firebase Benefits
   - 1GB free storage (vs 5GB for S3, but more operations)
   - 50,000 reads/day free
   - 20,000 writes/day free
   - No credit card required
   - Real-time capabilities
   - Better for structured data

7. 🔒 Security Rules
   Make sure your Firebase Storage rules allow authenticated access:
   ```
   rules_version = '2';
   service firebase.storage {
     match /b/{bucket}/o {
       match /{allPaths=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```
""")


def main():
    """Main demo function."""
    print("🔥 KOMpass Firebase Storage Setup & Demo")
    print("=" * 60)
    
    # Check if this is a setup check or full demo
    if len(sys.argv) > 1 and sys.argv[1] == "--setup":
        firebase_setup_guide()
        return
    
    # Run setup check
    if not check_firebase_setup():
        print("\n❌ Firebase setup incomplete!")
        print("Run 'python demo_firebase_setup.py --setup' for setup guide")
        return
    
    # Test Firebase operations
    if test_firebase_connection():
        print("\n🎉 Firebase setup is working perfectly!")
    else:
        print("\n❌ Firebase setup has issues")
        return
    
    # Display storage info
    get_storage_info()
    
    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("1. Your Firebase storage is ready to use!")
    print("2. KOMpass will automatically use Firebase as the preferred backend")
    print("3. Data will be organized with user isolation for privacy")
    print("4. PII will be automatically removed from fitness data")
    print("5. Deploy to Streamlit Community Cloud with confidence!")
    print("\n💡 Tip: Firebase is free, reliable, and perfect for Streamlit Cloud!")


if __name__ == "__main__":
    main()