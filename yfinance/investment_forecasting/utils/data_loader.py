import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def download_stock_data(tickers, start_date, end_date):
    """
    Download daily stock price data for the specified tickers and date range.
    
    Parameters:
    -----------
    tickers : list
        List of ticker symbols
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    
    Returns:
    --------
    tuple
        (stock_data, valid_tickers, failed_tickers)
    """
    print(f"Downloading data for {len(tickers)} tickers...")
    
    # Add buffer days before start date to calculate returns properly
    start_buffer = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=5)
    
    try:
        stock_data = yf.download(
            tickers=tickers, 
            start=start_buffer.strftime('%Y-%m-%d'), 
            end=end_date, 
            interval="1d", 
            group_by='ticker'
        )
        
        # Handle failed tickers
        valid_tickers = [ticker for ticker in tickers if ticker in stock_data.columns.levels[0]]
        failed_tickers = [ticker for ticker in tickers if ticker not in stock_data.columns.levels[0]]
        
        if failed_tickers:
            print(f"Failed to download data for {len(failed_tickers)} tickers.")
        
        print(f"Successfully downloaded data for {len(valid_tickers)} tickers.")
        
        return stock_data, valid_tickers, failed_tickers
        
    except Exception as e:
        print(f"Error downloading stock data: {e}")
        return None, [], tickers

def load_tickers_and_weights(config):
    """
    Load tickers and calculate allocation weights based on configuration.
    
    Parameters:
    -----------
    config : dict
        Configuration dictionary
    
    Returns:
    --------
    tuple
        (tickers, allocation_weights)
    """
    tickers_source = config.get('tickers_source', '')
    
    # Load tickers from CSV or use provided list
    if isinstance(tickers_source, str) and tickers_source.endswith('.csv'):
        tickers = extract_top_tickers_from_csv(
            tickers_source, 
            top_n=config.get('top_n', 250)
        )
    else:
        tickers = config.get('tickers_source', [])
    
    # Calculate allocation weights
    portfolio_allocation = config.get('portfolio_allocation', 'equal')
    
    if portfolio_allocation == 'equal':
        # Equal weight allocation
        weight = 1.0 / len(tickers)
        allocation_weights = {ticker: weight for ticker in tickers}
    elif isinstance(portfolio_allocation, dict):
        # User-provided weights
        # Normalize to ensure weights sum to 1
        total_weight = sum(portfolio_allocation.values())
        allocation_weights = {t: w/total_weight for t, w in portfolio_allocation.items() if t in tickers}
    elif isinstance(portfolio_allocation, str) and portfolio_allocation.endswith('.csv'):
        # Load weights from CSV
        try:
            weights_dict = extract_weights_from_csv(portfolio_allocation)
            # Filter for only our tickers and normalize
            filtered_weights = {t: weights_dict.get(t, 0) for t in tickers}
            total_weight = sum(filtered_weights.values())
            if total_weight > 0:
                allocation_weights = {t: w/total_weight for t, w in filtered_weights.items()}
            else:
                # Fall back to equal weight if no weights found
                weight = 1.0 / len(tickers)
                allocation_weights = {ticker: weight for ticker in tickers}
        except Exception as e:
            print(f"Error loading weights from CSV: {e}")
            # Fall back to equal weight
            weight = 1.0 / len(tickers)
            allocation_weights = {ticker: weight for ticker in tickers}
    else:
        # Default to equal weight
        weight = 1.0 / len(tickers)
        allocation_weights = {ticker: weight for ticker in tickers}
    
    return tickers, allocation_weights

def extract_top_tickers_from_csv(csv_path, top_n=250):
    """
    Extract top N tickers from a CSV file.
    
    Parameters:
    -----------
    csv_path : str
        Path to CSV file
    top_n : int
        Number of top tickers to extract
    
    Returns:
    --------
    list
        List of ticker symbols
    """
    try:
        df = pd.read_csv(csv_path)
        # Assume the CSV has a column named 'Symbol' or 'Ticker'
        ticker_col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        
        if ticker_col not in df.columns:
            raise ValueError(f"CSV does not contain a '{ticker_col}' column")
            
        # Take top N tickers
        tickers = df[ticker_col].head(top_n).tolist()
        return tickers
    except Exception as e:
        print(f"Error extracting tickers from CSV: {e}")
        return []

def extract_weights_from_csv(csv_path):
    """
    Extract ticker weights from a CSV file.
    
    Parameters:
    -----------
    csv_path : str
        Path to CSV file
    
    Returns:
    --------
    dict
        Dictionary mapping tickers to weights
    """
    try:
        df = pd.read_csv(csv_path)
        # Assume the CSV has columns named 'Symbol'/'Ticker' and 'Weight'
        ticker_col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
        weight_col = 'Weight' if 'Weight' in df.columns else 'weight'
        
        if ticker_col not in df.columns:
            raise ValueError(f"CSV does not contain a '{ticker_col}' column")
        if weight_col not in df.columns:
            raise ValueError(f"CSV does not contain a '{weight_col}' column")
            
        # Create dictionary of ticker to weight
        weights = dict(zip(df[ticker_col], df[weight_col]))
        return weights
    except Exception as e:
        print(f"Error extracting weights from CSV: {e}")
        return {}