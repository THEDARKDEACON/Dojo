"""
Configuration management utilities for the robot_perception package.
"""
import os
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path

class ConfigManager:
    """Manages configuration loading and access for the perception system."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file. If None, loads default config.
        """
        self._config = {}
        self._config_path = config_path
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file or use defaults."""
        if self._config_path and os.path.isfile(self._config_path):
            with open(self._config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            # Use default configuration
            self._config = {
                'camera': {
                    'image_topic': "/camera/color/image_raw",
                    'info_topic': "/camera/color/camera_info",
                    'compressed': False,
                    'queue_size': 10,
                },
                'debug': {
                    'enable': True,
                    'log_level': 'info'
                }
            }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.
        
        Args:
            key: Dot-separated key path (e.g., 'camera.image_topic')
            default: Default value if key not found
            
        Returns:
            The configuration value or default if not found
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation.
        
        Args:
            key: Dot-separated key path (e.g., 'camera.image_topic')
            value: Value to set
        """
        keys = key.split('.')
        current = self._config
        
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration with values from a dictionary.
        
        Args:
            config_dict: Dictionary of configuration values to update
        """
        def _update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = _update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d
        
        self._config = _update(self._config, config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return the configuration as a dictionary."""
        return self._config.copy()
    
    def save(self, file_path: Optional[str] = None) -> None:
        """Save the current configuration to a YAML file.
        
        Args:
            file_path: Path to save the configuration. Uses the loaded path if None.
        """
        path = file_path or self._config_path
        if not path:
            raise ValueError("No file path provided for saving configuration")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        with open(path, 'w') as f:
            yaml.safe_dump(self._config, f, default_flow_style=False)


def load_config(config_path: Optional[str] = None) -> ConfigManager:
    """Load configuration from a YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
                     If None, looks for 'perception_params.yaml' in the package config directory.
    
    Returns:
        ConfigManager instance with the loaded configuration
    """
    if config_path is None:
        # Try to find the default config file
        try:
            from ament_index_python.packages import get_package_share_directory
            pkg_share = get_package_share_directory('robot_perception')
            config_path = os.path.join(pkg_share, 'config', 'perception_params.yaml')
        except Exception as e:
            import warnings
            warnings.warn(f"Could not find default config file: {e}")
    
    return ConfigManager(config_path)
