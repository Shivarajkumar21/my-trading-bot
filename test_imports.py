"""Test script to verify imports and basic functionality."""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load environment variables
load_dotenv()

try:
    from src.client import BinanceFuturesClient
    from src.spot_client import BinanceSpotClient
    from src.config import setup_logger, logger
    
    print("All imports successful!")
    print(f"BinanceFuturesClient: {BinanceFuturesClient}")
    print(f"BinanceSpotClient: {BinanceSpotClient}")
    
    # Test logger
    logger = setup_logger('test_imports')
    logger.info("Test logging message")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
