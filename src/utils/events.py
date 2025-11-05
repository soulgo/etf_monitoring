"""
Custom wxPython events for inter-thread communication.

Events are used to notify the UI thread of data changes and configuration updates
from background threads in a thread-safe manner.
"""

import wx
import wx.lib.newevent


# Custom event for data changes (ETF quotes updated)
DataChangedEvent, EVT_DATA_CHANGED = wx.lib.newevent.NewEvent()

# Custom event for configuration changes (config.json modified)
ConfigChangedEvent, EVT_CONFIG_CHANGED = wx.lib.newevent.NewEvent()

# Custom event for refresh requests (manual refresh triggered)
RefreshEvent, EVT_REFRESH = wx.lib.newevent.NewEvent()

# Custom event for errors (network failures, data errors)
ErrorEvent, EVT_ERROR = wx.lib.newevent.NewEvent()


class EventData:
    """
    Base class for event data payloads.
    """
    pass


class DataChangedEventData(EventData):
    """
    Data payload for DataChangedEvent.
    
    Attributes:
        changed_codes: List of ETF codes that have changed
        all_data: Dictionary of all current ETF data
        timestamp: Event timestamp
    """
    
    def __init__(self, changed_codes: list, all_data: dict, timestamp: float):
        self.changed_codes = changed_codes
        self.all_data = all_data
        self.timestamp = timestamp


class ConfigChangedEventData(EventData):
    """
    Data payload for ConfigChangedEvent.
    
    Attributes:
        config: Updated configuration dictionary
        changed_keys: List of configuration keys that changed
    """
    
    def __init__(self, config: dict, changed_keys: list):
        self.config = config
        self.changed_keys = changed_keys


class ErrorEventData(EventData):
    """
    Data payload for ErrorEvent.
    
    Attributes:
        error_type: Type of error (network, data, config, etc.)
        message: Error message
        exception: Optional exception object
    """
    
    def __init__(self, error_type: str, message: str, exception: Exception = None):
        self.error_type = error_type
        self.message = message
        self.exception = exception

