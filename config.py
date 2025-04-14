from dotenv import load_dotenv
import os
import logging
import logging.handlers
import sys

load_dotenv()

# Logging configuration
class LoggingConfig:
    def __init__(self):
        self.log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        self.log_file = os.environ.get("LOG_FILE", "claude_app.log")
        self.log_format = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        self.max_log_size = int(os.environ.get("MAX_LOG_SIZE", 5 * 1024 * 1024))  # 5 MB default
        self.backup_count = int(os.environ.get("LOG_BACKUP_COUNT", 3))  # Default to 3 backup files
        self.console_logging = os.environ.get("CONSOLE_LOGGING", "true").lower() == "true"

class Config:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.logging = LoggingConfig()
        
    def setup_logging(self):
        """Set up the logging configuration"""
        # Get the root logger
        logger = logging.getLogger()
        
        # Set the log level
        log_level = getattr(logging, self.logging.log_level, logging.INFO)
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(self.logging.log_format)
        
        # Set up file handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.logging.log_file,
            maxBytes=self.logging.max_log_size,
            backupCount=self.logging.backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Optionally add console logging
        if self.logging.console_logging:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
        # Log startup information
        logging.info(f"Logging initialized at level {self.logging.log_level}")
        
        return logger

cfg = Config()