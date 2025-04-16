from dotenv import load_dotenv
import os
import logging
import logging.handlers
import sys
from colorama import Fore, Back, Style, init

# Initialize colorama
init(autoreset=True)

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
        
# Console color configuration
class ColorConfig:
    def __init__(self):
        # Define colors for different console outputs
        self.thinking_color = os.environ.get("THINKING_COLOR", Fore.GREEN) 
        self.user_prompt_color = os.environ.get("USER_PROMPT_COLOR", Fore.YELLOW)
        self.claude_output_color = os.environ.get("CLAUDE_OUTPUT_COLOR", Fore.WHITE)
        self.tool_call_color = os.environ.get("TOOL_CALL_COLOR", Fore.BLUE)
        
        # Whether to use colors at all
        self.use_colors = os.environ.get("USE_COLORS", "true").lower() == "true"
        
    def thinking(self, text):
        """Format thinking text (grey and dim)"""
        if self.use_colors:
            return f"{self.thinking_color}{text}{Style.RESET_ALL}"
        return text
        
    def user_prompt(self, text):
        """Format user prompt text (white)"""
        if self.use_colors:
            return f"{self.user_prompt_color}{text}{Style.RESET_ALL}"
        return text
        
    def claude_output(self, text):
        """Format Claude's output text (green)"""
        if self.use_colors:
            return f"{self.claude_output_color}{text}{Style.RESET_ALL}"
        return text
        
    def tool_call(self, text):
        """Format tool call text (blue)"""
        if self.use_colors:
            return f"{self.tool_call_color}{text}{Style.RESET_ALL}"
        return text

class Config:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.logging = LoggingConfig()
        self.colors = ColorConfig()
        
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