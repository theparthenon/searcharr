"""
Searcharr
Sonarr & Radarr Telegram Bot
Logging Utilities
By Todd Roberts
https://github.com/toddrob99/searcharr
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_verbose = False
_console_logging = False


def configure_logging(verbose=False, console_logging=False):
    """Set global logging defaults for all subsequent set_up_logger calls.

    Args:
        verbose (bool): Enable debug logging globally.
        console_logging (bool): Enable console logging globally.
    """
    global _verbose, _console_logging
    _verbose = verbose
    _console_logging = console_logging


def set_up_logger(logger_name, verbose=None, console_logging=None):
    """Set up and configure a logger.

    Args:
        logger_name (str): The name of the logger
        verbose (bool, optional): Enable debug logging. Defaults to global setting.
        console_logging (bool, optional): Enable console logging. Defaults to global setting.

    Returns:
        logging.Logger: The configured logger
    """
    if verbose is None:
        verbose = _verbose
    if console_logging is None:
        console_logging = _console_logging

    # Set up logging level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create logger if it doesn't exist
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False
    # Clear existing handlers to avoid duplicate logs on re-initialization
    if logger.handlers:
        logger.handlers.clear()

    # Define log format
    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Set up file logging
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
        "logs",
    )

    # Create logs directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Add file handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f"{logger_name.replace('.', '_')}.log"),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # Add console handler if enabled
    if console_logging:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    return logger
