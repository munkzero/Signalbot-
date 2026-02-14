"""Logging utilities"""
from ..config.settings import should_log

def log_debug(msg: str):
    """Log debug message if level permits"""
    if should_log('DEBUG'):
        print(f"DEBUG: {msg}")

def log_info(msg: str):
    """Log info message if level permits"""
    if should_log('INFO'):
        print(f"INFO: {msg}")

def log_warning(msg: str):
    """Log warning message (always shown in INFO+)"""
    if should_log('WARNING'):
        print(f"WARNING: {msg}")

def log_error(msg: str):
    """Log error message (always shown)"""
    if should_log('ERROR'):
        print(f"ERROR: {msg}")
