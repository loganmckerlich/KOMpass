"""
UI Components for KOMpass application.

This module coordinates all UI operations using specialized components:
- Header and layout management
- Home page rendering
- Route upload handling
- Route analysis display

Note: This module has been refactored into smaller, focused components in the components/ subdirectory.
"""

from .components import UIComponents as NewUIComponents
from helper.config.logging_config import get_logger

logger = get_logger(__name__)


class UIComponents:
    """Legacy wrapper for the refactored UI components."""
    
    def __init__(self):
        """Initialize UI components."""
        logger.info("Initializing refactored UIComponents")
        self._components = NewUIComponents()
    
    def __getattr__(self, name):
        """Delegate all method calls to the new components for backwards compatibility."""
        return getattr(self._components, name)


def get_ui_components():
    """Factory function to get UI components instance."""
    return UIComponents()