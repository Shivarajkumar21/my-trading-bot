"""Configuration and settings management for the Binance Futures trading bot."""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TESTNET = os.getenv('TESTNET', 'false').lower() == 'true'

# Trading Configuration
DEFAULT_LEVERAGE = int(os.getenv('DEFAULT_LEVERAGE', '10'))
DEFAULT_QUANTITY = float(os.getenv('DEFAULT_QUANTITY', '0.01'))

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FILE = BASE_DIR / os.getenv('LOG_FILE', 'bot.log')

# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def setup_logger(name):
    """Configure and return a logger with the specified name."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Create a default logger
logger = setup_logger(__name__)
