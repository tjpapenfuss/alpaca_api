
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import config
import json 
from datetime import date, timedelta

from SQL_scripts.buy_sell import insert_orders, buy_entries_for_tickers, get_all_symbols
from trading.trade_report import report, get_orders_v2
from utils.stock_data import get_stock_data

import psycopg2

# Function to get Buy entries for a specific symbol
def get_buy_entries_for_symbol(symbol):
    # Connect to your PostgreSQL database
    conn = psycopg2.connect(
        host=config.db_config['host'],
        dbname=config.db_config['dbname'],
        user=config.db_config['user'],
        password=config.db_config['password'],
        port=config.db_config.get('port', 5432)
    )
    cur = conn.cursor()

    try:
        with psycopg2.connect(
            host="your_host",
            port="5432",
            dbname="your_db",
            user="your_user",
            password="your_password"
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM Buy WHERE symbol = %s", (symbol,))
                return cur.fetchall()
    except Exception as e:
        print(f"Error fetching entries for {symbol}:", e)
        return []

if __name__ == '__main__':
    api_key = config.ALPACA_API_KEY
    api_secret = config.ALPACA_API_SECRET
    trading_client = TradingClient(api_key, api_secret, paper=True)
    
    # Example of calling the trade retrieval function (commented out for now)
    # from utils.update_trade_db import update_trade_database
    # update_trade_database(trading_client, 150, config.db_config, user_id=config.user_id)
    
    # The rest of your existing code for getting today's stock data
    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    tickers = get_all_symbols(user_id=config.user_id)
    pickle_file = f"C:/Users/tjpap/sandbox/alpaca_api/pickle_files/test-{len(tickers)}-{yesterday}-{today}.pkl"
    prices_df = get_stock_data(start_date=yesterday,
                               end_date=today,
                               tickers=tickers,
                               # tickers_source=config.yfinance_config.get('tickers_source'),
                               top_n=len(tickers),
                               pickle_file=pickle_file
                               )

    buys_df = buy_entries_for_tickers(prices_df)
    # print(buys_df)
    # print(prices_df)
    # Compare prices for matching symbols
    for _, buy_row in buys_df.iterrows():
        symbol = buy_row['symbol']
        buy_price = float(buy_row['buy_price'])  # Assuming there's a 'price' column in buys_df
        
         # Check if the symbol exists as a column in prices_df
        if symbol in prices_df.columns:
            # Get the most recent price from prices_df for this symbol
            # (using the last row in the DataFrame)
            price_from_prices_df = float(prices_df[symbol].iloc[-1])
            
            # Compare prices
            if price_from_prices_df <= buy_price * 0.9:  # 10% or more drop
                percentage_drop = ((buy_price - price_from_prices_df) / buy_price) * 100
                print(f"Symbol: {symbol} - ALERT! Price dropped {percentage_drop:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
            elif price_from_prices_df < buy_price:
                # If there's a drop, but less than 10%
                percentage_drop = ((buy_price - price_from_prices_df) / buy_price) * 100
                print(f"Symbol: {symbol} - Price dropped {percentage_drop:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
            elif price_from_prices_df > buy_price:
                percentage_gain = ((price_from_prices_df - buy_price) / buy_price) * 100
                print(f"Symbol: {symbol} - Price increased {percentage_gain:.2f}% from ${buy_price:.2f} to ${price_from_prices_df:.2f}")
            else:
                print(f"Symbol: {symbol} - Price unchanged at ${buy_price:.2f}")
        else:
            print(f"Symbol: {symbol} - Not found in prices_df")

    # WHAT I NEED TO DO:
    # - Run this and you see I have the comparison. Now I just need to find a way to merge this with 
    #   existing functionality for TLH.
    # - 
    # - I have the orders. I need to get all the orders for all 500 stocks. Try this in batches of 50. 
    # - Once I have all orders in the SQL DB, then I can run the below code to find the buy entries.
    # - Buy entries I can extract the price of the buy and compare it with the current price from prices_df.
    # - What I want is an output that I can show someone that says hey, here are the potential sells and 
    #   here is the value you could get from these sells. 

    # print_buy_entries_for_each_ticker(prices_df)
