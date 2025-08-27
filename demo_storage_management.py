#!/usr/bin/env python3
"""
Storage Management Demo for KOMpass.

This script demonstrates and helps manage the storage system including:
- S3 storage monitoring and FIFO cleanup
- Local to S3 data migration 
- Storage usage reporting
- Configuration verification

Usage:
    python demo_storage_management.py                    # Show storage status
    python demo_storage_management.py --migrate          # Migrate local data to S3
    python demo_storage_management.py --cleanup          # Force FIFO cleanup
    python demo_storage_management.py --monitor          # Detailed monitoring
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Any

# Add helper modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from helper.config.config import get_config
from helper.config.logging_config import setup_logging, get_logger
from helper.storage.storage_manager import get_storage_manager

logger = get_logger(__name__)


def print_banner():
    """Print application banner."""
    print("\n" + "="*60)
    print("  KOMpass Storage Management System")
    print("  S3 Cloud Storage with FIFO Management")
    print("="*60)


def print_storage_status(storage_manager):
    """Print comprehensive storage status."""
    print("\n📊 STORAGE STATUS")
    print("-" * 40)
    
    info = storage_manager.get_storage_info()
    
    print(f"Preferred Backend: {info['preferred_backend'].upper()}")
    print(f"Available Backends: {', '.join(info['backends_available'])}")
    print(f"S3 Enabled: {'✅' if info['s3_enabled'] else '❌'}")
    print(f"S3 Configured: {'✅' if info.get('s3_configured', False) else '❌'}")
    
    if info.get('s3_usage'):
        usage = info['s3_usage']
        print(f"\n🪣 S3 BUCKET USAGE")
        print(f"Bucket: {usage['bucket_name']}")
        print(f"Total Size: {usage['total_size_gb']:.3f} GB / {usage['max_size_gb']:.1f} GB")
        print(f"Usage: {usage['usage_percent']:.1f}%")
        print(f"Objects: {usage['total_objects']:,}")
        print(f"Users: {usage['user_count']}")
        print(f"Auto Cleanup: {'✅' if usage['cleanup_enabled'] else '❌'}")
        print(f"Cleanup Threshold: {usage['cleanup_threshold']}%")
        
        if usage['usage_percent'] >= 70:
            print(f"⚠️  WARNING: Approaching storage limit!")
        if usage['usage_percent'] >= 90:
            print(f"🚨 CRITICAL: Storage nearly full!")
    
    print(f"\n💾 LOCAL STORAGE")
    print(f"Directory: {info['local_directory']}")
    print(f"Exists: {'✅' if os.path.exists(info['local_directory']) else '❌'}")


def print_data_type_breakdown(storage_manager):
    """Print breakdown by data type."""
    info = storage_manager.get_storage_info()
    
    if info.get('s3_usage') and info['s3_usage'].get('data_type_stats'):
        print(f"\n📁 DATA TYPE BREAKDOWN")
        print("-" * 40)
        
        for data_type, stats in info['s3_usage']['data_type_stats'].items():
            size_mb = stats['size_bytes'] / (1024 * 1024)
            print(f"{data_type.title()}: {stats['count']} files, {size_mb:.2f} MB")


def migrate_data(storage_manager):
    """Migrate local data to S3."""
    print("\n🚚 MIGRATING LOCAL DATA TO S3")
    print("-" * 40)
    
    if not storage_manager.is_s3_enabled():
        print("❌ S3 not enabled - cannot migrate data")
        return False
    
    print("Starting migration...")
    results = storage_manager.migrate_local_to_s3()
    
    if results['success']:
        print(f"✅ Migration completed successfully!")
        print(f"   Files migrated: {results['migrated_files']}")
        print(f"   Failed files: {results['failed_files']}")
        print(f"   Total size: {results['total_size_mb']:.2f} MB")
        
        if results['errors']:
            print(f"\n⚠️  Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
    else:
        print(f"❌ Migration failed!")
        for error in results.get('errors', []):
            print(f"   Error: {error}")
    
    return results['success']


def force_cleanup(storage_manager):
    """Force FIFO cleanup for all users."""
    print("\n🧹 FORCING FIFO CLEANUP")
    print("-" * 40)
    
    if not storage_manager.is_s3_enabled():
        print("❌ S3 not enabled - cannot perform cleanup")
        return
    
    # This would require implementing a method to list all users
    # For now, show how it would work
    print("⚠️  Manual cleanup would require specific user IDs")
    print("Use the S3 console or AWS CLI for emergency cleanup:")
    print(f"   aws s3 ls s3://{storage_manager.config.s3.bucket_name}/users/")
    

def monitor_storage(storage_manager):
    """Detailed storage monitoring."""
    print("\n🔍 DETAILED STORAGE MONITORING")
    print("-" * 40)
    
    info = storage_manager.get_storage_info()
    
    # S3 monitoring
    if storage_manager.is_s3_enabled() and info.get('s3_usage'):
        usage = info['s3_usage']
        
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bucket Usage: {usage['usage_percent']:.1f}% ({usage['total_size_gb']:.3f} GB)")
        
        # Alert levels
        if usage['usage_percent'] >= 90:
            print("🚨 CRITICAL: Storage > 90% - Immediate action required!")
        elif usage['usage_percent'] >= 80:
            print("⚠️  WARNING: Storage > 80% - Monitor closely")
        elif usage['usage_percent'] >= 70:
            print("⚠️  INFO: Storage > 70% - FIFO cleanup active")
        else:
            print("✅ Storage levels normal")
        
        # Free tier monitoring
        free_tier_gb = 5.0
        if usage['total_size_gb'] > free_tier_gb * 0.9:
            print(f"⚠️  Approaching AWS free tier limit ({free_tier_gb} GB)")
    
    # Local storage check
    print(f"\nLocal Directory: {info['local_directory']}")
    if os.path.exists(info['local_directory']):
        try:
            # Calculate local storage usage
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(info['local_directory']):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.isfile(filepath):
                        total_size += os.path.getsize(filepath)
                        file_count += 1
            
            local_size_mb = total_size / (1024 * 1024)
            print(f"Local Usage: {file_count} files, {local_size_mb:.2f} MB")
            
            if local_size_mb > 10:
                print("💡 Consider migrating local data to S3")
            
        except Exception as e:
            print(f"Error calculating local usage: {e}")


def check_configuration():
    """Check and display configuration."""
    print("\n⚙️  CONFIGURATION CHECK")
    print("-" * 40)
    
    config = get_config()
    
    print(f"S3 Enabled: {'✅' if config.s3.enabled else '❌'}")
    if config.s3.enabled:
        print(f"Bucket: {config.s3.bucket_name or '❌ Not set'}")
        print(f"Region: {config.s3.aws_region}")
        print(f"Access Key: {'✅ Set' if config.s3.aws_access_key_id else '❌ Not set'}")
        print(f"Secret Key: {'✅ Set' if config.s3.aws_secret_access_key else '❌ Not set'}")
        print(f"Auto Cleanup: {'✅' if config.s3.auto_cleanup_enabled else '❌'}")
        print(f"Cleanup Threshold: {config.s3.cleanup_threshold_percent}%")
        print(f"Max User Storage: {config.s3.max_user_storage_mb} MB")
        print(f"Max Total Storage: {config.s3.max_total_storage_gb} GB")
    
    # Required environment variables
    required_env_vars = [
        "S3_STORAGE_ENABLED",
        "AWS_S3_BUCKET", 
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY"
    ]
    
    print(f"\nEnvironment Variables:")
    for var in required_env_vars:
        value = os.environ.get(var)
        status = "✅ Set" if value else "❌ Not set"
        print(f"  {var}: {status}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="KOMpass Storage Management")
    parser.add_argument('--migrate', action='store_true', 
                       help='Migrate local data to S3')
    parser.add_argument('--cleanup', action='store_true',
                       help='Force FIFO cleanup')
    parser.add_argument('--monitor', action='store_true',
                       help='Detailed storage monitoring')
    parser.add_argument('--config', action='store_true',
                       help='Check configuration')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging("INFO")
    
    print_banner()
    
    try:
        # Initialize storage manager
        storage_manager = get_storage_manager()
        
        # Configuration check
        if args.config or not any([args.migrate, args.cleanup, args.monitor]):
            check_configuration()
        
        # Show storage status
        if not args.config:
            print_storage_status(storage_manager)
            print_data_type_breakdown(storage_manager)
        
        # Perform specific actions
        if args.migrate:
            migrate_data(storage_manager)
        
        if args.cleanup:
            force_cleanup(storage_manager)
        
        if args.monitor:
            monitor_storage(storage_manager)
        
        print(f"\n✅ Storage management completed")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Storage management error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())