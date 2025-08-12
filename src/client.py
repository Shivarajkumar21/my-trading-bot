"""Binance Futures API client with comprehensive validation and error handling."""
import re
from typing import Dict, List, Optional, Union
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException, BinanceRequestException
import os
from .config import logger, API_KEY, API_SECRET

class BinanceFuturesClient:
    """Client for interacting with Binance Futures API with enhanced validation and error handling.
    
    This client provides a more robust interface to the Binance Futures API with:
    - Input validation
    - Comprehensive error handling
    - Automatic retries for transient failures
    - Rate limiting awareness
    - Detailed logging
    """
    
    # Constants for validation
    SYMBOL_PATTERN = re.compile(r'^[A-Z0-9]{5,20}$')
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self, testnet: bool = False, api_key: str = None, api_secret: str = None):
        """Initialize the Binance Futures client.
        
        Args:
            testnet: Whether to use the testnet environment.
            api_key: Optional API key (overrides environment variable).
            api_secret: Optional API secret (overrides environment variable).
            
        Raises:
            ValueError: If API credentials are missing or invalid.
            RuntimeError: If client initialization fails.
        """
        self.testnet = bool(testnet)
        # Try to use explicitly provided keys, then Futures keys, then fall back to Spot keys
        self._api_key = api_key or os.getenv('FUTURES_API_KEY') or API_KEY
        self._api_secret = api_secret or os.getenv('FUTURES_API_SECRET') or API_SECRET
        self._validate_credentials()
        self.client = self._initialize_client()
    
    def _validate_credentials(self) -> None:
        """Validate API credentials.
        
        Raises:
            ValueError: If credentials are missing or invalid.
        """
        if not self._api_key or not isinstance(self._api_key, str):
            raise ValueError("Missing or invalid Binance API key")
            
        if not self._api_secret or not isinstance(self._api_secret, str):
            raise ValueError("Missing or invalid Binance API secret")
            
        # Basic format validation for API key (alphanumeric, 64 chars)
        if not re.match(r'^[A-Za-z0-9]{64}$', self._api_key):
            raise ValueError("Invalid API key format")
            
        # Basic format validation for API secret (alphanumeric, 64 chars)
        if not re.match(r'^[A-Za-z0-9]{64}$', self._api_secret):
            raise ValueError("Invalid API secret format")
        
    def _initialize_client(self) -> BinanceClient:
        """Initialize and return the Binance client with proper configuration."""
        try:
            if self.testnet:
                # For testnet, use the testnet endpoint
                client = BinanceClient(
                    api_key=self._api_key,
                    api_secret=self._api_secret,
                    tld='com',
                    testnet=True
                )
            else:
                client = BinanceClient(
                    api_key=self._api_key,
                    api_secret=self._api_secret,
                    requests_params={'timeout': 15},
                    tld='com'
                )
            
            # Test the connection
            try:
                client.futures_ping()
                return client
            except Exception as e:
                if 'testnet' in str(e).lower():
                    raise RuntimeError("Testnet connection failed. Please ensure you're using testnet API keys.")
                raise
                
            
            return client
            
        except BinanceAPIException as e:
            error_msg = f"Binance API error during client initialization: {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Failed to initialize Binance client: {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg) from e
    
    def _get_proxies(self) -> Optional[Dict[str, str]]:
        """Get proxy configuration from environment variables if available.
        
        Returns:
            Optional dictionary with proxy configuration or None.
        """
        # Example: You can implement proxy support here if needed
        # For example, read from environment variables:
        # http_proxy = os.environ.get('HTTP_PROXY')
        # https_proxy = os.environ.get('HTTPS_PROXY')
        return None
    
    def _test_connection(self, client: BinanceClient) -> None:
        """Test the connection to the Binance API.
        
        Args:
            client: Initialized Binance client.
            
        Raises:
            RuntimeError: If connection test fails.
        """
        try:
            # Simple API call to test connectivity
            client.futures_ping()
            
            # Verify API key permissions
            account_info = client.futures_account()
            if 'canTrade' not in account_info or not account_info['canTrade']:
                raise RuntimeError("API key does not have trading permissions")
                
            logger.info("Successfully connected to Binance Futures API")
            
        except BinanceAPIException as e:
            error_msg = f"Binance API connection test failed: {e}"
            logger.critical(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_exchange_info(self, symbol: str = None) -> Dict:
        """Get exchange information with validation and error handling.
        
        Args:
            symbol: Optional trading pair symbol (e.g., 'BTCUSDT').
            
        Returns:
            dict: Exchange information for the specified symbol or all symbols.
            
        Raises:
            ValueError: If the symbol is invalid.
            BinanceAPIException: For API-related errors.
        """
        try:
            if symbol:
                if not self.validate_symbol(symbol):
                    raise ValueError(f"Invalid symbol: {symbol}")
                
                # Get exchange info for a specific symbol
                info = self._make_request(
                    self.client.futures_exchange_info,
                    symbol=symbol
                )
                
                # Extract the specific symbol's info
                for s in info.get('symbols', []):
                    if s['symbol'] == symbol:
                        return s
                
                raise ValueError(f"Symbol {symbol} not found in exchange info")
                
            # Get exchange info for all symbols
            return self._make_request(self.client.futures_exchange_info)
            
        except BinanceAPIException as e:
            logger.error(f"API error getting exchange info for {symbol or 'all symbols'}: {e}")
            raise
            
    def _make_request(self, func, *args, **kwargs):
        """Make an API request with retry logic.
        
        Args:
            func: The API function to call.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            The API response.
            
        Raises:
            BinanceAPIException: For API-related errors after retries.
            Exception: For other errors after retries.
        """
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return func(*args, **kwargs)
                
            except (BinanceAPIException, BinanceRequestException) as e:
                last_exception = e
                
                # Don't retry on client errors (4xx) except for rate limits
                if hasattr(e, 'status_code') and 400 <= e.status_code < 500 and 'too many requests' not in str(e).lower():
                    logger.error(f"Client error (will not retry): {e}")
                    break
                    
                # Log the error and wait before retrying
                wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                logger.warning(
                    f"API request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in API request: {e}")
                break
        
        # If we get here, all retries failed
        if last_exception:
            logger.error(f"API request failed after {self.MAX_RETRIES} attempts")
            raise last_exception
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get detailed information about a specific trading pair with validation.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            
        Returns:
            dict: Symbol information or None if not found.
            
        Raises:
            ValueError: If the symbol format is invalid.
            BinanceAPIException: For API-related errors.
        """
        if not isinstance(symbol, str) or not self.SYMBOL_PATTERN.match(symbol):
            raise ValueError(f"Invalid symbol format: {symbol}")
            
        try:
            info = self.get_exchange_info(symbol)
            
            # If we get here, the symbol exists in the exchange info
            for s in info.get('symbols', []):
                if s['symbol'] == symbol:
                    # Add additional validation for required fields
                    required_fields = [
                        'status', 'baseAsset', 'quoteAsset', 'filters',
                        'orderTypes', 'timeInForce', 'quotePrecision'
                    ]
                    
                    for field in required_fields:
                        if field not in s:
                            logger.warning(f"Missing required field '{field}' in symbol info for {symbol}")
                    
                    return s
            
            logger.warning(f"Symbol {symbol} not found in exchange info")
            return None
            
        except BinanceAPIException as e:
            logger.error(f"API error getting info for symbol {symbol}: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error getting info for symbol {symbol}: {e}")
            raise
    
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if a trading symbol exists and is active.
        
        Args:
            symbol: Trading pair symbol to validate (e.g., 'BTCUSDT').
            
        Returns:
            bool: True if symbol is valid and active for trading, False otherwise.
            
        Raises:
            ValueError: If the symbol format is invalid.
        """
        # Basic symbol format validation
        if not isinstance(symbol, str) or not re.match(r'^[A-Z0-9]{5,20}$', symbol):
            raise ValueError(f"Invalid symbol format: {symbol}")
            
        try:
            info = self.get_symbol_info(symbol)
            if not info:
                logger.warning(f"Symbol not found: {symbol}")
                return False
                
            if info.get('status') != 'TRADING':
                logger.warning(f"Symbol {symbol} is not trading. Status: {info.get('status')}")
                return False
                
            # Check if the symbol supports MARGIN and TRADING permissions
            permissions = info.get('permissions', [])
            if 'MARGIN' not in permissions or 'TRADING' not in permissions:
                logger.warning(f"Symbol {symbol} does not support margin trading. Permissions: {permissions}")
                return False
                
            return True
            
        except BinanceAPIException as e:
            logger.error(f"API error validating symbol {symbol}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating symbol {symbol}: {e}")
            return False
    
    def get_price(self, symbol: str) -> float:
        """Get the current price for a symbol with validation.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT').
            
        Returns:
            float: Current price of the symbol.
            
        Raises:
            ValueError: If the symbol is invalid or price cannot be retrieved.
            BinanceAPIException: For API-related errors.
        """
        if not self.validate_symbol(symbol):
            raise ValueError(f"Cannot get price for invalid symbol: {symbol}")
            
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            if not ticker or 'price' not in ticker:
                raise ValueError(f"Invalid response when getting price for {symbol}")
                
            price = float(ticker['price'])
            if price <= 0:
                raise ValueError(f"Invalid price received for {symbol}: {price}")
                
            return price
            
        except (ValueError, TypeError) as e:
            logger.error(f"Data format error getting price for {symbol}: {e}")
            raise ValueError(f"Failed to parse price for {symbol}") from e
            
        except BinanceAPIException as e:
            logger.error(f"API error getting price for {symbol}: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error getting price for {symbol}: {e}")
            raise
