# KOMpass Code Organization & Logging

This document describes the refactored architecture of the KOMpass application, focusing on improved code organization, comprehensive logging, and better maintainability.

## Architecture Overview

The application has been refactored from a monolithic `main.py` (600+ lines) into a modular architecture with clear separation of concerns:

```
KOMpass/
├── main.py                 # Main application entry point (~70 lines)
├── logging_config.py       # Centralized logging configuration
├── config.py              # Configuration management
├── auth_manager.py         # Strava OAuth authentication
├── ui_components.py        # UI rendering and user interactions
├── route_processor.py      # Route analysis and processing (existing)
├── weather_analyzer.py     # Weather analysis (existing)
├── strava_connect.py       # Strava API integration (enhanced)
├── strava_oauth.py         # OAuth client (existing)
└── logs/                   # Application logs directory
```

## Key Improvements

### 1. Comprehensive Logging System (`logging_config.py`)

- **Centralized Configuration**: Single place to configure logging for entire application
- **File + Console Output**: Logs to both console (INFO+) and files (DEBUG+)
- **Performance Tracking**: Decorator for timing function execution
- **Structured Error Logging**: Consistent error reporting with context
- **Daily Log Rotation**: Separate log files per day

```python
# Example usage
from logging_config import get_logger, log_execution_time

logger = get_logger(__name__)

@log_execution_time()
def process_route():
    logger.info("Processing route...")
```

### 2. Configuration Management (`config.py`)

- **Environment Variable Support**: Centralized env var handling
- **Configuration Validation**: Automatic validation of all settings
- **Type Safety**: Dataclass-based configuration with type hints
- **Environment Detection**: Automatic dev/prod environment detection

```python
# Example usage
from config import get_config

config = get_config()
redirect_uri = config.strava.get_redirect_uri()
max_file_size = config.app.max_file_size_mb
```

### 3. Authentication Management (`auth_manager.py`)

- **Session State Management**: Proper handling of Streamlit session state
- **OAuth Flow Handling**: Complete OAuth flow with error handling
- **Token Management**: Access token refresh and validation
- **UI Components**: Reusable authentication UI components

### 4. UI Components (`ui_components.py`)

- **Modular UI**: Reusable UI components and page renderers
- **Error Handling**: Consistent error handling across all UI elements
- **Performance Logging**: Automatic timing of expensive operations
- **Clean Separation**: UI logic separated from business logic

### 5. Enhanced Main Application (`main.py`)

- **Minimal and Clean**: Reduced from 600+ lines to ~70 lines
- **Clear Flow**: Simple, readable application flow
- **Error Handling**: Top-level error handling with logging
- **Configuration-Driven**: Uses configuration system for all settings

## Logging Features

### Log Levels
- **DEBUG**: Detailed debugging information, function entry/exit
- **INFO**: General application flow, successful operations
- **WARNING**: Warning conditions that don't halt execution
- **ERROR**: Error conditions with full stack traces

### Log Format
```
2025-08-25 23:22:48 - kompass.module - LEVEL - function:line - Message
```

### Performance Logging
```python
@log_execution_time()
def expensive_operation():
    # Function execution time automatically logged
    pass
```

### Error Logging
```python
try:
    risky_operation()
except Exception as e:
    log_error(logger, e, "Context about what failed")
    raise
```

## Configuration Options

### Environment Variables

**Strava Configuration:**
- `STRAVA_CLIENT_ID`: Strava application client ID
- `STRAVA_CLIENT_SECRET`: Strava application client secret
- `STRAVA_REDIRECT_URI_DEV`: Development redirect URI (default: http://localhost:8501)
- `STRAVA_REDIRECT_URI_PROD`: Production redirect URI (default: https://kompass-dev.streamlit.app)

**Application Configuration:**
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_TO_FILE`: Enable file logging (true/false)
- `DATA_DIRECTORY`: Directory for saved routes (default: saved_routes)
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 10)

**Weather Configuration:**
- `WEATHER_API_URL`: Weather service URL (default: Open-Meteo)
- `WEATHER_TIMEOUT`: API timeout in seconds (default: 10)
- `MAX_FORECAST_DAYS`: Maximum forecast days (default: 7)

## Testing

### Integration Test
Run the integration test to verify all modules work together:

```bash
python test_integration.py
```

### Module Tests
Test individual modules:

```bash
python logging_config.py    # Test logging system
python config.py           # Test configuration
python auth_manager.py     # Test authentication (outside Streamlit)
```

## Benefits of Refactoring

1. **Maintainability**: Clear separation of concerns makes code easier to maintain
2. **Debugging**: Comprehensive logging makes issues easier to track and resolve
3. **Testing**: Modular design allows for better unit and integration testing
4. **Configuration**: Centralized configuration management
5. **Error Handling**: Consistent error handling and logging throughout
6. **Performance**: Performance monitoring and optimization capabilities
7. **Scalability**: Modular architecture supports future enhancements

## Usage

The refactored application maintains the same user interface and functionality while providing:

- Better error messages and debugging information
- Performance insights through logging
- More robust configuration management
- Improved error recovery
- Better development experience

All existing functionality remains intact while providing a much more maintainable and debuggable codebase.