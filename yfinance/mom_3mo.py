import pandas as pd
import yfinance as yf
from pull_tickers import extract_weights_from_csv, add_weights_to_ranked_list, extract_top_tickers_from_csv
from datetime import datetime

# ---------------------------------------------------------------------------------------------------
# Gather tickers from S&P 500 CSV
# ---------------------------------------------------------------------------------------------------
tickers = extract_top_tickers_from_csv('../sp500_companies.csv', top_n=250)  
tickers_list = tickers.split()
start_date = "2023-01-01"
end_date = "2024-01-02"

# ---------------------------------------------------------------------------------------------------
# Download stock data (batch download)
# ---------------------------------------------------------------------------------------------------
print(f"Downloading data for tickers: {len(tickers_list)} tickers")
# Use monthly interval instead of quarterly for more consistent data points
raw_data = yf.download(tickers=tickers_list, start=start_date, end=end_date, interval="1mo", group_by='ticker')
print(raw_data)
# ---------------------------------------------------------------------------------------------------
# Identify failed tickers
# ---------------------------------------------------------------------------------------------------
failed_tickers = [ticker for ticker in tickers_list if ticker not in raw_data.columns.levels[0]]
valid_tickers = [ticker for ticker in tickers_list if ticker in raw_data.columns.levels[0]]

# Print results
if failed_tickers:
    print(f"\n❌ Failed to download: {len(failed_tickers)} tickers")
print(f"✅ Processed valid tickers: {len(valid_tickers)} tickers\n")

# ---------------------------------------------------------------------------------------------------
# Extract Open Prices (Only for Valid Tickers)
# ---------------------------------------------------------------------------------------------------
if "Open" in raw_data.columns.levels[1]:  
    open_prices = raw_data.xs("Open", level=1, axis=1)  # Extract 'Open' price for valid tickers
else:
    print("Error: 'Open' column missing in data. Exiting.")
    exit()
print(open_prices)
# ---------------------------------------------------------------------------------------------------
# Filter for quarterly data (Jan, Apr, Jul, Oct)
# ---------------------------------------------------------------------------------------------------
quarterly_months = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct for quarterly data
quarterly_data = open_prices[open_prices.index.month.isin(quarterly_months)].copy()

# ---------------------------------------------------------------------------------------------------
# Prepare DataFrame with Quarterly Stock Data
# ---------------------------------------------------------------------------------------------------
result_df = pd.DataFrame()

for ticker in valid_tickers:
    ticker_data = quarterly_data[ticker].dropna()  # Drop NaN values for this ticker
    
    # Skip tickers with insufficient data
    if len(ticker_data) < 2:
        print(f"Skipping {ticker}: insufficient quarterly data points")
        continue
        
    temp_df = pd.DataFrame({
        'Date': ticker_data.index,
        'Ticker': ticker,
        'Open': ticker_data.values.round(2)  # Round to 2 decimals
    })
    result_df = pd.concat([result_df, temp_df])

# Sort and reset index
result_df = result_df.sort_values(['Ticker', 'Date']).reset_index(drop=True)

# ---------------------------------------------------------------------------------------------------
# Calculate quarter-over-quarter changes
# ---------------------------------------------------------------------------------------------------
performance_data = []

for ticker in valid_tickers:
    # Get data for this ticker
    ticker_data = result_df[result_df['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)
    
    # Skip tickers with insufficient data
    if len(ticker_data) < 2:
        continue
        
    row_data = {
        "Ticker": ticker,
        "Start_Date": ticker_data.loc[0, "Date"].strftime('%Y-%m-%d'),
        "Q1_Price": round(ticker_data.loc[0, "Open"], 2)
    }
    
    # Process only the available data points
    for i in range(1, len(ticker_data)):
        prev_price = ticker_data.loc[i-1, "Open"]
        next_price = ticker_data.loc[i, "Open"]
        
        # Calculate changes
        change = round(next_price - prev_price, 2)
        percent_change = round((change / prev_price) * 100, 2)
        
        row_data[f"Q{i}_Price"] = round(next_price, 2)
        row_data[f"Percent_Change"] = percent_change
    
    performance_data.append(row_data)

# Convert results to DataFrame
performance_df = pd.DataFrame(performance_data)

# Display result
print(performance_df.head())

weights_dict = extract_weights_from_csv('../sp500_companies.csv')
result_with_weights = add_weights_to_ranked_list(performance_df, weights_dict)
# result_with_weights = result_with_weights.sort_values('Percent_Change')

# Save to CSV
result_with_weights.to_csv('performance_output.csv', index=False)