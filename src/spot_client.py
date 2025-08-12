"""Binance Spot API client with comprehensive validation and error handling."""
import re
import time
import logging
from typing import Dict, List, Optional, Union
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
from .config import logger, API_KEY, API_SECRET, TESTNET

class BinanceSpotClient:
    """Client for interacting with Binance Spot API with enhanced validation and error handling."""
    
    # Constants for validation
    SYMBOL_PATTERN = re.compile(r'^[A-Z0-9]{5,20}$')
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, testnet: bool = False, api_key: str = None, api_secret: str = None):
        """Initialize the Binance Spot client.
        
        Args:
            testnet: Whether to use the testnet environment.
            api_key: Optional API key (overrides environment variable).
            api_secret: Optional API secret (overrides environment variable).
        """
        self.testnet = testnet or TESTNET
        self._api_key = api_key or API_KEY
        self._api_secret = api_secret or API_SECRET
        self._validate_credentials()
        self.client = self._initialize_client()
    
    def _validate_credentials(self) -> None:
        """Validate API credentials."""
        if not self._api_key or not isinstance(self._api_key, str):
            raise ValueError("Missing or invalid Binance API key")
            
        if not self._api_secret or not isinstance(self._api_secret, str):
            raise ValueError("Missing or invalid Binance API secret")
    
    def _initialize_client(self) -> BinanceClient:
        """Initialize and return the Binance client with proper configuration."""
        try:
            client = BinanceClient(
                api_key=self._api_key,
                api_secret=self._api_secret,
                testnet=self.testnet,
                requests_params={'timeout': 15}
            )
            
            # Test the connection
            client.get_account()
            return client
            
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"Binance API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get information about a trading pair."""
        try:
            info = self.client.get_symbol_info(symbol.upper())
            if not info:
                logger.warning(f"No information found for symbol: {symbol}")
            return info
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            raise
    
    def get_price(self, symbol: str) -> float:
        """Get the current price for a symbol."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol.upper())
            return float(ticker['price'])
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            raise
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        """Place a market order."""
        try:
            params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'MARKET',
                'quantity': quantity
            }
            
            if self.testnet:
                return self.client.create_test_order(**params)
            return self.client.create_order(**params)
            
        except Exception as e:
            logger.error(f"Error placing {side} market order for {quantity} {symbol}: {e}")
            raise
