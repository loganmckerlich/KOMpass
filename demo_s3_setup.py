#!/usr/bin/env python3
"""
S3 Configuration Demo for KOMpass.
Demonstrates how to configure and test S3 storage.
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def demo_s3_configuration():
    """Demonstrate S3 configuration options."""
    print("S3 Configuration Demo")
    print("=" * 30)
    
    print("\n1. Environment Variables Setup")
    print("Add these to your .env file or environment:")
    print("""
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
""")
    
    print("\n2. AWS S3 Bucket Setup")
    print("Create an S3 bucket with these settings:")
    print("- Bucket name: kompass-data (or your chosen name)")
    print("- Region: us-east-1 (or your preferred region)")
    print("- Block public access: ENABLED (for security)")
    print("- Versioning: OPTIONAL (recommended for production)")
    
    print("\n3. IAM User Setup")
    print("Create an IAM user with these permissions:")
    print("""
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-kompass-bucket-name",
                "arn:aws:s3:::your-kompass-bucket-name/*"
            ]
        }
    ]
}
""")

def demo_current_configuration():
    """Show current configuration status."""
    print("\n4. Current Configuration Status")
    print("-" * 30)
    
    try:
        from helper.config.config import get_config
        
        config = get_config()
        
        print(f"S3 Enabled: {config.s3.enabled}")
        print(f"S3 Configured: {config.s3.is_configured()}")
        print(f"S3 Bucket: {config.s3.bucket_name or 'Not set'}")
        print(f"S3 Region: {config.s3.aws_region}")
        print(f"Max File Size: {config.s3.max_file_size_mb}MB")
        print(f"Max User Storage: {config.s3.max_user_storage_mb}MB")
        
        # Test storage manager
        from helper.storage.storage_manager import get_storage_manager
        manager = get_storage_manager()
        storage_info = manager.get_storage_info()
        
        print(f"\nAvailable Backends: {', '.join(storage_info['backends_available'])}")
        
        if config.s3.enabled and not config.s3.is_configured():
            print("\n⚠️  S3 is enabled but not properly configured!")
            print("   Please check your AWS credentials and bucket name.")
        elif config.s3.enabled and config.s3.is_configured():
            print("\n✅ S3 is enabled and configured!")
            print("   New data will be stored in S3 with local fallback.")
        else:
            print("\n📁 Using local storage only.")
            print("   Set S3_STORAGE_ENABLED=true to enable S3 storage.")
            
    except Exception as e:
        print(f"Error checking configuration: {e}")

def demo_data_flow():
    """Demonstrate data flow and organization."""
    print("\n5. Data Flow and Organization")
    print("-" * 30)
    
    print("\nData Types and Storage Locations:")
    print("• User Routes: users/{user_id}/routes/")
    print("• User Fitness Data: users/{user_id}/fitness/ (PII removed)")
    print("• ML Models: models/ (global access)")
    print("• Training Data: training_data/ (global access)")
    
    print("\nData Flow:")
    print("1. User uploads route → Storage Manager")
    print("2. Storage Manager tries S3 first (if enabled)")
    print("3. Falls back to local storage if S3 fails")
    print("4. Data isolated by user ID for privacy")
    
    print("\nPII Removal (for rider data):")
    print("• Removes: names, emails, locations, GPS coordinates")
    print("• Keeps: performance metrics, training data")
    print("• Generates: anonymous user hash for consistency")

def main():
    """Run the S3 configuration demo."""
    demo_s3_configuration()
    demo_current_configuration()
    demo_data_flow()
    
    print("\n" + "=" * 50)
    print("NEXT STEPS")
    print("=" * 50)
    print("1. Create AWS S3 bucket and IAM user")
    print("2. Set environment variables in .env file")
    print("3. Run: python test_backend_storage.py")
    print("4. Start using KOMpass with backend storage!")
    print("\nFor detailed documentation, see: BACKEND_STORAGE.md")

if __name__ == "__main__":
    main()