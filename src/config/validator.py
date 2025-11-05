"""
Configuration validation with type checking and range validation.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class ConfigValidator:
    """
    Validates configuration data against expected schema.
    
    Provides methods to validate individual fields and entire configuration objects,
    ensuring type safety and value constraints.
    """
    
    # Valid rotation modes
    VALID_ROTATION_MODES = ['timer', 'change', 'both']
    
    # Valid log levels
    VALID_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    # Valid notification types
    VALID_NOTIFICATION_TYPES = ['toast', 'popup', 'both']
    
    @staticmethod
    def validate_etf_code(code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate ETF code format.
        
        Args:
            code: ETF code string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(code, str):
            return False, "ETF code must be a string"
        
        if not re.match(r'^\d{6}$', code):
            return False, f"ETF code must be 6 digits, got: {code}"
        
        return True, None
    
    @staticmethod
    def validate_etf_list(etf_list: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate ETF list.
        
        Args:
            etf_list: ETF list to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(etf_list, list):
            return False, "etf_list must be a list"
        
        if len(etf_list) > 100:
            return False, f"Too many ETFs (max 100), got {len(etf_list)}"
        
        for code in etf_list:
            is_valid, error = ConfigValidator.validate_etf_code(code)
            if not is_valid:
                return False, f"Invalid ETF code in list: {error}"
        
        return True, None
    
    @staticmethod
    def validate_interval(value: Any, min_val: int, max_val: int, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate interval value within range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Field name for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(value, int):
            return False, f"{name} must be an integer, got {type(value).__name__}"
        
        if value < min_val or value > max_val:
            return False, f"{name} must be between {min_val} and {max_val}, got {value}"
        
        return True, None
    
    @staticmethod
    def validate_rotation_mode(mode: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate rotation mode.
        
        Args:
            mode: Rotation mode string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(mode, str):
            return False, "rotation_mode must be a string"
        
        if mode not in ConfigValidator.VALID_ROTATION_MODES:
            return False, f"Invalid rotation_mode: {mode}. Must be one of {ConfigValidator.VALID_ROTATION_MODES}"
        
        return True, None
    
    @staticmethod
    def validate_log_level(level: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate log level.
        
        Args:
            level: Log level string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(level, str):
            return False, "log_level must be a string"
        
        if level.upper() not in ConfigValidator.VALID_LOG_LEVELS:
            return False, f"Invalid log_level: {level}. Must be one of {ConfigValidator.VALID_LOG_LEVELS}"
        
        return True, None
    
    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate entire configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate config_version
        if 'config_version' not in config:
            errors.append("Missing required field: config_version")
        elif not isinstance(config['config_version'], str):
            errors.append("config_version must be a string")
        
        # Validate etf_list
        if 'etf_list' in config:
            is_valid, error = cls.validate_etf_list(config['etf_list'])
            if not is_valid:
                errors.append(error)
        
        # Validate refresh_interval
        if 'refresh_interval' in config:
            is_valid, error = cls.validate_interval(
                config['refresh_interval'], 3, 30, 'refresh_interval'
            )
            if not is_valid:
                errors.append(error)
        
        # Validate rotation_interval
        if 'rotation_interval' in config:
            is_valid, error = cls.validate_interval(
                config['rotation_interval'], 1, 60, 'rotation_interval'
            )
            if not is_valid:
                errors.append(error)
        
        # Validate rotation_mode
        if 'rotation_mode' in config:
            is_valid, error = cls.validate_rotation_mode(config['rotation_mode'])
            if not is_valid:
                errors.append(error)
        
        # Validate log_level
        if 'log_level' in config:
            is_valid, error = cls.validate_log_level(config['log_level'])
            if not is_valid:
                errors.append(error)

        # Validate floating window config
        if 'floating_window' in config:
            floating_window = config['floating_window']
            if not isinstance(floating_window, dict):
                errors.append("floating_window must be a dictionary")
            else:
                size = floating_window.get('size')
                if size is not None:
                    if (not isinstance(size, (list, tuple)) or len(size) != 2):
                        errors.append("floating_window.size must be a list of [width, height]")
                    else:
                        width, height = size
                        if not isinstance(width, int) or not isinstance(height, int):
                            errors.append("floating_window.size values must be integers")
                        else:
                            if width < 200 or width > 800:
                                errors.append("floating_window.size width must be between 200 and 800")
                            if height < 40 or height > 200:
                                errors.append("floating_window.size height must be between 40 and 200")
        
        # Validate api_config structure
        if 'api_config' in config:
            api_config = config['api_config']
            if not isinstance(api_config, dict):
                errors.append("api_config must be a dictionary")
            else:
                # Validate primary API
                if 'primary' not in api_config:
                    errors.append("api_config.primary is required")
                elif not isinstance(api_config['primary'], dict):
                    errors.append("api_config.primary must be a dictionary")
                
                # Validate retry_count
                if 'retry_count' in api_config:
                    is_valid, error = cls.validate_interval(
                        api_config['retry_count'], 0, 5, 'api_config.retry_count'
                    )
                    if not is_valid:
                        errors.append(error)
                
                # Validate failover_threshold
                if 'failover_threshold' in api_config:
                    is_valid, error = cls.validate_interval(
                        api_config['failover_threshold'], 1, 10, 'api_config.failover_threshold'
                    )
                    if not is_valid:
                        errors.append(error)
        
        return len(errors) == 0, errors

