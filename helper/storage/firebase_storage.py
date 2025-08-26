"""
Firebase Storage Backend for KOMpass.
Handles Google Firebase/Firestore operations with user data isolation and generous free tier.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
import tempfile

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

from ..config.logging_config import get_logger, log_function_entry, log_function_exit

logger = get_logger(__name__)


class FirebaseStorageBackend:
    """Firebase/Firestore storage backend with user data isolation."""
    
    def __init__(self, config):
        """
        Initialize Firebase storage backend.
        
        Args:
            config: FirebaseConfig instance with Firebase credentials and settings
        """
        self.config = config
        self.firebase_app = None
        self.db = None
        self.bucket = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase app with configured credentials."""
        try:
            if not FIREBASE_AVAILABLE:
                logger.error("Firebase SDK not available. Install with: pip install firebase-admin")
                return
                
            if not self.config.is_configured():
                logger.warning("Firebase not properly configured - missing credentials or project ID")
                return
            
            # Check if Firebase app already exists
            try:
                self.firebase_app = firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            except ValueError:
                # Initialize new Firebase app
                cred = self._get_credentials()
                if not cred:
                    return
                    
                self.firebase_app = firebase_admin.initialize_app(cred, {
                    'storageBucket': self.config.storage_bucket,
                    'projectId': self.config.project_id
                })
                logger.info(f"Firebase app initialized for project: {self.config.project_id}")
            
            # Initialize Firestore database
            self.db = firestore.client()
            
            # Initialize Cloud Storage bucket
            self.bucket = storage.bucket()
            
            # Test connection
            self._test_connection()
            logger.info("Firebase storage backend ready")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            self.firebase_app = None
            self.db = None
            self.bucket = None
    
    def _get_credentials(self):
        """Get Firebase credentials from configuration."""
        try:
            if self.config.service_account_key_path:
                # Load from file path
                return credentials.Certificate(self.config.service_account_key_path)
            elif self.config.service_account_key_json:
                # Load from JSON string
                if isinstance(self.config.service_account_key_json, str):
                    # Parse JSON string
                    cred_dict = json.loads(self.config.service_account_key_json)
                else:
                    # Already a dict
                    cred_dict = self.config.service_account_key_json
                return credentials.Certificate(cred_dict)
            else:
                logger.error("No Firebase service account key provided")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load Firebase credentials: {e}")
            return None
    
    def _test_connection(self):
        """Test Firebase connection."""
        try:
            # Test Firestore connection
            test_doc = self.db.collection('_test').document('connection')
            test_doc.set({'timestamp': firestore.SERVER_TIMESTAMP})
            test_doc.delete()
            
            # Test Storage connection
            self.bucket.blob('_test_connection').upload_from_string('test')
            self.bucket.blob('_test_connection').delete()
            
            logger.debug("Firebase connection test successful")
            
        except Exception as e:
            logger.warning(f"Firebase connection test failed: {e}")
    
    def is_available(self) -> bool:
        """Check if Firebase storage is available."""
        return (
            FIREBASE_AVAILABLE and 
            self.firebase_app is not None and 
            self.db is not None and 
            self.bucket is not None
        )
    
    def _get_storage_path(self, user_id: Optional[str], data_type: str, filename: str) -> str:
        """Build Firebase storage path with proper user data isolation."""
        if user_id:
            return f"users/{user_id}/{data_type}/{filename}"
        else:
            return f"{data_type}/{filename}"
    
    def _get_firestore_path(self, user_id: Optional[str], data_type: str) -> str:
        """Build Firestore collection path."""
        if user_id:
            return f"users/{user_id}/{data_type}"
        else:
            return data_type
    
    def save_file(self, data: Any, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Save data to Firebase Storage and metadata to Firestore.
        
        Args:
            data: Data to save (dict, string, or bytes)
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "save_file", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename
        )
        
        if not self.is_available():
            logger.error("Firebase storage not available")
            return False
        
        try:
            # Check file size limits
            data_size = self._get_data_size(data)
            if data_size > self.config.max_file_size_mb * 1024 * 1024:
                logger.error(f"File too large: {data_size / (1024*1024):.2f}MB > {self.config.max_file_size_mb}MB")
                return False
            
            # Check user storage quota
            if user_id and not self._check_user_quota(user_id, data_size):
                logger.error(f"User storage quota exceeded for user {user_id}")
                return False
            
            # Prepare data for upload
            upload_data = self._prepare_upload_data(data)
            
            # Upload to Firebase Storage
            storage_path = self._get_storage_path(user_id, data_type, filename)
            blob = self.bucket.blob(storage_path)
            
            if isinstance(upload_data, bytes):
                blob.upload_from_string(upload_data)
            else:
                blob.upload_from_string(upload_data, content_type='application/json')
            
            # Save metadata to Firestore
            metadata = {
                'filename': filename,
                'data_type': data_type,
                'user_id': user_id,
                'size_bytes': data_size,
                'size_mb': round(data_size / (1024 * 1024), 2),
                'content_type': 'application/json' if not isinstance(data, bytes) else 'application/octet-stream',
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'storage_path': storage_path
            }
            
            # Save to Firestore collection
            collection_path = self._get_firestore_path(user_id, data_type)
            doc_id = filename.replace('.', '_')  # Firestore doesn't allow dots in doc IDs
            self.db.collection(collection_path).document(doc_id).set(metadata)
            
            logger.info(f"File saved to Firebase: {storage_path}")
            log_function_exit(logger, "save_file", "success=True")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save to Firebase: {e}")
            log_function_exit(logger, "save_file", "success=False")
            return False
    
    def load_file(self, user_id: Optional[str], data_type: str, filename: str) -> Optional[Any]:
        """
        Load data from Firebase Storage.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Loaded data or None if not found
        """
        log_function_entry(logger, "load_file", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename
        )
        
        if not self.is_available():
            logger.error("Firebase storage not available")
            return None
        
        try:
            storage_path = self._get_storage_path(user_id, data_type, filename)
            blob = self.bucket.blob(storage_path)
            
            if not blob.exists():
                logger.debug(f"File not found in Firebase: {storage_path}")
                return None
            
            # Download data
            content = blob.download_as_bytes()
            
            # Try to parse as JSON first
            try:
                return json.loads(content.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Return as bytes if not JSON
                return content
            
        except Exception as e:
            logger.error(f"Failed to load from Firebase: {e}")
            log_function_exit(logger, "load_file", "success=False")
            return None
    
    def list_files(self, user_id: Optional[str], data_type: str) -> List[Dict[str, Any]]:
        """
        List files for a user and data type from Firestore metadata.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            
        Returns:
            List of file information
        """
        log_function_entry(logger, "list_files", user_id=user_id, data_type=data_type)
        
        if not self.is_available():
            logger.error("Firebase storage not available")
            return []
        
        try:
            collection_path = self._get_firestore_path(user_id, data_type)
            docs = self.db.collection(collection_path).stream()
            
            files = []
            for doc in docs:
                doc_data = doc.to_dict()
                if doc_data:
                    # Convert Firestore timestamps to ISO strings
                    if 'created_at' in doc_data and doc_data['created_at']:
                        doc_data['created_at'] = doc_data['created_at'].isoformat()
                    if 'updated_at' in doc_data and doc_data['updated_at']:
                        doc_data['updated_at'] = doc_data['updated_at'].isoformat()
                    
                    doc_data['backend'] = 'firebase'
                    files.append(doc_data)
            
            # Sort by created_at descending
            files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            log_function_exit(logger, "list_files", f"success=True, count={len(files)}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list Firebase files: {e}")
            log_function_exit(logger, "list_files", "success=False")
            return []
    
    def delete_file(self, user_id: Optional[str], data_type: str, filename: str) -> bool:
        """
        Delete data from Firebase Storage and Firestore.
        
        Args:
            user_id: User ID (None for global data)
            data_type: Type of data (routes, fitness, models, training_data)
            filename: File name
            
        Returns:
            Success status
        """
        log_function_entry(logger, "delete_file", 
            user_id=user_id, 
            data_type=data_type, 
            filename=filename
        )
        
        if not self.is_available():
            logger.error("Firebase storage not available")
            return False
        
        try:
            # Delete from Firebase Storage
            storage_path = self._get_storage_path(user_id, data_type, filename)
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
                logger.debug(f"Deleted from Firebase Storage: {storage_path}")
            
            # Delete metadata from Firestore
            collection_path = self._get_firestore_path(user_id, data_type)
            doc_id = filename.replace('.', '_')
            self.db.collection(collection_path).document(doc_id).delete()
            logger.debug(f"Deleted from Firestore: {collection_path}/{doc_id}")
            
            log_function_exit(logger, "delete_file", "success=True")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete from Firebase: {e}")
            log_function_exit(logger, "delete_file", "success=False")
            return False
    
    def get_user_storage_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get storage usage for a user from Firestore metadata.
        
        Args:
            user_id: User ID
            
        Returns:
            Storage usage information
        """
        log_function_entry(logger, "get_user_storage_usage", user_id=user_id)
        
        if not self.is_available():
            return {}
        
        try:
            total_size = 0
            file_count = 0
            data_types = {}
            
            # Query all data types for this user
            for data_type in ['routes', 'fitness', 'models', 'training_data']:
                collection_path = f"users/{user_id}/{data_type}"
                docs = self.db.collection(collection_path).stream()
                
                type_size = 0
                type_count = 0
                
                for doc in docs:
                    doc_data = doc.to_dict()
                    if doc_data and 'size_bytes' in doc_data:
                        size = doc_data['size_bytes']
                        total_size += size
                        type_size += size
                        file_count += 1
                        type_count += 1
                
                if type_count > 0:
                    data_types[data_type] = {
                        'count': type_count,
                        'size_bytes': type_size,
                        'size_mb': round(type_size / (1024 * 1024), 2)
                    }
            
            usage = {
                'user_id': user_id,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'file_count': file_count,
                'data_types': data_types,
                'backend': 'firebase'
            }
            
            log_function_exit(logger, "get_user_storage_usage", 
                success=True, 
                total_size_mb=usage['total_size_mb']
            )
            return usage
            
        except Exception as e:
            logger.error(f"Failed to get Firebase storage usage: {e}")
            return {}
    
    def _get_data_size(self, data: Any) -> int:
        """Get size of data in bytes."""
        if isinstance(data, bytes):
            return len(data)
        elif isinstance(data, str):
            return len(data.encode('utf-8'))
        else:
            # Assume it's JSON-serializable
            return len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def _prepare_upload_data(self, data: Any) -> Union[str, bytes]:
        """Prepare data for upload to Firebase Storage."""
        if isinstance(data, bytes):
            return data
        elif isinstance(data, str):
            return data
        else:
            # Convert to JSON
            return json.dumps(data, ensure_ascii=False, indent=2)
    
    def _check_user_quota(self, user_id: str, additional_size: int) -> bool:
        """Check if user storage quota allows additional data."""
        try:
            usage = self.get_user_storage_usage(user_id)
            current_size_mb = usage.get('total_size_mb', 0)
            additional_size_mb = additional_size / (1024 * 1024)
            
            return (current_size_mb + additional_size_mb) <= self.config.max_user_storage_mb
            
        except Exception as e:
            logger.error(f"Failed to check user quota: {e}")
            # Allow upload if quota check fails
            return True