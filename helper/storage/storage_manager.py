"""
Storage Manager for KOMpass.
Provides unified interface for local and S3 storage backends.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import hashlib

from ..config.config import get_config
from ..config.logging_config import get_logger, log_function_entry, log_function_exit
from .s3_storage import S3StorageBackend

logger = get_logger(__name__)


class StorageManager:
    """Unified storage manager supporting local and S3 backends."""
    
    def __init__(self):
        """Initialize storage manager with appropriate backend."""
        self.config = get_config()
        self.local_data_dir = self.config.app.data_directory
        self.s3_backend = None
        
        # Initialize S3 backend if configured
        if self.config.s3.enabled:
            self.s3_backend = S3StorageBackend(self.config.s3)
        
        self._ensure_local_directories()
        
        logger.info(f"Storage manager initialized - S3: {self.is_s3_enabled()}, Local: {self.local_data_dir}")
    
    def _ensure_local_directories(self):
        """Ensure local data directories exist."""
        try:
            os.makedirs(self.local_data_dir, exist_ok=True)
            # Create subdirectories for data organization
            for subdir in ['routes', 'fitness', 'models', 'training_data']:
                os.makedirs(os.path.join(self.local_data_dir, subdir), exist_ok=True)
            logger.debug(f"Local directories ensured: {self.local_data_dir}")
        except Exception as e:
            logger.error(f"Failed to create local directories: {e}")
    
    def is_s3_enabled(self) -> bool:
        """Check if S3 storage is enabled and available."""
        return (
            self.config.s3.enabled and 
            self.s3_backend is not None and 
            self.s3_backend.is_available()
        )
    
    def _get_local_filepath(self, user_id: Optional[str], data_type: str, filename: str) -> str:
        """Build local file path with proper organization."""
        if user_id:
            # User-specific data in subdirectories
            user_dir = os.path.join(self.local_data_dir, data_type, user_id)
            os.makedirs(user_dir, exist_ok=True)
            return os.path.join(user_dir, filename)
        else:
            # Global data in type-specific directories
            return os.path.join(self.local_data_dir, data_type, filename)
    
    def save_data(self, data: Any, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Save data using preferred backend (S3 if available, local fallback).
        
        Args:
            data: Data to save (dict, string, or bytes)
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "save_data", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename,
            backend="s3" if self.is_s3_enabled() else "local"
        )
        
        success = False
        
        # Try S3 first if enabled
        if self.is_s3_enabled():
            success = self.s3_backend.save_file(data, user_id, data_type, filename)
            if success:
                logger.info(f"Data saved to S3: {data_type}/{filename}")
                log_function_exit(logger, "save_data", "success-s3")
                return True
            else:
                logger.warning("S3 save failed, falling back to local storage")
        
        # Fallback to local storage
        success = self._save_local(data, user_id, data_type, filename)
        backend = "local"
        
        if success:
            logger.info(f"Data saved locally: {data_type}/{filename}")
        else:
            logger.error(f"Failed to save data: {data_type}/{filename}")
        
        log_function_exit(logger, "save_data", f"success={success}, backend={backend}")
        return success
    
    def _save_local(self, data: Any, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """Save data to local storage."""
        try:
            filepath = self._get_local_filepath(user_id, data_type, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            if isinstance(data, dict):
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            elif isinstance(data, bytes):
                with open(filepath, 'wb') as f:
                    f.write(data)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(str(data))
            
            logger.debug(f"Saved to local file: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save local file: {e}")
            return False
    
    def load_data(self, user_id: Optional[str], data_type: str, filename: str) -> Optional[Any]:
        """
        Load data from available backend.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Loaded data or None if not found
        """
        log_function_entry(logger, "load_data", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename
        )
        
        # Try S3 first if enabled
        if self.is_s3_enabled():
            data = self.s3_backend.load_file(user_id, data_type, filename)
            if data is not None:
                logger.debug(f"Data loaded from S3: {data_type}/{filename}")
                log_function_exit(logger, "load_data", "success=True, backend=s3")
                return data
        
        # Fallback to local storage
        data = self._load_local(user_id, data_type, filename)
        backend = "local" if data is not None else "not_found"
        
        if data is not None:
            logger.debug(f"Data loaded locally: {data_type}/{filename}")
        else:
            logger.debug(f"Data not found: {data_type}/{filename}")
        
        log_function_exit(logger, "load_data", f"success={data is not None}, backend={backend}")
        return data
    
    def _load_local(self, user_id: Optional[str], data_type: str, filename: str) -> Optional[Any]:
        """Load data from local storage."""
        try:
            filepath = self._get_local_filepath(user_id, data_type, filename)
            
            if not os.path.exists(filepath):
                return None
            
            # Determine file type and load appropriately
            if filename.endswith('.json'):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Try to read as text first, fallback to bytes
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return f.read()
                except UnicodeDecodeError:
                    with open(filepath, 'rb') as f:
                        return f.read()
            
        except Exception as e:
            logger.error(f"Failed to load local file: {e}")
            return None
    
    def list_user_data(self, user_id: str, data_type: str) -> List[Dict[str, Any]]:
        """
        List data files for a user and data type.
        
        Args:
            user_id: User ID
            data_type: Type of data (routes, fitness, models, training_data)
            
        Returns:
            List of file information
        """
        log_function_entry(logger, "list_user_data", user_id=user_id, data_type=data_type)
        
        files = []
        
        # Get from S3 if enabled
        if self.is_s3_enabled():
            files = self.s3_backend.list_files(user_id, data_type)
            logger.debug(f"Listed {len(files)} files from S3")
        
        # Merge with local files if S3 not available or as backup
        local_files = self._list_local_files(user_id, data_type)
        
        # Merge and deduplicate
        file_dict = {f['filename']: f for f in files}
        for local_file in local_files:
            if local_file['filename'] not in file_dict:
                file_dict[local_file['filename']] = local_file
        
        result = list(file_dict.values())
        result.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
        
        log_function_exit(logger, "list_user_data", f"success=True, count={len(result)}")
        return result
    
    def _list_local_files(self, user_id: Optional[str], data_type: str) -> List[Dict[str, Any]]:
        """List files from local storage."""
        files = []
        try:
            if user_id:
                directory = os.path.join(self.local_data_dir, data_type, user_id)
            else:
                directory = os.path.join(self.local_data_dir, data_type)
            
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        stat = os.stat(filepath)
                        files.append({
                            'filename': filename,
                            'filepath': filepath,
                            'size_bytes': stat.st_size,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'backend': 'local'
                        })
        except Exception as e:
            logger.error(f"Failed to list local files: {e}")
        
        return files
    
    def delete_data(self, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Delete data from storage.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "delete_data", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename
        )
        
        success = True
        
        # Delete from S3 if enabled
        if self.is_s3_enabled():
            s3_success = self.s3_backend.delete_file(user_id, data_type, filename)
            if s3_success:
                logger.info(f"Data deleted from S3: {data_type}/{filename}")
        
        # Also delete from local storage
        local_success = self._delete_local(user_id, data_type, filename)
        if local_success:
            logger.info(f"Data deleted locally: {data_type}/{filename}")
        
        # Consider it successful if deleted from at least one location
        overall_success = (
            (self.is_s3_enabled() and s3_success) or 
            local_success
        )
        
        log_function_exit(logger, "delete_data", f"success={overall_success}")
        return overall_success
    
    def _delete_local(self, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """Delete data from local storage."""
        try:
            filepath = self._get_local_filepath(user_id, data_type, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Deleted local file: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete local file: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage backend information and status."""
        info = {
            "s3_enabled": self.is_s3_enabled(),
            "s3_configured": self.config.s3.is_configured() if self.config.s3.enabled else False,
            "local_directory": self.local_data_dir,
            "backends_available": []
        }
        
        if self.is_s3_enabled():
            info["backends_available"].append("s3")
            info["s3_bucket"] = self.config.s3.bucket_name
            info["s3_region"] = self.config.s3.aws_region
        
        info["backends_available"].append("local")
        
        return info
    
    def get_user_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage usage for a user across all backends.
        
        Args:
            user_id: User ID
            
        Returns:
            Storage usage information
        """
        log_function_entry(logger, "get_user_storage_usage", user_id=user_id)
        
        usage = {
            "user_id": user_id,
            "total_size_mb": 0,
            "backends": {}
        }
        
        # Get S3 usage if enabled
        if self.is_s3_enabled():
            s3_usage = self.s3_backend.get_user_storage_usage(user_id)
            if s3_usage:
                usage["backends"]["s3"] = s3_usage
                usage["total_size_mb"] += s3_usage.get("total_size_mb", 0)
        
        # Get local usage
        local_usage = self._get_local_storage_usage(user_id)
        if local_usage:
            usage["backends"]["local"] = local_usage
            usage["total_size_mb"] += local_usage.get("total_size_mb", 0)
        
        log_function_exit(logger, "get_user_storage_usage", 
            success=True, 
            total_size_mb=usage["total_size_mb"]
        )
        return usage
    
    def _get_local_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """Get local storage usage for a user."""
        try:
            total_size = 0
            file_count = 0
            data_types = {}
            
            for data_type in ['routes', 'fitness', 'models', 'training_data']:
                user_dir = os.path.join(self.local_data_dir, data_type, user_id)
                if os.path.exists(user_dir):
                    for filename in os.listdir(user_dir):
                        filepath = os.path.join(user_dir, filename)
                        if os.path.isfile(filepath):
                            size = os.path.getsize(filepath)
                            total_size += size
                            file_count += 1
                            
                            if data_type not in data_types:
                                data_types[data_type] = {'count': 0, 'size_bytes': 0}
                            data_types[data_type]['count'] += 1
                            data_types[data_type]['size_bytes'] += size
            
            return {
                'user_id': user_id,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'data_types': data_types,
                'backend': 'local'
            }
            
        except Exception as e:
            logger.error(f"Failed to get local storage usage: {e}")
            return {}


# Global storage manager instance
_storage_manager = None


def get_storage_manager() -> StorageManager:
    """Get the global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager