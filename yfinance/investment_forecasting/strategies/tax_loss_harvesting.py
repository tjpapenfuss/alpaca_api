import pandas as pd

# Import the Porftolio Model
from models.portfolio import Portfolio
from utils.reporting import record_gains_losses

def track_and_manage_positions(portfolio: Portfolio, prices, date, transactions, sell_trigger):
    """
    Track position performance and trigger sells based on loss threshold.
    This implements the tax-loss harvesting strategy.
    
    Returns:
        list: Tickers that were sold for tax-loss harvesting
    """
    date_prices = prices.loc[date]
    sold_tickers = []
    current_date = pd.to_datetime(date)
    
    for ticker, holding in portfolio.holdings.items():
        if ticker not in date_prices or pd.isna(date_prices[ticker]):
            continue
            
        current_price = date_prices[ticker]
        ticker_sold = False
        
        # Update each investment's current value and return
        for investment in holding['investments']:
            if investment['sold']:
                continue
                
            # Calculate actual days held based on current date
            purchase_date = pd.to_datetime(investment['date'])
            
            # Update days held correctly - calculate the actual days passed
            investment['days_held'] = (current_date - purchase_date).days
            # Don't need prev value just the investment cost
            # previous_value = investment['current_value'] 
            current_value = round(investment['shares_remaining'] * current_price, 2)
            investment['current_value'] = current_value
            # Because we might have sold some shares for a specific lot, we must get the prorated 
            # cost for a particular investment. Ex. Initially purchased 20 shares at $10. I sold 
            # 10 shares. New price is $12/share. My current value is $120. My return percentage is
            # $120 / ($200 * (10/20)) => $120/$100 => 120%
            investment_cost_prorated = investment['cost'] * \
                (investment['shares_remaining'] / investment['initial_shares_purchased'])
            investment['return_pct'] = round(((current_value / investment_cost_prorated) - 1) * 100, 2)
            # Check if this specific investment meets the sell trigger
            if investment['return_pct'] <= sell_trigger:
                # Sell this specific lot
                investment['sold'] = True
                
                # Update portfolio
                holding['shares_remaining'] = round(holding['shares_remaining'] - investment['shares_remaining'], 4)
                sale_proceeds = round(investment['shares_remaining'] * current_price, 2)
                portfolio.cash += sale_proceeds
                
                # Calculate loss for reporting
                realized_loss = sale_proceeds - investment_cost_prorated

                # Keep records of my gains and losses.
                record_gains_losses(realized_loss, investment['days_held'], portfolio)

                # Record transaction
                transactions.append({
                    'date': date,
                    'type': 'sell',
                    'ticker': ticker,
                    'shares': investment['shares_remaining'],
                    'price': current_price,
                    'amount': sale_proceeds,
                    'gain_loss': realized_loss,
                    'gain_loss_pct': investment['return_pct'],
                    'days_held': investment['days_held'],
                    'description': f'Sold {investment["shares_remaining"]} shares of {ticker} for tax-loss harvesting'
                })
                ticker_sold = True
        
        if ticker_sold:
            sold_tickers.append(ticker)
    
    return transactions, sold_tickers

def get_tax_loss_harvesting_summary(transactions):
    """
    Generate a summary of tax-loss harvesting transactions.
    """
    # Implementation...