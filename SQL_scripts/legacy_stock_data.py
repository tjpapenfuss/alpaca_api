import pandas as pd
import yfinance as yf
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta, date
import logging
from typing import List, Optional, Union, Dict, Any

class StockDataLoader:
    """
    Handles downloading stock data and storing it in the legacy_stock_data PostgreSQL database.
    """
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize the StockDataLoader.
        
        Args:
            db_config: Dictionary containing PostgreSQL connection parameters
                       (host, database, user, password, port)
        """
        self.db_config = db_config
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up and configure logger for the class."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _get_connection(self):
        """
        Create and return a connection to the PostgreSQL database.
        
        Returns:
            A connection to the PostgreSQL database
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Database connection error: {e}")
            raise
    

    def download_stock_data(self, 
                           tickers: List[str], 
                           start_date: Optional[Union[str, datetime]] = None,
                           end_date: Optional[Union[str, datetime]] = None,
                           period: str = "1y",
                           interval: str = "1d") -> pd.DataFrame:
        """
        Download stock data for the specified tickers.
        
        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for data (if None, uses period)
            end_date: End date for data (defaults to today)
            period: Period to download if start_date not specified (e.g., '1y', '6mo')
            
        Returns:
            DataFrame containing the stock data
        """
        self.logger.info(f"Downloading data for: {', '.join(tickers)}")
        
        if not start_date:
            start_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
            
        try:
            # Download data
            data = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                period=period if start_date is None else None,
                interval=interval,
                group_by='ticker',
                auto_adjust=True,
                threads=True
            )
            
            # If only one ticker is provided, add a ticker level to match multi-ticker format
            if len(tickers) == 1:
                ticker = tickers[0]
                data = pd.concat([data], axis=1, keys=[ticker])
                
            self.logger.info(f"Successfully downloaded data: {data.shape}")
            return data
        except Exception as e:
            self.logger.error(f"Error downloading stock data: {e}")
            raise

    def save_to_database(self, data: pd.DataFrame) -> None:
        """
        Save the downloaded stock data to the legacy_stock_data PostgreSQL database.
        
        Args:
            data: DataFrame containing stock data with multi-level columns
                    (ticker, [Open, High, Low, Close, Volume])
        """
        if data.empty:
            self.logger.warning("No data to save to database")
            return
        
        conn = self._get_connection()
        try:
            # Convert the multi-level DataFrame to a format suitable for database insertion
            records = []
            
            # Get all tickers from the DataFrame
            tickers = data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else [data.columns[0]]
            
            for ticker in tickers:
                ticker_data = data[ticker]
                
                for date, row in ticker_data.iterrows():
                    # Handle NaN values
                    record = (
                        date.strftime('%Y-%m-%d'),
                        ticker,
                        float(row['Open']) if not pd.isna(row['Open']) else None,
                        float(row['High']) if not pd.isna(row['High']) else None,
                        float(row['Low']) if not pd.isna(row['Low']) else None,
                        float(row['Close']) if not pd.isna(row['Close']) else None,
                        int(row['Volume']) if not pd.isna(row['Volume']) else None
                    )
                    records.append(record)
            
            # Insert records into the database using execute_batch for efficiency
            cursor = conn.cursor()
            query = '''
            INSERT INTO legacy_stock_data (date, ticker, open_price, close_price, high_price, low_price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, ticker) 
            DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume
            '''
            
            execute_batch(cursor, query, records, page_size=1000)
            conn.commit()
            self.logger.info(f"Successfully saved {len(records)} records to database")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error saving data to database: {e}")
            raise
        finally:
            conn.close()

    def load_close_data_from_db(self, 
                            tickers: List[str], 
                            start_date: Optional[Union[str, datetime]] = None,
                            end_date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
        """
        Load stock data from the database for the specified tickers and date range.
        
        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for data (defaults to 1 year ago)
            end_date: End date for data (defaults to today)
            
        Returns:
            DataFrame containing the stock data in the same format as download_stock_data()
        """
        if not start_date:
            start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.today().strftime('%Y-%m-%d')
            
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            placeholders = ','.join(['%s'] * len(tickers))
            
            query = f"""
            SELECT ticker, date, open_price, close_price, high_price, low_price, volume
            FROM public.legacy_stock_data
            WHERE ticker IN ({placeholders})
                AND date BETWEEN %s AND %s
            ORDER BY date, ticker
            """
            
            # Pass in tickers + date range as parameters
            params = tickers + [start_date, end_date]
            cursor.execute(query, params)
            
            # Fetch all records
            rows = cursor.fetchall()
            columns = ['ticker', 'date', 'open', 'close', 'high', 'low', 'volume']
            
            # Create DataFrame from fetched data
            df = pd.DataFrame(rows, columns=columns)
            conn.close()
            
            if df.empty:
                self.logger.warning("No data found in database for the specified criteria")
                return pd.DataFrame()
            
            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Get only close prices and pivot the data
            close_prices = df.pivot(index='date', columns='ticker', values='close')
            self.logger.info(f"Successfully loaded data from database: {close_prices.shape}")
            return close_prices
            
            
        except Exception as e:
            self.logger.error(f"Error loading data from database: {e}")
            raise
        finally:
            if conn:
                conn.close()
