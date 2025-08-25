"""
Configuration management for KOMpass application.
Centralizes environment variables and application settings.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StravaConfig:
    """Strava API configuration."""
    client_id: str
    client_secret: str
    redirect_uri_local: str = "http://localhost:8501"
    redirect_uri_prod: str = "https://kompass-dev.streamlit.app/"
    
    def get_redirect_uri(self) -> str:
        """Get appropriate redirect URI based on environment."""
        if os.environ.get("STREAMLIT_ENV") == "development":
            return self.redirect_uri_local
        return self.redirect_uri_prod


@dataclass
class AppConfig:
    """General application configuration."""
    log_level: str = "INFO"
    log_to_file: bool = True
    data_directory: str = "saved_routes"
    max_file_size_mb: int = 10
    supported_file_types: list = None
    
    def __post_init__(self):
        if self.supported_file_types is None:
            self.supported_file_types = ['gpx']


@dataclass
class WeatherConfig:
    """Weather service configuration."""
    base_url: str = "https://api.open-meteo.com/v1/forecast"
    timeout_seconds: int = 10
    request_delay_seconds: float = 1.0
    max_forecast_days: int = 7


@dataclass
class PerformanceConfig:
    """Performance and ML configuration."""
    default_rider_weight_kg: int = 70
    default_bike_weight_kg: int = 10
    default_cda: float = 0.32
    default_crr: float = 0.005
    default_efficiency: float = 0.95


class ConfigManager:
    """Centralized configuration manager for the KOMpass application."""
    
    def __init__(self):
        """Initialize configuration manager."""
        logger.info("Initializing configuration manager")
        self._strava_config = None
        self._app_config = None
        self._weather_config = None
        self._performance_config = None
        
        self._load_configurations()
    
    def _load_configurations(self):
        """Load all configuration sections."""
        try:
            self._app_config = self._load_app_config()
            self._strava_config = self._load_strava_config()
            self._weather_config = self._load_weather_config()
            self._performance_config = self._load_performance_config()
            
            logger.info("All configurations loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading configurations: {e}")
            raise
    
    def _load_strava_config(self) -> StravaConfig:
        """Load Strava API configuration from environment variables."""
        client_id = os.environ.get("STRAVA_CLIENT_ID")
        client_secret = os.environ.get("STRAVA_CLIENT_SECRET")
        
        if not client_id:
            logger.warning("STRAVA_CLIENT_ID not found in environment variables")
            client_id = "your_client_id_here"
        
        if not client_secret:
            logger.warning("STRAVA_CLIENT_SECRET not found in environment variables")
            client_secret = "your_client_secret_here"
        
        config = StravaConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri_local=os.environ.get("STRAVA_REDIRECT_URI_LOCAL", "http://localhost:8501"),
            redirect_uri_prod=os.environ.get("STRAVA_REDIRECT_URI_PROD", "https://kompass-dev.streamlit.app/")
        )
        
        logger.debug(f"Strava config loaded - Client ID: {client_id[:8]}...")
        return config
    
    def _load_app_config(self) -> AppConfig:
        """Load general application configuration."""
        config = AppConfig(
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_to_file=os.environ.get("LOG_TO_FILE", "true").lower() == "true",
            data_directory=os.environ.get("DATA_DIRECTORY", "saved_routes"),
            max_file_size_mb=int(os.environ.get("MAX_FILE_SIZE_MB", "10")),
        )
        
        logger.debug(f"App config loaded - Log level: {config.log_level}")
        return config
    
    def _load_weather_config(self) -> WeatherConfig:
        """Load weather service configuration."""
        config = WeatherConfig(
            base_url=os.environ.get("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast"),
            timeout_seconds=int(os.environ.get("WEATHER_TIMEOUT", "10")),
            request_delay_seconds=float(os.environ.get("WEATHER_DELAY", "1.0")),
            max_forecast_days=int(os.environ.get("MAX_FORECAST_DAYS", "7"))
        )
        
        logger.debug(f"Weather config loaded - URL: {config.base_url}")
        return config
    
    def _load_performance_config(self) -> PerformanceConfig:
        """Load performance calculation configuration."""
        config = PerformanceConfig(
            default_rider_weight_kg=int(os.environ.get("DEFAULT_RIDER_WEIGHT", "70")),
            default_bike_weight_kg=int(os.environ.get("DEFAULT_BIKE_WEIGHT", "10")),
            default_cda=float(os.environ.get("DEFAULT_CDA", "0.32")),
            default_crr=float(os.environ.get("DEFAULT_CRR", "0.005")),
            default_efficiency=float(os.environ.get("DEFAULT_EFFICIENCY", "0.95"))
        )
        
        logger.debug(f"Performance config loaded - Rider weight: {config.default_rider_weight_kg}kg")
        return config
    
    @property
    def strava(self) -> StravaConfig:
        """Get Strava configuration."""
        return self._strava_config
    
    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        return self._app_config
    
    @property
    def weather(self) -> WeatherConfig:
        """Get weather configuration."""
        return self._weather_config
    
    @property
    def performance(self) -> PerformanceConfig:
        """Get performance configuration."""
        return self._performance_config
    
    def is_strava_configured(self) -> bool:
        """Check if Strava API is properly configured."""
        return (
            self._strava_config.client_id != "your_client_id_here" and
            self._strava_config.client_secret != "your_client_secret_here" and
            self._strava_config.client_id and
            self._strava_config.client_secret
        )
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information for debugging."""
        return {
            "environment": os.environ.get("STREAMLIT_ENV", "production"),
            "python_version": os.environ.get("PYTHON_VERSION", "unknown"),
            "strava_configured": self.is_strava_configured(),
            "data_directory": self._app_config.data_directory,
            "log_level": self._app_config.log_level,
            "weather_service": self._weather_config.base_url,
        }
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate all configuration sections."""
        validation_results = {}
        
        # Validate Strava config
        validation_results["strava_client_id"] = bool(self._strava_config.client_id)
        validation_results["strava_client_secret"] = bool(self._strava_config.client_secret)
        validation_results["strava_configured"] = self.is_strava_configured()
        
        # Validate app config
        validation_results["valid_log_level"] = self._app_config.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        validation_results["data_directory_exists"] = os.path.exists(self._app_config.data_directory) or self._create_data_directory()
        
        # Validate weather config
        validation_results["weather_url_valid"] = self._weather_config.base_url.startswith("http")
        validation_results["weather_timeout_valid"] = self._weather_config.timeout_seconds > 0
        
        logger.info(f"Configuration validation completed: {sum(validation_results.values())}/{len(validation_results)} checks passed")
        
        return validation_results
    
    def _create_data_directory(self) -> bool:
        """Create data directory if it doesn't exist."""
        try:
            os.makedirs(self._app_config.data_directory, exist_ok=True)
            logger.info(f"Created data directory: {self._app_config.data_directory}")
            return True
        except Exception as e:
            logger.error(f"Failed to create data directory: {e}")
            return False


# Global configuration instance
config_manager = ConfigManager()


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager


if __name__ == "__main__":
    # Test configuration loading
    from logging_config import setup_logging
    
    setup_logging("DEBUG")
    
    config = get_config()
    
    print("=== Configuration Test ===")
    print(f"Strava configured: {config.is_strava_configured()}")
    print(f"Environment info: {config.get_environment_info()}")
    print(f"Validation results: {config.validate_configuration()}")
    
    print("\n=== Strava Config ===")
    print(f"Redirect URI: {config.strava.get_redirect_uri()}")
    
    print("\n=== App Config ===")
    print(f"Log level: {config.app.log_level}")
    print(f"Data directory: {config.app.data_directory}")
    
    print("\n✅ Configuration test completed")
