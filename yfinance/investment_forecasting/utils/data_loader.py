import yfinance as yf
from ..utils.date_utils import get_closest_trading_day
import pandas as pd
from datetime import datetime, timedelta

def download_stock_data(tickers, start_date, end_date):
    """
    Download daily stock price data for the specified tickers and date range.
    """
    
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
        tickers = valid_tickers
        
        # Took out returning failed tickers. Can put this back in if necessary
        return valid_tickers, stock_data
        
    except Exception as e:
        print(f"Error downloading stock data: {e}")
        return None, tickers
    
def extract_tickers_from_source(source, top_n=250):
    """
    Extract ticker symbols from a source (CSV file or list).
    """
    # Implementation...

def extract_top_tickers_from_csv(csv_file, top_n=10):
    # Read the CSV file
    csv_data = pd.read_csv(csv_file)
    
    # Sort by Weight column in descending order
    sorted_data = csv_data.sort_values('Weight', ascending=False)
    
    # Take only the top n tickers
    top_tickers = sorted_data.head(top_n)
    
    # Extract the symbols
    symbols = top_tickers['Symbol'].tolist()
    
    # Join symbols with a space for yfinance
    # tickers_string = " ".join(symbols)
    
    print(f"Selected top {len(symbols)} tickers by weight: {symbols}")
    
    return symbols

# Read the CSV file to extract the symbols and weights
def extract_weights_from_csv(csv_file):
    # Read the CSV file
    csv_data = pd.read_csv(csv_file)
    
    # Create a dictionary mapping Symbol to Weight with rounded values
    weights_dict = dict(zip(csv_data['Symbol'], csv_data['Weight']))
    
    return weights_dict

# # Add weights to your existing ranked DataFrame
# def add_weights_to_ranked_list(ranked_df, weights_dict):
#     # Create a new column for the weights
#     ranked_df['Portfolio_Weight'] = ranked_df['Ticker'].map(weights_dict)
    
#     # Calculate the weighted impact on the portfolio
#     # ranked_df['Weighted_Impact'] = ranked_df['Percent_Change'] * ranked_df['Portfolio_Weight']
    
#     # Optional: Convert weights to percentage format for better readability
#     ranked_df['Portfolio_Weight'] = round(ranked_df['Portfolio_Weight'] * 100, 2)
    
#     return ranked_df