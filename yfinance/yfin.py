import yfinance as yf
import pandas as pd

# dat = yf.Ticker("APPL")
df = yf.download(tickers="AAPL GOOG LUMN", start="2023-01-01", end="2024-01-02", interval="3mo")
#data.to_csv(path_or_buf="Apple_Google.csv")

# df = pd.read_csv("Apple_Google.csv")

# First, let's get just the 'Open' price column
open_prices = df['Open']

# Create a new empty DataFrame that will hold our results
result_df = pd.DataFrame()

# For each ticker in the 'Open' column
for ticker in open_prices.columns:
    # Create a temporary DataFrame with the date index
    temp_df = pd.DataFrame({
        'Date': open_prices.index,  # Use the original index which contains dates
        'Ticker': ticker,
        'Open': open_prices[ticker].values
    })
    result_df = pd.concat([result_df, temp_df])

# Sort and reset index
result_df = result_df.sort_values(['Date', 'Ticker']).reset_index(drop=True)

# Display the result
print(result_df)

# ---------------------------------------------------------------------------------------------------
# Find the worst performers and best performers.
# ---------------------------------------------------------------------------------------------------
# Convert Date to datetime format
result_df['Date'] = pd.to_datetime(result_df['Date'])

# Calculate year-over-year changes for each ticker
# First, get the first and last date for each ticker
first_dates = result_df.groupby('Ticker')['Date'].min().reset_index()
last_dates = result_df.groupby('Ticker')['Date'].max().reset_index()

# Get the price values for the first and last dates
first_values = pd.merge(first_dates, result_df, on=['Ticker', 'Date'])
last_values = pd.merge(last_dates, result_df, on=['Ticker', 'Date'])

# Calculate the percentage change
result = pd.DataFrame({
    'Ticker': first_values['Ticker'],
    'Start_Date': first_values['Date'],
    'Start_Price': first_values['Open'],
    'End_Date': last_values['Date'],
    'End_Price': last_values['Open'],
    'Change': (last_values['Open'] - first_values['Open']),
    'Percent_Change': ((last_values['Open'] - first_values['Open']) / first_values['Open'] * 100)
})

# Sort by percentage change to easily see which went down the most
result = result.sort_values('Percent_Change')
print(result)
# Filter for tickers that went down
down_tickers = result[result['Change'] < 0]

print("Tickers that went down over the time period:")
print(down_tickers)

print("\nTickers that went up over the time period:")
print(result[result['Change'] > 0])