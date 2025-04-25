"""
Module for Alpaca trading API client configuration and initialization.
"""
import os
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient


def get_alpaca_client(paper: bool = True) -> TradingClient:
    """
    Creates and returns an authenticated Alpaca Trading Client.
    
    Args:
        paper: If True, uses paper trading environment. Defaults to True.
    
    Returns:
        TradingClient: Authenticated Alpaca Trading Client instance.
        
    Raises:
        ValueError: If API credentials are not found in environment variables.
    """
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError(
            "Alpaca API credentials not found in environment variables. "
            "Please set ALPACA_API_KEY and ALPACA_API_SECRET."
        )
    
    return TradingClient(api_key, api_secret, paper=paper)
