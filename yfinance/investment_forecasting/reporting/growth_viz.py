import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from models.investment_model import InvestmentForecastingModel
from datetime import datetime

def plot_results(top_n_df, spy_df):

    # Create the plot
    plt.figure(figsize=(12, 6))

    # Plot total value
    plt.plot(
        top_n_df['date'], 
        top_n_df['total_value'],
        label='Total Portfolio Value'
    )

    # Plot S&P 500 equivalent. 
    plt.plot(
        spy_df['date'],
        spy_df['total_value'],
        label='S&P 500 (SPY) Equivalent',
        color='green',
        linestyle='-.',
        linewidth=2
    )

    plt.title('Portfolio Growth vs S&P 500')
    plt.xlabel('Date')
    plt.ylabel('Value ($)')
    plt.grid(True, alpha=0.3)
    plt.legend()

    plt.tight_layout()
    plt.show()

    # Calculate performance metrics SPY
    print("Portfolio Performance Summary:")
    print(f"Total Initial Value: ${spy_df['total_value'].iloc[0]:,.2f}")
    print(f"Total Final Value: ${spy_df['total_value'].iloc[-1]:,.2f}")
    print(f"Total Return: {(spy_df['total_value'].iloc[-1] / spy_df['total_value'].iloc[0] - 1) * 100:.2f}%")
