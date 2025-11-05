"""
Logging configuration with rotating file handler and level-based filtering.

Provides centralized logging setup for the application with:
- Daily log rotation with 7-day retention
- Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console and file output
- Thread-safe operation
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


# Default log directory relative to application root
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "etf_monitor.log"
DEFAULT_LOG_LEVEL = logging.INFO


def setup_logger(
    name: str = "etf_monitor",
    log_dir: Optional[str] = None,
    log_level: int = DEFAULT_LOG_LEVEL,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up the application logger with file rotation and optional console output.
    
    Args:
        name: Logger name
        log_dir: Directory for log files (created if doesn't exist)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Whether to output logs to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(log_level)
    
    # Create log directory if needed
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR
    
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure formatter
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname)-8s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with daily rotation (keep 7 days)
    log_file_path = log_path / DEFAULT_LOG_FILE
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file_path),
        when='midnight',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance by name.
    
    Args:
        name: Logger name (uses default if None)
        
    Returns:
        Logger instance
    """
    if name is None:
        name = "etf_monitor"
    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    """
    Set the log level for the application logger.
    
    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logger = get_logger()
    numeric_level = getattr(logging, level.upper(), DEFAULT_LOG_LEVEL)
    logger.setLevel(numeric_level)
    
    # Update all handlers
    for handler in logger.handlers:
        handler.setLevel(numeric_level)

