#from .data_loader import extract_weights_from_csv
#from models.portfolio import Portfolio
import math
import pandas as pd

from models.portfolio import Portfolio
from utils.transaction import buy_position

def calculate_allocation_weights(portfolio: Portfolio):
    """Calculate allocation weights for the portfolio."""
    if portfolio.portfolio_allocation == 'equal':
        # Equal weight allocation
        weight = 1.0 / len(portfolio.tickers)
        return {ticker: weight for ticker in portfolio.tickers}
    elif isinstance(portfolio.portfolio_allocation, dict):
        # User-provided weights
        adjusted_weights = portfolio.portfolio_allocation.copy()
        
        # Normalize remaining weights to sum to 1
        weight_sum = sum(adjusted_weights.values())
        if weight_sum > 0:  # Avoid division by zero
            adjusted_weights = {k: float(f"{(v/weight_sum):.4f}") for k, v in adjusted_weights.items()}
        return adjusted_weights
    else:
        print("ERRRROOOORRRR YOU CANNOT DO THIS. ")


def invest_available_cash(portfolio: Portfolio, allocation_weights, prices, date, transactions, excluded_tickers=None):
    """
    Invest available cash according to target allocation weights.
    
    Parameters:
    -----------
    allocation_weights : dict
        Dictionary mapping tickers to target weight
    prices : DataFrame
        DataFrame of price data
    date : str
        Date to use for prices
    transactions : list
        List to record transactions
    excluded_tickers : list, optional
        Tickers to exclude from purchase (e.g., recently sold)
    """
    if excluded_tickers is None:
        excluded_tickers = []

    date_prices = prices.loc[date]
    available_cash = portfolio.cash
    
    # Skip if no available cash
    if available_cash <= 0:
        return transactions
            
    # Adjust allocation weights to exclude tickers that were just sold
    adjusted_weights = allocation_weights.copy()
    
    # Remove excluded tickers and normalize remaining weights
    if excluded_tickers:
        for ticker in excluded_tickers:
            if ticker in adjusted_weights:
                adjusted_weights.pop(ticker)
                    
    # Normalize remaining weights to sum to 1
    weight_sum = sum(adjusted_weights.values())
    if weight_sum > 0:  # Avoid division by zero
        adjusted_weights = {k: float(f"{(v/weight_sum):.4f}") for k, v in adjusted_weights.items()}
    # Calculate amount to invest in each ticker
    for ticker, weight in adjusted_weights.items():
        if ticker not in date_prices or pd.isna(date_prices[ticker]):
            continue
                
        # Calculate investment amount and number of shares. Truncate to two decimal places.
        investment_amount = math.floor(available_cash * weight * 100) / 100
        price = date_prices[ticker]
        shares_to_buy = investment_amount / price
        
        # Round to 2 decimal places for fractional shares
        shares_to_buy = math.floor(shares_to_buy * 100) / 100
        actual_investment = round(shares_to_buy * price, 2)
        
        # Only buy if at least 0.01 shares
        if shares_to_buy >= 0.01:
            # Call to buy position function
            buy_position(portfolio, ticker, shares_to_buy, price, date, transactions, f'Bought {shares_to_buy} shares of {ticker}')
            
    return transactions