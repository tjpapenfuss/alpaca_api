import pandas as pd
import yfinance as yf
from pull_tickers import extract_top_tickers_from_csv
import math

# ---------------------------------------------------------------------------------------------------
# Gather the tickers from the s&p500 csv file.
# ---------------------------------------------------------------------------------------------------
tickers = extract_top_tickers_from_csv('../sp500_companies.csv', top_n=2)  # "AAPL NVDA"
tickers_list = tickers.split()  # Convert "AAPL NVDA" → ["AAPL", "NVDA"]
start_date = "2023-01-01"
end_date = "2024-01-02"
interval = "3mo"

# Use yahoo finance function to pull stock tickers
df = yf.download(tickers=tickers_list, start=start_date, end=end_date, interval=interval)

# First, let's get just the 'Open' price column
open_prices = df['Open']

# Create a new empty DataFrame that will hold our results
result_df = pd.DataFrame()

# Reshape data for easier processing
for ticker in open_prices.columns:
    temp_df = pd.DataFrame({
        'Date': open_prices.index,
        'Ticker': ticker,
        'Open': open_prices[ticker].values
    })
    result_df = pd.concat([result_df, temp_df])

# Sort and reset index
result_df = result_df.sort_values(['Ticker', 'Date']).reset_index(drop=True)

# ---------------------------------------------------------------------------------------------------
# Calculate month-over-month changes dynamically
# ---------------------------------------------------------------------------------------------------
performance_data = []

for ticker in result_df['Ticker'].unique():  # Iterate over unique tickers
    ticker_data = result_df[result_df['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)

    row_data = {
        "Ticker": ticker,
        "Start_Date": ticker_data.loc[0, "Date"],
        "Start_Price": ticker_data.loc[0, "Open"]
    }
    
    # Iterate over time periods and dynamically add columns
    for i in range(1, len(ticker_data)):  # Start from the second row
        prev_date = ticker_data.loc[i - 1, "Date"]
        prev_price = ticker_data.loc[i - 1, "Open"]
        next_date = ticker_data.loc[i, "Date"]
        next_price = ticker_data.loc[i, "Open"]
        change = math.floor((next_price - prev_price)*100) / 100
        percent_change = (change / prev_price) * 100 if prev_price else None

        # Dynamically add columns
        row_data[f"Next_Date_{i}"] = next_date
        row_data[f"Next_Price_{i}"] = next_price
        row_data[f"Change_{i}"] = change
        row_data[f"Percent_Change_{i}"] = percent_change

    performance_data.append(row_data)

# Convert results to DataFrame
performance_df = pd.DataFrame(performance_data)

# Display result
print(performance_df)

# Save to CSV
performance_df.to_csv('performance_output.csv', index=False)
