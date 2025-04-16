from utils.data_loader import download_stock_data, extract_top_tickers_from_csv


def get_stock_data(start_date, end_date, tickers_source, top_n):

    tickers = extract_top_tickers_from_csv(
            csv_file=tickers_source, 
            top_n=top_n
        )
    # Download historical stock data
    valid_tickers, stock_data = download_stock_data(
        tickers=tickers, 
        start_date=start_date, 
        end_date=end_date,
        tickers_source=tickers_source,
        top_n=top_n, 
        interval="1d",
        pickle_file="C:/Users/tjpap/sandbox/alpaca_api/test-5-2025-04-15-2025-04-16.pkl"
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