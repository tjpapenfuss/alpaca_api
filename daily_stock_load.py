from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
from datetime import date, timedelta
from dotenv import load_dotenv
import os
from SQL_scripts.legacy_stock_data import StockDataLoader
from utils.data_loader import extract_top_tickers_from_csv
import config

if __name__ == "__main__":
    """Example usage of the StockDataLoader class."""
    # PostgreSQL connection configuration


    # Load environment variables from the .env file (if present)
    load_dotenv()

    # Access environment variables as if they came from the actual environment

    db_config = {
        'host': os.getenv('db_config.host', 'localhost'),
        'dbname': os.getenv('db_config.dbname'),
        'user': os.getenv('db_config.user'),
        'password': os.getenv('db_config.password'),
        'port': int(os.getenv('db_config.port'))
    }
    tickers_csv = config.yfinance_config['tickers_source']
    top_n = int(config.yfinance_config['top_n'])  # Number of top tickers to extract
    # Extract top tickers from CSV file
    tickers = extract_top_tickers_from_csv(tickers_csv, top_n=top_n)
    if not tickers:
        print("No tickers found in the CSV file. Exiting.")
        exit(1)
    start_date = (date.today() - timedelta(days=4)).strftime('%Y-%m-%d') # get yesterday's date
    end_date = date.today().strftime('%Y-%m-%d')
    loader = StockDataLoader(db_config)
    
    # Download stock data for Apple and NVIDIA
    # data = loader.download_stock_data(tickers, start_date=start_date, end_date=end_date, period='1mo', interval='1d')
    # Save data to database
    # loader.save_to_database(data)

    # Load data from database for verification
    loaded_data = loader.load_close_data_from_db(tickers, start_date=start_date, end_date=end_date)
    #latest_prices = loaded_data.iloc[-1]
    latest_prices = loaded_data.sort_index(ascending=False).head(1)
    print(latest_prices)
