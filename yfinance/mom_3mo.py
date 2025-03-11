import pandas as pd
import yfinance as yf
from pull_tickers import extract_top_tickers_from_csv

# ---------------------------------------------------------------------------------------------------
# Gather tickers from S&P 500 CSV
# ---------------------------------------------------------------------------------------------------
tickers = extract_top_tickers_from_csv('../sp500_companies.csv', top_n=250)  
tickers_list = tickers.split()  # Convert "AAPL NVDA BRK.B GEV" → ["AAPL", "NVDA", "BRK.B", "GEV"]
start_date = "2023-01-01"
end_date = "2024-01-02"
interval = "3mo"

# ---------------------------------------------------------------------------------------------------
# Download stock data (only once)
# ---------------------------------------------------------------------------------------------------
print(f"Downloading data for tickers: {tickers_list}")
raw_data = yf.download(tickers=tickers_list, start=start_date, end=end_date, interval=interval, group_by='ticker')

# ---------------------------------------------------------------------------------------------------
# Identify failed tickers
# ---------------------------------------------------------------------------------------------------
failed_tickers = [ticker for ticker in tickers_list if ticker not in raw_data.columns.levels[0]]
valid_tickers = [ticker for ticker in tickers_list if ticker in raw_data.columns.levels[0]]

# Print results
if failed_tickers:
    print(f"\n❌ Failed to download: {failed_tickers}\n")
print(f"✅ Processed valid tickers: {valid_tickers}\n")

# ---------------------------------------------------------------------------------------------------
# Extract Open Prices (Only for Valid Tickers)
# ---------------------------------------------------------------------------------------------------
if "Open" in raw_data.columns.levels[1]:  
    open_prices = raw_data.xs("Open", level=1, axis=1)  # Extract 'Open' price for valid tickers
else:
    print("Error: 'Open' column missing in data. Exiting.")
    exit()

# ---------------------------------------------------------------------------------------------------
# Prepare DataFrame with Stock Data
# ---------------------------------------------------------------------------------------------------
result_df = pd.DataFrame()

for ticker in valid_tickers:
    temp_df = pd.DataFrame({
        'Date': open_prices.index,
        'Ticker': ticker,
        'Open': open_prices[ticker].values.round(2)  # Round to 2 decimals
    })
    result_df = pd.concat([result_df, temp_df])

# Sort and reset index
result_df = result_df.sort_values(['Ticker', 'Date']).reset_index(drop=True)

# ---------------------------------------------------------------------------------------------------
# Calculate month-over-month changes dynamically
# ---------------------------------------------------------------------------------------------------
performance_data = []

for ticker in valid_tickers:  # Process only valid tickers
    ticker_data = result_df[result_df['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)

    row_data = {
        "Ticker": ticker,
        "Start_Date": ticker_data.loc[0, "Date"],
        "Start_Price": round(ticker_data.loc[0, "Open"], 2)
    }
    
    for i in range(1, len(ticker_data)):  # Iterate over time periods
        prev_date = ticker_data.loc[i - 1, "Date"]
        prev_price = ticker_data.loc[i - 1, "Open"]
        next_date = ticker_data.loc[i, "Date"]
        next_price = ticker_data.loc[i, "Open"]
        change = round(next_price - prev_price, 2)
        percent_change = round((change / prev_price) * 100, 2) if prev_price else None

        row_data[f"Next_Date_{i}"] = next_date
        row_data[f"Next_Price_{i}"] = round(next_price, 2)
        row_data[f"Change_{i}"] = change
        row_data[f"Percent_Change_{i}"] = percent_change

    performance_data.append(row_data)

# Convert results to DataFrame
performance_df = pd.DataFrame(performance_data)

# Display result
print(performance_df)

# Save to CSV
performance_df.to_csv('performance_output.csv', index=False)
