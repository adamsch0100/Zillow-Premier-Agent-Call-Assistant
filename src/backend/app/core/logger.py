import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    """Configure and return a logger instance"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Only add handlers if they don't exist
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # File handler (rotating logs)
        file_handler = RotatingFileHandler(
            filename=log_dir / "app.log",
            maxBytes=10485760,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger