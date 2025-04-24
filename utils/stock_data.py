from utils.data_loader import download_stock_data, extract_top_tickers_from_csv


def get_stock_data(start_date, end_date, top_n, tickers=None, tickers_source=None, pickle_file=None):

    if tickers is None and tickers_source is not None:
        tickers = extract_top_tickers_from_csv(
                csv_file=tickers_source, 
                top_n=top_n
            )
    elif tickers is None and tickers_source is None:
        print("Error: No tickers provided and no tickers source file specified.")
        return None
    # Download historical stock data
    valid_tickers, stock_data = download_stock_data(
        tickers=tickers, 
        start_date=start_date, 
        end_date=end_date,
        top_n=top_n, 
        interval="1d",
        pickle_file=pickle_file
    )

    return extract_price_data(stock_data=stock_data)

def extract_price_data(stock_data, decimals=2):
        """
        Extract price data from stock data.
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame of adjusted close prices
        """
        if "Close" in stock_data.columns.levels[1]:
            close_prices = stock_data.xs("Close", level=1, axis=1)
            return close_prices.round(decimals)
        else:
            print("Error: 'Close' column not found in data.")
            return None
        
def find_top_loss_stocks(buys_df, prices_df, drop_threshold=10.0, top=5):
    """
    Find stocks that have dropped significantly and calculate the resulting losses.
    
    Args:
        buys_df (pandas.DataFrame): DataFrame containing buy information including
                                    'symbol', 'filled_avg_price', and 'quantity_remaining'.
        prices_df (pandas.DataFrame): DataFrame containing current prices with 
                                      symbols as column names.
        drop_threshold (float): Minimum percentage drop to be considered significant (default: 10.0).
        top_n (int): Number of top stocks to return (default: 5).
        
    Returns:
        list: A list of dictionaries containing information about the top N stocks 
              with the highest dollar losses.
    """
    # Create a list to collect stocks with significant drops
    significant_drops = []
    
    # Compare prices for matching symbols
    for _, buy_row in buys_df.iterrows():
        symbol = buy_row['symbol']
        filled_avg_price = float(buy_row['filled_avg_price'])
        quantity = float(buy_row['remaining_qty'])  # Get remaining quantity
        
        # Check if the symbol exists as a column in prices_df
        if symbol in prices_df.columns:
            # Get the most recent price from prices_df for this symbol
            current_price = float(prices_df[symbol].iloc[-1])
            
            # Calculate percentage drop
            if current_price < filled_avg_price:
                percentage_drop = ((filled_avg_price - current_price) / filled_avg_price) * 100
                
                # Check if drop is more than the threshold (e.g., 10% or more)
                if percentage_drop >= drop_threshold:
                    # Calculate total loss in dollar value
                    dollar_loss = (filled_avg_price - current_price) * quantity
                    
                    # Add to our collection of significant drops
                    significant_drops.append({
                        'symbol': symbol,
                        'percentage_drop': percentage_drop,
                        'filled_avg_price': filled_avg_price,
                        'current_price': current_price,
                        'quantity': quantity,
                        'dollar_loss': dollar_loss
                    })
        else:
            print(f"Symbol: {symbol} - Not found in prices_df")
    
    # Sort significant drops by dollar loss (highest to lowest)
    significant_drops.sort(key=lambda x: x['dollar_loss'], reverse=True)
    
    # Return the top drops (or fewer if less than 5 significant drops)
    top_drops = significant_drops[:top]
    
    # Print the results
    if top_drops:
        print(f"Top {top} Stocks with Highest Dollar Losses (10%+ drops):")
        for i, drop in enumerate(top_drops, 1):
            print(f"{i}. {drop['symbol']} - ${drop['dollar_loss']:.2f} loss " 
                  f"(Down {drop['percentage_drop']:.2f}% from ${drop['filled_avg_price']:.2f} " 
                  f"to ${drop['current_price']:.2f}, {drop['quantity']} shares)")
    else:
        print("No stocks with drops of 10% or more were found.")
    
    return top_drops