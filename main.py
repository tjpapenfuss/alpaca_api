
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import config
import json 
from datetime import date, timedelta
from dotenv import load_dotenv
import os

from SQL_scripts.buy_sell import OrderManager
from trading.trade_report import report, get_orders_v2
from utils.stock_data import get_stock_data, find_top_loss_stocks

import psycopg2
from SQL_scripts.legacy_stock_data import StockDataLoader
from SQL_scripts.position import PositionManager

# Function to get Buy entries for a specific symbol
# def get_buy_entries_for_symbol(symbol):
#     # Connect to your PostgreSQL database
#     conn = psycopg2.connect(
#         host=config.db_config['host'],
#         dbname=config.db_config['dbname'],
#         user=config.db_config['user'],
#         password=config.db_config['password'],
#         port=config.db_config.get('port', 5432)
#     )
#     cur = conn.cursor()

#     try:
#         with psycopg2.connect(
#             host="your_host",
#             port="5432",
#             dbname="your_db",
#             user="your_user",
#             password="your_password"
#         ) as conn:
#             with conn.cursor() as cur:
#                 cur.execute("SELECT * FROM Buy WHERE symbol = %s", (symbol,))
#                 return cur.fetchall()
#     except Exception as e:
#         print(f"Error fetching entries for {symbol}:", e)
#         return []

if __name__ == '__main__':
    load_dotenv()
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')
    trading_client = TradingClient(api_key, api_secret, paper=True)
    db_config = {
        'host': os.getenv('db_config.host', 'localhost'),
        'dbname': os.getenv('db_config.dbname'),
        'user': os.getenv('db_config.user'),
        'password': os.getenv('db_config.password'),
        'port': int(os.getenv('db_config.port'))
    }
    from api.db import SessionLocal

    db = SessionLocal()
    try:
        orderer = OrderManager(db=db, user_id=os.getenv('user_id'), account_id=os.getenv('account_id'))
        loader = StockDataLoader(db=db)
        position_mgr = PositionManager(db=db, user_id=os.getenv('user_id'), account_id=os.getenv('account_id'))
    finally:
        db.close()

    position_mgr.hydrate_positions()

    # --------------------#
    # This block of code can be used to pull in transactions from alpaca.markets. 
    # This will only pull in transactions 500 at a time so be careful with how many transactions you have. 
    # ------------------- #
    '''
    from utils.update_trade_db import update_trade_database
    from utils.data_loader import extract_top_tickers_from_csv
    tickers = extract_top_tickers_from_csv(csv_file=config.yfinance_config.get('tickers_source'), 
        top_n=config.yfinance_config.get('top_n'))
    tickers.append('SPY')  # Ensure SPY is included in the list
    # tickers = ['SPY']
    update_trade_database(api_client=trading_client, orderer=orderer, days_to_fetch=150,
        db_config=db_config, symbols=tickers)
    '''

    # The rest of your existing code for getting today's stock data
    today = date.today().strftime("%Y-%m-%d")
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    tickers = orderer.get_all_symbols()
    start_date = (date.today() - timedelta(days=4)).strftime('%Y-%m-%d') # get yesterday's date
    end_date = date.today().strftime('%Y-%m-%d')

    # Load data from database and find top loss stocks
    prices_df = loader.load_close_data_from_db(tickers, start_date=start_date, end_date=end_date)
    buys_df = orderer.buy_entries_for_tickers(df=prices_df)

    find_top_loss_stocks(buys_df, prices_df, drop_threshold=10.0, top=15)

    # Compare prices for matching symbols
    # for _, buy_row in buys_df.iterrows():
    #     symbol = buy_row['symbol']
    #     buy_price = float(buy_row['buy_price'])  # Assuming there's a 'price' column in buys_df
        
    #      # Check if the symbol exists as a column in prices_df
    #     if symbol in prices_df.columns:
    #         # Get the most recent price from prices_df for this symbol
    #         # (using the last row in the DataFrame)
    #         price_from_prices_df = float(prices_df[symbol].iloc[-1])
            
    #         # Compare prices
    #         if price_from_prices_df <= buy_price * 0.9:  # 10% or more drop
    #             percentage_drop = ((buy_price - price_from_prices_df) / buy_price) * 100
    #             print(f"Symbol: {symbol} - ALERT! Price dropped {percentage_drop:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
    #         elif price_from_prices_df < buy_price:
    #             # If there's a drop, but less than 10%
    #             percentage_drop = ((buy_price - price_from_prices_df) / buy_price) * 100
    #             print(f"Symbol: {symbol} - Price dropped {percentage_drop:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
    #         elif price_from_prices_df > buy_price:
    #             percentage_gain = ((price_from_prices_df - buy_price) / buy_price) * 100
    #             print(f"Symbol: {symbol} - Price increased {percentage_gain:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
    #         else:
    #             print(f"Symbol: {symbol} - Price unchanged at ${buy_price:.2f}")
    #     else:
    #         print(f"Symbol: {symbol} - Not found in prices_df")

