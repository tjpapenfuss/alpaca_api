from SQL_scripts.buy_sell import insert_orders
from trading.trade_report import report, get_orders_v2
from alpaca.trading.client import TradingClient
import config
from datetime import date, timedelta
from utils.stock_data import get_stock_data

# Function to batch the list
def batch_list(items: list, batch_size: int) -> list[list]:
    """
    Split a list into batches of specified size.
    
    Args:
        items: The list to split into batches
        batch_size: The maximum size of each batch
        
    Returns:
        A list of lists, where each inner list is a batch
    """
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def update_trade_database(api_client: TradingClient, days_to_fetch: int = 150, 
                          db_config: dict = None, symbols: list = None) -> None:
    """
    Retrieve historical trade information from Alpaca and store in the database.
    
    This function fetches historical trading data for specified symbols (or all available 
    symbols if none provided) and stores the results in a database. It's designed to be 
    used when you need to capture and archive previous trade information that may not 
    already exist in your database.
    
    Args:
        api_client: Alpaca trading client instance
        days_to_fetch: Number of previous days of trade data to retrieve (default: 150)
        db_config: Database configuration dictionary for connection
        symbols: Optional list of stock symbols to fetch. If None, will use all available symbols
                 from your price data.
    
    Usage:
        # To update trades for all tracked symbols:
        update_trade_database(trading_client, 150, config.db_config)
        
        # To update trades for specific symbols:
        update_trade_database(trading_client, 150, config.db_config, ['AAPL', 'MSFT'])
    
    Note:
        Before running this function, consider checking if the trades already exist in your
        database to avoid duplicate entries and unnecessary API calls.
    """
    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    if symbols is None:
        # Get your tickers list - implement this or use the same method as in your main code
        prices_df = get_stock_data(start_date=yesterday,
                                  end_date=today,
                                  tickers_source=config.yfinance_config.get('tickers_source'),
                                  top_n=config.yfinance_config.get('top_n'))
        symbols = prices_df.columns.tolist()
    
    # Process in batches of 100 tickers to avoid API limitations
    batched_symbols = batch_list(symbols, 100)
    
    for i, batch in enumerate(batched_symbols):
        print(f"Processing batch {i+1}/{len(batched_symbols)} (size {len(batch)}): {batch[:5]}...")
        
        # Fetch orders for the current batch of symbols
        trade_df = get_orders_v2(api=api_client, prevDays=days_to_fetch, symbols=batch)
        
        # Store the fetched orders in the database
        if not trade_df.empty:
            insert_orders(df=trade_df, db_config=db_config)
            print(f"Inserted {len(trade_df)} trade records for batch {i+1}")
        else:
            print(f"No trades found for batch {i+1}")