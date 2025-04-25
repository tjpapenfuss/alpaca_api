"""User CRUD service for database operations."""
from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from alpaca.trading.client import TradingClient

# Import your actual data access functions
# For now, I'll implement placeholders
def get_all_symbols(user_id: str) -> List[str]:
    """
    Get all stock symbols for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of stock symbols
    """
    # Replace with actual implementation
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

def get_account_positions(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all positions for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        List of position dictionaries
    """
    # Replace with actual implementation
    from datetime import datetime
    
    return [
        {
            "buy_order_id": "order1",
            "symbol": "AAPL",
            "buy_price": 150.0,
            "original_quantity": 10.0,
            "remaining_quantity": 10.0,
            "buy_datetime": datetime.now()
        },
        {
            "buy_order_id": "order2",
            "symbol": "MSFT",
            "buy_price": 300.0,
            "original_quantity": 5.0,
            "remaining_quantity": 5.0,
            "buy_datetime": datetime.now()
        }
    ]

def buy_entries_for_tickers(user_id: str, df: Any) -> Any:
    """
    Get buy entries for specified tickers.
    
    Args:
        user_id: The user ID
        df: DataFrame of stock data
        
    Returns:
        DataFrame with buy entries
    """
    # Replace with actual implementation
    return df

from fastapi import Depends, HTTPException
import strawberry
from api.dependencies import get_trading_client, get_current_user_id, get_current_account_id
from utils.stock_data import get_stock_data, find_top_loss_stocks
from api.db import SessionLocal
from SQL_scripts.buy_sell import OrderManager
from SQL_scripts.legacy_stock_data import StockDataLoader
from SQL_scripts.position import PositionManager

async def get_loss_leaders(
    days_back: Optional[int] = 1,
    drop_threshold: Optional[float] = 10.0,
    top_n: Optional[int] = 5,
    trading_client: TradingClient = Depends(get_trading_client),
    current_user_id: str = strawberry.field(default_factory=get_current_user_id),
    account_id: str = strawberry.field(default_factory=get_current_account_id)
    ) -> List[Dict[str, Any]]:
    """
    Get the top stocks with the most significant losses.

    Args:
        days_back: How many days to look back for start date (default: 1)
        drop_threshold: Percentage threshold for considering a stock as a loss leader (default: 10.0%)
        top_n: Number of top loss leaders to return (default: 5)
        trading_client: Alpaca trading client dependency
        current_user_id: ID of the current user
    
    Returns:
        List of dictionaries containing loss leader stock information
    """
    try:
        today = date.today().strftime("%Y-%m-%d")
        start_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        db = SessionLocal()
        try:
            orderer = OrderManager(db=db, user_id=current_user_id, account_id=account_id)
            loader = StockDataLoader(db=db)
            position_mgr = PositionManager(db=db, user_id=current_user_id, account_id=account_id)
        finally:
            db.close()
        tickers = orderer.get_all_symbols()

        # Load data from database and find top loss stocks
        prices_df = loader.load_close_data_from_db(tickers)
        buys_df = orderer.buy_entries_for_tickers(df=prices_df)
    
        # Find top loss leaders
        loss_leaders = find_top_loss_stocks(buys_df, prices_df, drop_threshold=drop_threshold, top=top_n)
        return loss_leaders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving loss leaders: {str(e)}")