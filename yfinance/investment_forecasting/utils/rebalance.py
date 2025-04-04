import pandas as pd
from utils.allocation import calculate_allocation_weights
from utils.transaction import buy_position, sell_position

from models.portfolio import Portfolio
    
def perform_rebalance(portfolio: Portfolio, prices, date, transactions, excluded_tickers):
    """
    Rebalance the portfolio to match target allocation weights.
    Will sell overweight positions and buy underweight positions.
    """
    date_prices = prices.loc[date]
    total_value = portfolio.calculate_total_value(prices, date)
    target_allocation = calculate_allocation_weights(portfolio=portfolio)
    
    # First, calculate current allocation and target values
    current_values = {}
    target_values = {}
    
    for ticker, holding in portfolio.holdings.items():
        if ticker in date_prices and not pd.isna(date_prices[ticker]):
            current_values[ticker] = holding['shares_remaining'] * date_prices[ticker]
    
    # Adjust target allocation to exclude recently sold tickers (to avoid wash sales)
    adjusted_target = target_allocation.copy()
    for ticker in excluded_tickers:
        if ticker in adjusted_target:
            del adjusted_target[ticker]
            
    # Normalize the adjusted target allocation
    if adjusted_target:
        total_weight = sum(adjusted_target.values())
        adjusted_target = {k: v/total_weight for k, v in adjusted_target.items()}
    
    # Calculate target values based on adjusted allocation
    for ticker, weight in adjusted_target.items():
        target_values[ticker] = total_value * weight
    
    # Identify positions to sell (overweight)
    for ticker, current_value in current_values.items():
        if ticker not in target_values:
            if ticker not in excluded_tickers:
                # Completely sell positions that are no longer in target allocation
                sell_position(portfolio, ticker,portfolio.holdings[ticker]['shares_remaining'], 
                                date_prices[ticker], date, transactions, "Rebalancing - Sell")
        elif current_value > target_values[ticker] * 1.02:  # Allow 2% buffer to reduce unnecessary trading
            # Sell partial position to reach target
            shares_to_sell = (current_value - target_values[ticker]) / date_prices[ticker]
            shares_to_sell = round(shares_to_sell, 2)  # Round to 2 decimal places for fractional shares
            
            if shares_to_sell > 0.01:  # Only sell if it's at least 0.01 shares
                sell_position(portfolio, ticker, shares_to_sell, 
                                date_prices[ticker], date, transactions, "Rebalancing - Trim")
    
    # Now buy underweight positions with available cash
    if portfolio.cash > 10:  # Only rebalance if we have at least $10 cash
        for ticker, target_value in target_values.items():
            current_value = current_values.get(ticker, 0)
            
            if ticker in excluded_tickers:
                continue  # Skip recently sold tickers
                
            if ticker in date_prices and not pd.isna(date_prices[ticker]):
                if current_value < target_value * 0.98:  # Allow 2% buffer
                    # Buy to reach target
                    amount_to_buy = min(target_value - current_value, portfolio.cash)
                    shares_to_buy = amount_to_buy / date_prices[ticker]
                    shares_to_buy = round(shares_to_buy, 2)  # Round to 2 decimal places
                    
                    if shares_to_buy >= 0.01 and amount_to_buy > 10:  # Minimum purchase
                        buy_position(portfolio, ticker, shares_to_buy, 
                                        date_prices[ticker], date, transactions, "Rebalancing - Add")

def check_and_rebalance(portfolio: Portfolio, prices, investment_date, closest_trading_date, start_date, 
    transactions, sold_tickers=None):
    """
    Check if portfolio needs rebalancing and perform rebalancing if necessary.
    
    Args:
        portfolio: Current portfolio state
        prices: DataFrame of prices
        date: Current date
        transactions: List to record transactions
        sold_tickers: List of tickers that were recently sold (to avoid wash sales)
    """
    if sold_tickers is None:
        sold_tickers = []
    
    # Skip if no holdings or not enough history
    if not portfolio.holdings:
        print("No holdings to rebalance.")
        return
        
    # Check if it's time to rebalance based on frequency
    should_rebalance_time = False
    current_date = pd.to_datetime(investment_date)
    
    last_rebalance = pd.to_datetime(portfolio.last_rebalance_date)
    if portfolio.rebalance_frequency == 'monthly':
        should_rebalance_time = (current_date.year > last_rebalance.year or 
                                (current_date.year == last_rebalance.year and 
                                current_date.month > last_rebalance.month))
    elif portfolio.rebalance_frequency == 'quarterly':
        curr_quarter = (current_date.month - 1) // 3 + 1
        last_quarter = (last_rebalance.month - 1) // 3 + 1
        should_rebalance_time = (current_date.year > last_rebalance.year or 
                                (current_date.year == last_rebalance.year and 
                                curr_quarter > last_quarter))
    elif portfolio.rebalance_frequency == 'yearly':
        should_rebalance_time = current_date.year > last_rebalance.year
            
    # If not time to rebalance, check drift threshold
    if not should_rebalance_time:
        # Calculate current allocation vs target allocation
        # Here we use closest trading date to make sure we are getting a date where stocks were traded. 
        date_prices = prices.loc[closest_trading_date]
        total_value = portfolio.calculate_total_value(prices, closest_trading_date)
        current_allocation = {}
        
        for ticker, holding in portfolio.holdings.items():
            if ticker in date_prices and not pd.isna(date_prices[ticker]) and holding['shares_remaining'] > 0:
                current_value = holding['shares_remaining'] * date_prices[ticker]
                current_allocation[ticker] = current_value / total_value * 100
        
        # Get target allocation
        target_allocation = calculate_allocation_weights(portfolio=portfolio)
        target_allocation = {k: v * 100 for k, v in target_allocation.items()}
        
        # Calculate maximum drift
        max_drift = 0
        for ticker, target_pct in target_allocation.items():
            if ticker in current_allocation:
                drift = abs(current_allocation[ticker] - target_pct)
                max_drift = max(max_drift, drift)
        
        should_rebalance_drift = max_drift > portfolio.rebalance_threshold
    else:
        should_rebalance_drift = False
        
    # Perform rebalancing if needed
    if should_rebalance_time or should_rebalance_drift:
        perform_rebalance(portfolio, prices, closest_trading_date, transactions, sold_tickers)
        portfolio.last_rebalance_date = closest_trading_date