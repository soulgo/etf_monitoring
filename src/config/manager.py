"""
Configuration manager with loading, validation, and atomic saving.

Implements singleton pattern for global configuration access with thread-safe operations.
"""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from threading import Lock

from .validator import ConfigValidator
from ..utils.logger import get_logger


class ConfigManager:
    """
    Singleton configuration manager.
    
    Provides centralized configuration management with:
    - Automatic loading from config.json
    - Validation with default value fallback
    - Atomic saving with temporary file + rename
    - Thread-safe operations
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = Lock()
    
    # Default configuration file paths
    DEFAULT_CONFIG_FILE = "config.json"
    DEFAULT_CONFIG_TEMPLATE = "config.default.json"
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "config_version": "1.0",
        "etf_list": [],
        "refresh_interval": 5,
        "rotation_interval": 3,
        "rotation_mode": "both",
        "api_config": {
            "primary": {
                "name": "eastmoney",
                "base_url": "http://push2.eastmoney.com/api/qt/stock/get",
                "timeout": 5,
                "enabled": True
            },
            "backup": [
                {
                    "name": "tencent",
                    "base_url": "http://qt.gtimg.cn/q=",
                    "timeout": 5,
                    "enabled": True
                }
            ],
            "retry_count": 3,
            "retry_interval": 1,
            "failover_threshold": 3
        },
        "display_config": {
            "tooltip_format": "{name} ({code})\n最新价: {price} ({change_percent})\n更新: {time}",
            "show_update_time": True,
            "color_up": "green",
            "color_down": "red",
            "color_neutral": "gray"
        },
        "alert_threshold": {
            "enabled": False,
            "up_threshold": 3.0,
            "down_threshold": -3.0,
            "notification_type": "toast",
            "sound_enabled": False
        },
        "auto_start": False,
        "log_level": "INFO",
        "floating_window": {
            "enabled": True,
            "position": [100, 100],
            "size": [350, 60],
            "font_size": 18,
            "transparency": 200,
            "always_on_top": True
        },
        "advanced": {
            "single_instance": True,
            "minimize_to_tray": True,
            "check_update": False,
            "data_cache_expire": 300
        }
    }
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager."""
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._config_file = self.DEFAULT_CONFIG_FILE
        self._logger = get_logger(__name__)
        self._operation_lock = Lock()
        
    def load(self, config_file: Optional[str] = None) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_file: Path to configuration file (uses default if None)
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if config_file:
            self._config_file = config_file
        
        config_path = Path(self._config_file)
        
        # If config doesn't exist, create from template or defaults
        if not config_path.exists():
            self._logger.info(f"Config file not found: {config_path}")
            return self._create_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
            
            # Validate configuration
            is_valid, errors = ConfigValidator.validate_config(loaded_config)
            if not is_valid:
                self._logger.warning(f"Configuration validation errors: {errors}")
                # Still use the config but fill missing fields with defaults
            
            # Merge with defaults to ensure all fields exist
            self._config = self._merge_with_defaults(loaded_config)
            
            self._logger.info(f"Configuration loaded from {config_path}")
            return True
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Failed to parse config file: {e}")
            self._logger.warning("Using default configuration")
            self._config = self.DEFAULT_CONFIG.copy()
            return False
            
        except Exception as e:
            self._logger.error(f"Failed to load config: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            return False
    
    def save(self) -> bool:
        """
        Save configuration to file atomically.
        
        Uses temporary file + rename for atomic operation to prevent data loss.
        
        Returns:
            True if saved successfully, False otherwise
        """
        with self._operation_lock:
            try:
                config_path = Path(self._config_file)
                temp_path = config_path.with_suffix('.tmp')
                
                # Write to temporary file
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                
                # Atomic rename (overwrites existing file)
                shutil.move(str(temp_path), str(config_path))
                
                self._logger.info(f"Configuration saved to {config_path}")
                return True
                
            except Exception as e:
                self._logger.error(f"Failed to save config: {e}")
                return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation, e.g., "api_config.primary.timeout")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        with self._operation_lock:
            keys = key.split('.')
            config = self._config
            
            # Navigate to parent
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            # Set value
            config[keys[-1]] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get entire configuration dictionary.
        
        Returns:
            Copy of configuration dictionary
        """
        return self._config.copy()
    
    def reload(self) -> bool:
        """
        Reload configuration from file.
        
        Returns:
            True if reloaded successfully
        """
        return self.load()
    
    def _create_default_config(self) -> bool:
        """
        Create default configuration file.
        
        Returns:
            True if created successfully
        """
        try:
            # First try to copy from template
            template_path = Path(self.DEFAULT_CONFIG_TEMPLATE)
            if template_path.exists():
                self._logger.info(f"Creating config from template: {template_path}")
                with open(template_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                self._logger.info("Creating config from hardcoded defaults")
                self._config = self.DEFAULT_CONFIG.copy()
            
            # Save to config file
            self.save()
            self._logger.info(f"Default configuration created: {self._config_file}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to create default config: {e}")
            self._config = self.DEFAULT_CONFIG.copy()
            return False
    
    def _merge_with_defaults(self, loaded_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge loaded configuration with defaults to ensure all fields exist.
        
        Args:
            loaded_config: Configuration loaded from file
            
        Returns:
            Merged configuration
        """
        def merge_dicts(default: dict, loaded: dict) -> dict:
            """Recursively merge dictionaries."""
            result = default.copy()
            for key, value in loaded.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dicts(result[key], value)
                else:
                    result[key] = value
            return result
        
        return merge_dicts(self.DEFAULT_CONFIG, loaded_config)


# Global configuration instance
def get_config() -> ConfigManager:
    """
    Get global configuration manager instance.
    
    Returns:
        ConfigManager singleton instance
    """
    return ConfigManager()

