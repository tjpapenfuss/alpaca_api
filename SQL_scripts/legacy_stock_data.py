import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, date
import logging
from typing import List, Optional, Union, Dict, Any

class StockDataLoader:
    """
    Handles downloading stock data and storing it in the legacy_stock_data database using SQLAlchemy.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the StockDataLoader.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
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
            interval: Data interval (e.g., '1d', '1h')
            
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
        Save the downloaded stock data to the legacy_stock_data database using SQLAlchemy.
        
        Args:
            data: DataFrame containing stock data with multi-level columns
                  (ticker, [Open, High, Low, Close, Volume])
        """
        if data.empty:
            self.logger.warning("No data to save to database")
            return
        
        try:
            # Convert the multi-level DataFrame to a format suitable for database insertion
            records = []
            
            # Get all tickers from the DataFrame
            tickers = data.columns.levels[0] if isinstance(data.columns, pd.MultiIndex) else [data.columns[0]]
            
            for ticker in tickers:
                ticker_data = data[ticker]
                
                for date_idx, row in ticker_data.iterrows():
                    date_str = date_idx.strftime('%Y-%m-%d')
                    
                    # Use SQLAlchemy's text() to execute raw SQL
                    query = text("""
                    INSERT INTO legacy_stock_data 
                    (date, ticker, open_price, high_price, low_price, close_price, volume)
                    VALUES 
                    (:date, :ticker, :open, :high, :low, :close, :volume)
                    ON CONFLICT (date, ticker) 
                    DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                    """)
                    
                    # Execute the query with parameters
                    self.db.execute(query, {
                        'date': date_str,
                        'ticker': ticker,
                        'open': float(row['Open']) if not pd.isna(row['Open']) else None,
                        'high': float(row['High']) if not pd.isna(row['High']) else None,
                        'low': float(row['Low']) if not pd.isna(row['Low']) else None,
                        'close': float(row['Close']) if not pd.isna(row['Close']) else None,
                        'volume': int(row['Volume']) if not pd.isna(row['Volume']) else None
                    })
            
            # Commit the transaction
            self.db.commit()
            self.logger.info(f"Successfully saved stock data to database")
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error saving data to database: {e}")
            raise

    def load_close_data_from_db(self, 
                            tickers: List[str], 
                            start_date: Optional[Union[str, datetime]] = None,
                            end_date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
        """
        Load stock data from the database for the specified tickers and date range.
        
        Args:
            tickers: List of stock ticker symbols
            start_date: Start date for data (defaults to 2 weeks ago)
            end_date: End date for data (defaults to today)
            
        Returns:
            DataFrame containing the close prices with dates as index and tickers as columns
        """
        if not start_date:
            start_date = (datetime.today() - timedelta(days=14)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.today().strftime('%Y-%m-%d')
            
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')
            
        if not tickers:
            self.logger.warning("No tickers provided for loading data from database")
            return pd.DataFrame()
            
        try:
            # Convert list of tickers to comma-separated string for SQL IN clause
            ticker_params = ', '.join([f"'{ticker}'" for ticker in tickers])
            
            query = text(f"""
            SELECT ticker, date, open_price, close_price, high_price, low_price, volume
            FROM public.legacy_stock_data
            WHERE ticker IN ({ticker_params})
                AND date BETWEEN :start_date AND :end_date
            ORDER BY date, ticker
            """)
            
            # Execute query with parameters
            result = self.db.execute(query, {
                'start_date': start_date,
                'end_date': end_date
            })
            
            # Convert result to a list of dictionaries
            rows = [dict(row._mapping) for row in result]
            
            if not rows:
                self.logger.warning("No data found in database for the specified criteria")
                return pd.DataFrame()
            
            # Create DataFrame from fetched data
            df = pd.DataFrame(rows)
            
            # Convert date to datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Get only close prices and pivot the data
            close_prices = df.pivot(index='date', columns='ticker', values='close_price')
            self.logger.info(f"Successfully loaded data from database: {close_prices.shape}")
            return close_prices
            
        except Exception as e:
            self.logger.error(f"Error loading data from database: {e}")
            raise