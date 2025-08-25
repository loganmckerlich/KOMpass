"""
Centralized logging configuration for KOMpass application.
Provides structured logging with appropriate levels and formatting.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Setup centralized logging configuration for the KOMpass application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to also log to a file
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"kompass_{timestamp}.log"
    
    # Configure root logger
    logger = logging.getLogger("kompass")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if enabled)
    if log_to_file:
        try:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")
    
    # Log startup message
    logger.info("KOMpass logging system initialized")
    logger.debug(f"Log level set to: {log_level}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__ from calling module)
        
    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("kompass")
    
    # Create child logger
    return logging.getLogger(f"kompass.{name}")


def log_function_entry(logger: logging.Logger, func_name: str, **kwargs):
    """
    Log function entry with parameters.
    
    Args:
        logger: Logger instance
        func_name: Name of the function being entered
        **kwargs: Function parameters to log
    """
    if kwargs:
        params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.debug(f"Entering {func_name}({params})")
    else:
        logger.debug(f"Entering {func_name}()")


def log_function_exit(logger: logging.Logger, func_name: str, result=None):
    """
    Log function exit with optional return value.
    
    Args:
        logger: Logger instance
        func_name: Name of the function being exited
        result: Function return value (optional)
    """
    if result is not None:
        logger.debug(f"Exiting {func_name}() -> {type(result).__name__}")
    else:
        logger.debug(f"Exiting {func_name}()")


def log_error(logger: logging.Logger, error: Exception, context: str = None):
    """
    Log an error with context information.
    
    Args:
        logger: Logger instance
        error: Exception instance
        context: Additional context about where the error occurred
    """
    error_msg = f"{type(error).__name__}: {str(error)}"
    if context:
        error_msg = f"{context} - {error_msg}"
    
    logger.error(error_msg, exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float, details: str = None):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        operation: Description of the operation
        duration: Time taken in seconds
        details: Additional details about the operation
    """
    perf_msg = f"Performance: {operation} took {duration:.3f}s"
    if details:
        perf_msg += f" ({details})"
    
    logger.info(perf_msg)


# Performance logging decorator
def log_execution_time(logger: logging.Logger = None):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance (will create one if not provided)
    """
    import functools
    import time
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(logger, func.__name__, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_performance(logger, f"{func.__name__} (failed)", duration)
                log_error(logger, e, f"Error in {func.__name__}")
                raise
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test the logging configuration
    logger = setup_logging("DEBUG")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test child logger
    child_logger = get_logger("test_module")
    child_logger.info("Message from child logger")
    
    # Test error logging
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error(logger, e, "Testing error logging")
    
    print("✅ Logging configuration test completed")