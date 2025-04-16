
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import config
import json 
from datetime import date, timedelta

from SQL_scripts.buy_sell import insert_orders
from trading.trade_report import report, get_orders_v2
from utils.stock_data import get_stock_data

import psycopg2

def get_all_symbols():
    try:
        # Connect to your PostgreSQL database
        conn = psycopg2.connect(
            host=config.db_config['host'],
            dbname=config.db_config['dbname'],
            user=config.db_config['user'],
            password=config.db_config['password'],
            port=config.db_config.get('port', 5432)
        )
        cur = conn.cursor()

        # Execute query to get all distinct symbols
        cur.execute("SELECT DISTINCT symbol FROM Buy")
        symbols = cur.fetchall()

        # Close connections
        cur.close()
        conn.close()

        # Flatten and return as a list
        return [symbol[0] for symbol in symbols]

    except Exception as e:
        print("Error while fetching symbols:", e)
        return []

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

def print_buy_entries_for_each_ticker(df):
    tickers = df.columns.tolist()
    # Connect to your PostgreSQL database
    conn = psycopg2.connect(
        host=config.db_config['host'],
        dbname=config.db_config['dbname'],
        user=config.db_config['user'],
        password=config.db_config['password'],
        port=config.db_config.get('port', 5432)
    )
    try:
        with conn.cursor() as cur:
            for ticker in tickers:
                print(f"\n--- Entries for {ticker} ---")
                cur.execute("""
                    SELECT buy_order_id, symbol, buy_price, original_quantity, remaining_quantity, buy_datetime
                    FROM Buy
                    WHERE symbol = %s
                """, (ticker,))
                rows = cur.fetchall()
                if rows:
                    for row in rows:
                        print(row)
                else:
                    print("No entries found.")

    except Exception as e:
        print("Database error:", e)

if __name__ == '__main__':
    api_key = config.ALPACA_API_KEY
    api_secret = config.ALPACA_API_SECRET
    trading_client = TradingClient(api_key, api_secret, paper=True)
    # df = report(api=trading_client, prevDays=150)
    # insert_orders(df=df, db_config=config.db_config)

    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    prices_df = get_stock_data(start_date=yesterday,
                               end_date=today,
                               tickers_source=config.yfinance_config.get('tickers_source'),
                               top_n=config.yfinance_config.get('top_n'))
    print(prices_df)
    tickers = prices_df.columns.tolist()    
    print(tickers)
    print(get_orders_v2(api=trading_client, prevDays=150, symbols=tickers))

    # WHAT I NEED TO DO:
    # - I have the orders. I need to get all the orders for all 500 stocks. Try this in batches of 50. 
    # - Once I have all orders in the SQL DB, then I can run the below code to find the buy entries.
    # - Buy entries I can extract the price of the buy and compare it with the current price from prices_df.
    # - What I want is an output that I can show someone that says hey, here are the potential sells and 
    #   here is the value you could get from these sells. 

    # print_buy_entries_for_each_ticker(prices_df)
