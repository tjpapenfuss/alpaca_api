import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Read the transaction data
def read_transactions(data):
    # df = pd.read_csv(pd.iotools.StringIO(data), parse_dates=['date'])
    df = pd.read_csv(data, parse_dates=['date'])
    return df

# Classify transactions and calculate gains/losses
def analyze_transactions(df):
    # Filter only sell transactions
    sells = df[df['type'] == 'sell'].copy()
    
    # Calculate gain/loss classification
    def classify_gain_loss(row):
        # Find the corresponding buy transaction(s)
        buy_rows = df[(df['type'] == 'buy') & 
                      (df['ticker'] == row['ticker']) & 
                      (df['date'] < row['date'])]
        
        # Calculate total cost basis
        total_cost = buy_rows['amount'].sum()
        total_shares_bought = buy_rows['shares'].sum()
        
        # Calculate proceeds
        proceeds = row['amount']
        shares_sold = row['shares']
        
        # Calculate average cost per share
        avg_cost_per_share = total_cost / total_shares_bought if total_shares_bought > 0 else 0
        #sale_price_per_share = proceeds / shares_sold
        
        # Calculate gain/loss
        gain_loss = proceeds - (shares_sold * avg_cost_per_share)
        
        # Classify as short-term or long-term based on holding period
        days_held = row['days_held']
        if days_held < 365 and gain_loss > 0:
            gain_loss_type = 'Short-term-gain'
        elif days_held < 365 and gain_loss < 0:
            gain_loss_type = 'Short-term-loss'
        elif days_held >= 365 and gain_loss > 0:
            gain_loss_type = 'Long-term-gain'
        else:
            gain_loss_type = 'Long-term-loss'
        #Start
        
        return pd.Series({
            'gain_loss': gain_loss, 
            'gain_loss_type': gain_loss_type,
            'days_held': days_held
        })
    
    # Apply gain/loss classification
    sells[['gain_loss', 'gain_loss_type', 'days_held']] = sells.apply(classify_gain_loss, axis=1)
    
    return sells

# Aggregate gains and losses by month
def aggregate_gains_losses(sells_analysis):
    # Convert date to month start
    sells_analysis['month'] = sells_analysis['date'].dt.to_period('M')
    
    # Group by month, gain/loss type, and +/-
    monthly_summary = sells_analysis.groupby(['month', 'gain_loss_type'])['gain_loss'].sum().unstack(fill_value=0)
    return monthly_summary

# Plot the gains and losses
def plot_gains_losses(monthly_summary):
    plt.figure(figsize=(15, 6))
    
    # Plot short-term gains
    plt.bar(monthly_summary.index.astype(str), 
            abs(monthly_summary['Short-term-gain']), 
            label='Short-term-gains', 
            color='red', 
            alpha=0.7)
    # Plot short-term Loss
    plt.bar(monthly_summary.index.astype(str), 
            abs(monthly_summary['Short-term-loss']), 
            bottom=monthly_summary['Short-term-gain'], 
            label='Short-term-losses', 
            color='Green', 
            alpha=0.7)
    # Plot long-term gains
    plt.bar(monthly_summary.index.astype(str), 
            abs(monthly_summary['Long-term-gain']), 
            bottom=monthly_summary['Short-term-loss'], 
            label='Long-term-gains', 
            color='Pink', 
            alpha=0.7)
    # Plot long-term Loss
    plt.bar(monthly_summary.index.astype(str), 
            abs(monthly_summary['Long-term-loss']), 
            bottom=monthly_summary['Long-term-gain'], 
            label='Long-term-losses', 
            color='Blue', 
            alpha=0.7)
    
    plt.title('Monthly Realized Gains and Losses')
    plt.xlabel('Month')
    plt.ylabel('Gain/Loss ($)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    
    return plt

# Main analysis function
def perform_analysis(data):
    # Read transactions
    df = read_transactions(data)
    
    # Analyze transactions
    sells_analysis = analyze_transactions(df)
    
    # Aggregate monthly gains and losses
    monthly_summary = aggregate_gains_losses(sells_analysis)
    
    # Plot gains and losses
    plt = plot_gains_losses(monthly_summary)
    
    return sells_analysis, monthly_summary, plt

GLOBAL_FOLDER_LOCATION = "/Users/tannerpapenfuss/finance_testing/alpaca_api/yfinance/investment_forecasting/"

# Perform the analysis
# with open(f'{GLOBAL_FOLDER_LOCATION}output/history.csv', 'r') as file:
#     data = file.read()

sells_analysis, monthly_summary, plt = perform_analysis(f'{GLOBAL_FOLDER_LOCATION}output/transactions.csv')

# Display summary
print("Monthly Gains and Losses Summary:")
print(monthly_summary)

plt.savefig('gains_losses_plot.png')
plt.close()
