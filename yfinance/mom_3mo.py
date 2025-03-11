import pandas as pd
import yfinance as yf
from pull_tickers import extract_weights_from_csv, add_weights_to_ranked_list, extract_top_tickers_from_csv
from datetime import datetime

# ---------------------------------------------------------------------------------------------------
# Configuration - Toggle between monthly and quarterly analysis
# ---------------------------------------------------------------------------------------------------
analysis_mode = "monthly"  # Set to "monthly" or "quarterly" to toggle between modes
portfolio_value = 1000000
trigger_threshold = -10  # Sell trigger when rolling performance drops below this percentage
# ---------------------------------------------------------------------------------------------------
# Gather tickers from S&P 500 CSV
# ---------------------------------------------------------------------------------------------------
tickers = extract_top_tickers_from_csv('../sp500_companies.csv', top_n=250)  
start_date = "2023-01-01"
end_date = "2024-01-02"

# ---------------------------------------------------------------------------------------------------
# Download stock data (batch download)
# ---------------------------------------------------------------------------------------------------
print(f"Downloading data for tickers: {len(tickers)} tickers")
# Always download monthly data, we'll filter later based on mode
raw_data = yf.download(tickers=tickers, start=start_date, end=end_date, interval="1mo", group_by='ticker')
print(raw_data)

# ---------------------------------------------------------------------------------------------------
# Identify failed tickers
# ---------------------------------------------------------------------------------------------------
failed_tickers = [ticker for ticker in tickers if ticker not in raw_data.columns.levels[0]]
valid_tickers = [ticker for ticker in tickers if ticker in raw_data.columns.levels[0]]

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
# Filter data based on analysis mode
# ---------------------------------------------------------------------------------------------------
if analysis_mode == "quarterly":
    # Filter for quarterly data (Jan, Apr, Jul, Oct)
    quarterly_months = [1, 4, 7, 10]  # Jan, Apr, Jul, Oct for quarterly data
    filtered_data = open_prices[open_prices.index.month.isin(quarterly_months)].copy()
    period_label = "Q"  # Label for quarters
    num_periods = 5  # Number of quarters to analyze
else:  # monthly mode
    # Use all monthly data points
    filtered_data = open_prices.copy()
    period_label = "M"  # Label for months
    num_periods = 12  # Number of months to analyze

# ---------------------------------------------------------------------------------------------------
# Prepare DataFrame with Stock Data
# ---------------------------------------------------------------------------------------------------
result_df = pd.DataFrame()

for ticker in valid_tickers:
    ticker_data = filtered_data[ticker].dropna()  # Drop NaN values for this ticker
    
    # Skip tickers with insufficient data
    if len(ticker_data) < 2:
        print(f"Skipping {ticker}: insufficient data points")
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
# Calculate period-over-period changes with rolling performance tracking
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
        f"{period_label}1_Price": round(ticker_data.loc[0, "Open"], 2)
    }
    
    # Track rolling performance and sell events
    rolling_performance = 0
    performance_periods = []
    sell_events = []
    
    # Process only the available data points
    for i in range(1, min(len(ticker_data), num_periods)):
        prev_price = ticker_data.loc[i-1, "Open"]
        next_price = ticker_data.loc[i, "Open"]
        
        # Calculate changes
        change = round(next_price - prev_price, 2)
        percent_change = round((change / prev_price) * 100, 2)
        
        # Add period price and changes to row data
        row_data[f"{period_label}{i}_Price"] = round(next_price, 2)
        row_data[f"{period_label}{i}_Percent_Change"] = percent_change
        
        # Update rolling performance
        rolling_performance += percent_change
        
        # Record performance for this period
        performance_periods.append({
            "period": i,
            "percent_change": percent_change,
            "rolling_performance": round(rolling_performance, 2)
        })
        
        # Check if we need to trigger a sell
        if rolling_performance <= trigger_threshold:
            sell_events.append({
                "period": i,
                "rolling_performance": round(rolling_performance, 2),
                "reset_value": round(rolling_performance, 2)  # Store how much we "lost" before reset
            })
            # Reset rolling performance after a sell
            rolling_performance = 0
    
    # Add rolling performance data to row
    row_data["Final_Rolling_Performance"] = round(rolling_performance, 2)
    row_data["Num_Sell_Events"] = len(sell_events)
    
    # Calculate total negative impact from sell events
    total_reset_value = sum(event["reset_value"] for event in sell_events)
    row_data["Total_Reset_Value"] = round(total_reset_value, 2)
    
    # Add to performance data
    performance_data.append(row_data)

# Convert results to DataFrame
performance_df = pd.DataFrame(performance_data)

# Display result
print(performance_df.head())

weights_dict = extract_weights_from_csv('../sp500_companies.csv')
result_with_weights = add_weights_to_ranked_list(performance_df, weights_dict)

# ---------------------------------------------------------------------------------------------------
# Calculate negative impact based on sell events
# ---------------------------------------------------------------------------------------------------

# Go through each stock's data to calculate negative impact
for index, row in result_with_weights.iterrows():
    ticker = row["Ticker"]
    weight = row["Portfolio_Weight"]
    weight = weights_dict.get(ticker, 0)  # Get weight from dictionary or default to 0
    
    # Get total reset value (sum of negative performance that triggered sells)
    if "Total_Reset_Value" in row and pd.notna(row["Total_Reset_Value"]):
        total_reset_value = row["Total_Reset_Value"]
        
        # Calculate impact: negative reset value * weight * portfolio value / 100
        negative_impact = (total_reset_value * weight * portfolio_value) / 100
        
        # Add the total negative impact to the dataframe
        performance_df.at[index, "Sell_Events_Impact"] = round(negative_impact, 2)
    else:
        performance_df.at[index, "Sell_Events_Impact"] = 0

# Add weights to the performance data
result_with_weights = add_weights_to_ranked_list(performance_df, weights_dict)

# ---------------------------------------------------------------------------------------------------
# Add detailed performance tracking to the results
# ---------------------------------------------------------------------------------------------------
for ticker in valid_tickers:
    ticker_data = result_df[result_df['Ticker'] == ticker].sort_values('Date').reset_index(drop=True)
    
    if len(ticker_data) < 2:
        continue
    
    rolling_perf = 0
    rolling_track = []
    
    for i in range(1, min(len(ticker_data), num_periods)):
        prev_price = ticker_data.loc[i-1, "Open"]
        next_price = ticker_data.loc[i, "Open"]
        
        percent_change = round(((next_price - prev_price) / prev_price) * 100, 2)
        rolling_perf += percent_change
        
        # Check for sell trigger
        if rolling_perf <= trigger_threshold:
            rolling_track.append(f"{period_label}{i}:{round(rolling_perf,2)}% [SELL]")
            rolling_perf = 0
        else:
            rolling_track.append(f"{period_label}{i}:{round(rolling_perf,2)}%")
    
    # Find the ticker's index in the result_with_weights DataFrame
    idx = result_with_weights.index[result_with_weights['Ticker'] == ticker].tolist()
    if idx:
        # Add rolling performance tracking as a string
        result_with_weights.at[idx[0], "Rolling_Performance_Track"] = " -> ".join(rolling_track)

# Save to CSV with mode in filename
output_filename = f'performance_output_{analysis_mode}_trigger{abs(trigger_threshold)}.csv'
result_with_weights.to_csv(output_filename, index=False)
print(f"Analysis completed in {analysis_mode} mode with {trigger_threshold}% trigger. Results saved to {output_filename}")