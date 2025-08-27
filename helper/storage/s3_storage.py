"""
S3 Storage Backend for KOMpass.
Handles Amazon S3 operations with user data isolation and free tier compliance.
"""

import boto3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, BinaryIO
from botocore.exceptions import ClientError, NoCredentialsError

from ..config.logging_config import get_logger, log_function_entry, log_function_exit

logger = get_logger(__name__)


class S3StorageBackend:
    """Amazon S3 storage backend with user data isolation."""
    
    def __init__(self, config):
        """
        Initialize S3 storage backend.
        
        Args:
            config: S3Config instance with AWS credentials and settings
        """
        self.config = config
        self.s3_client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize S3 client with configured credentials."""
        try:
            if not self.config.is_configured():
                logger.warning("S3 not properly configured - missing credentials or bucket")
                return
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config.aws_access_key_id,
                aws_secret_access_key=self.config.aws_secret_access_key,
                region_name=self.config.aws_region
            )
            
            # Test connection
            self._test_connection()
            logger.info(f"S3 client initialized successfully for bucket: {self.config.bucket_name}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            self.s3_client = None
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None
    
    def _test_connection(self):
        """Test S3 connection and bucket access."""
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            logger.debug(f"Successfully connected to S3 bucket: {self.config.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"S3 bucket does not exist: {self.config.bucket_name}")
            elif error_code == '403':
                logger.error(f"Access denied to S3 bucket: {self.config.bucket_name}")
            else:
                logger.error(f"Error accessing S3 bucket: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if S3 storage is available."""
        return self.s3_client is not None and self.config.is_configured()
    
    def _build_key(self, user_id: Optional[str], data_type: str, filename: str) -> str:
        """
        Build S3 object key with proper data organization.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            S3 object key
        """
        if user_id:
            # User-specific data
            return f"users/{user_id}/{data_type}/{filename}"
        else:
            # Global data (models, training data)
            return f"{data_type}/{filename}"
    
    def save_file(self, data: Any, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Save data to S3.
        
        Args:
            data: Data to save (dict for JSON, bytes for binary)
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "save_file", user_id=user_id, data_type=data_type, filename=filename)
        
        if not self.is_available():
            logger.error("S3 storage not available")
            return False
        
        try:
            key = self._build_key(user_id, data_type, filename)
            
            # Convert data to appropriate format
            if isinstance(data, dict):
                content = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')
                content_type = 'application/json'
            elif isinstance(data, bytes):
                content = data
                content_type = 'application/octet-stream'
            elif isinstance(data, str):
                content = data.encode('utf-8')
                content_type = 'text/plain'
            else:
                content = str(data).encode('utf-8')
                content_type = 'text/plain'
            
            # Check file size limits
            size_mb = len(content) / (1024 * 1024)
            if size_mb > self.config.max_file_size_mb:
                logger.error(f"File too large: {size_mb:.2f}MB > {self.config.max_file_size_mb}MB")
                return False
            
            # Add metadata
            metadata = {
                'upload_timestamp': datetime.now().isoformat(),
                'data_type': data_type,
                'kompass_version': '1.0'
            }
            if user_id:
                metadata['user_id'] = user_id
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type,
                Metadata=metadata
            )
            
            logger.info(f"Successfully saved file to S3: {key} ({size_mb:.2f}MB)")
            log_function_exit(logger, "save_file", f"success=True, key=key")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save file to S3: {e}")
            log_function_exit(logger, "save_file", f"success=False, error={str(e)}")
            return False
    
    def load_file(self, user_id: Optional[str], data_type: str, filename: str) -> Optional[Any]:
        """
        Load data from S3.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Loaded data or None if not found
        """
        log_function_entry(logger, "load_file", user_id=user_id, data_type=data_type, filename=filename)
        
        if not self.is_available():
            logger.error("S3 storage not available")
            return None
        
        try:
            key = self._build_key(user_id, data_type, filename)
            
            response = self.s3_client.get_object(
                Bucket=self.config.bucket_name,
                Key=key
            )
            
            content = response['Body'].read()
            content_type = response.get('ContentType', '')
            
            # Parse content based on type
            if content_type == 'application/json':
                data = json.loads(content.decode('utf-8'))
            elif content_type == 'text/plain':
                data = content.decode('utf-8')
            else:
                data = content  # Return as bytes
            
            logger.debug(f"Successfully loaded file from S3: {key}")
            log_function_exit(logger, "load_file", f"success=True, key=key")
            return data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.debug(f"File not found in S3: {self._build_key(user_id, data_type, filename)}")
            else:
                logger.error(f"Failed to load file from S3: {e}")
            log_function_exit(logger, "load_file", f"success={False}, error={error_code}")
            return None
        except Exception as e:
            logger.error(f"Failed to load file from S3: {e}")
            log_function_exit(logger, "load_file", f"success=False, error={str(e)}")
            return None
    
    def list_files(self, user_id: Optional[str], data_type: str) -> List[Dict[str, Any]]:
        """
        List files in S3 for a user and data type.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            
        Returns:
            List of file information
        """
        log_function_entry(logger, "list_files", user_id=user_id, data_type=data_type)
        
        if not self.is_available():
            logger.error("S3 storage not available")
            return []
        
        try:
            prefix = self._build_key(user_id, data_type, "")
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            files = []
            for obj in response.get('Contents', []):
                # Extract filename from key
                filename = obj['Key'].split('/')[-1]
                if filename:  # Skip directory markers
                    files.append({
                        'filename': filename,
                        'key': obj['Key'],
                        'size_bytes': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'size_mb': round(obj['Size'] / (1024 * 1024), 2)
                    })
            
            logger.debug(f"Listed {len(files)} files from S3 prefix: {prefix}")
            log_function_exit(logger, "list_files", f"success=True, count=len(files")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files from S3: {e}")
            log_function_exit(logger, "list_files", f"success=False, error={str(e)}")
            return []
    
    def delete_file(self, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "delete_file", user_id=user_id, data_type=data_type, filename=filename)
        
        if not self.is_available():
            logger.error("S3 storage not available")
            return False
        
        try:
            key = self._build_key(user_id, data_type, filename)
            
            self.s3_client.delete_object(
                Bucket=self.config.bucket_name,
                Key=key
            )
            
            logger.info(f"Successfully deleted file from S3: {key}")
            log_function_exit(logger, "delete_file", f"success=True, key=key")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file from S3: {e}")
            log_function_exit(logger, "delete_file", f"success=False, error={str(e)}")
            return False
    
    def get_user_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage usage statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Storage usage information
        """
        log_function_entry(logger, "get_user_storage_usage", user_id=user_id)
        
        if not self.is_available():
            logger.error("S3 storage not available")
            return {}
        
        try:
            prefix = f"users/{user_id}/"
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            
            total_size = 0
            file_count = 0
            data_types = {}
            
            for obj in response.get('Contents', []):
                total_size += obj['Size']
                file_count += 1
                
                # Extract data type from key
                key_parts = obj['Key'].split('/')
                if len(key_parts) >= 3:
                    data_type = key_parts[2]
                    if data_type not in data_types:
                        data_types[data_type] = {'count': 0, 'size_bytes': 0}
                    data_types[data_type]['count'] += 1
                    data_types[data_type]['size_bytes'] += obj['Size']
            
            usage_info = {
                'user_id': user_id,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'data_types': data_types,
                'limit_mb': self.config.max_user_storage_mb,
                'usage_percent': round((total_size / (1024 * 1024)) / self.config.max_user_storage_mb * 100, 2)
            }
            
            logger.debug(f"User storage usage: {usage_info['total_size_mb']}MB / {usage_info['limit_mb']}MB")
            log_function_exit(logger, "get_user_storage_usage", f"success=True, usage_mb={usage_info['total_size_mb']}")
            return usage_info
            
        except Exception as e:
            logger.error(f"Failed to get user storage usage: {e}")
            log_function_exit(logger, "get_user_storage_usage", f"success=False, error={str(e)}")
            return {}