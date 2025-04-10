from models.portfolio import Portfolio
from utils.reporting import record_gains_losses
import pandas as pd

def buy_position(portfolio: Portfolio, ticker, shares_to_buy, price, date, transactions, description):
    """
    Buy shares of a ticker and record the transaction.
    
    Parameters:
    -----------
    ticker : str
        Ticker symbol
    shares_to_buy : float
        Number of shares to buy
    price : float
        Price per share
    date : str
        Date of purchase
    transactions : list
        List to record transactions
    description : str
        Description of the transaction
    """
    actual_investment = round(shares_to_buy * price, 2)
    
    # Check if we have enough cash
    if actual_investment > portfolio.cash:
        shares_to_buy = portfolio.cash / price
        actual_investment = round(shares_to_buy * price, 2)
    
    if shares_to_buy > 0:
        # Initialize holdings for this ticker if it doesn't exist
        if ticker not in portfolio.holdings:
            portfolio.holdings[ticker] = {
                'initial_shares_purchased': 0,
                'investments': [],
                'cost_basis': 0
            }

        # Update portfolio
        portfolio.holdings[ticker]['initial_shares_purchased'] += shares_to_buy
        portfolio.holdings[ticker]['shares_remaining'] += shares_to_buy
        
        # Track this specific investment separately
        purchase_record = {
            'date': date,
            'initial_shares_purchased': shares_to_buy,
            'shares_remaining': shares_to_buy,
            'price': price,
            'cost': actual_investment,
            'current_value': actual_investment,
            'return_pct': 0,
            'days_held': 0,
            'sold': False
        }
        portfolio.holdings[ticker]['investments'].append(purchase_record)
        
        # Update average cost basis
        total_shares = portfolio.holdings[ticker]['shares_remaining']
        current_basis = portfolio.holdings[ticker]['cost_basis']
        new_basis = (current_basis * (total_shares - shares_to_buy) + actual_investment) / total_shares
        portfolio.holdings[ticker]['cost_basis'] = new_basis
        
        # Update cash and record transaction
        portfolio.cash -= actual_investment
        transactions.append({
            'date': date,
            'type': 'buy',
            'ticker': ticker,
            'shares': shares_to_buy,
            'price': price, 
            'amount': actual_investment * -1, # Because this is a buy you deduct from your funds. 
            'description': description
        })
    return transactions
        
def sell_position(portfolio: Portfolio, ticker, shares_to_sell, price, date, transactions, description):
    """
    Sell shares of a ticker and record the transaction.
    
    Parameters:
    -----------
    ticker : str
        Ticker symbol
    shares_to_sell : float
        Number of shares to sell
    price : float
        Price per share
    date : str
        Date of sale
    transactions : list
        List to record transactions
    description : str
        Description of the transaction
    
    Returns:
    --------
    dict
        Transaction details including gain/loss
    """
    # Handle fractional shares by selling from most recent investments first
    remaining_to_sell = shares_to_sell
    realized_gain_loss = 0
    average_cost = 0
    total_cost = 0
    days_held_weighted = 0
    
    if ticker not in portfolio.holdings:
        print("FAILED. Ticker not in holdings.")
        return None
    
    # Find non-sold investments for this ticker
    active_investments = [inv for inv in portfolio.holdings[ticker]['investments'] if not inv['sold']]
    
    # Separate investments into loss and gain buckets
    loss_investments = [inv for inv in active_investments if inv['price'] > price]
    gain_investments = [inv for inv in active_investments if inv['price'] <= price]
    
    # Sort loss investments by highest loss first (purchase price descending)
    loss_investments.sort(key=lambda x: x['price'], reverse=True)
    
    # Sort gain investments by oldest first (date ascending)
    gain_investments.sort(key=lambda x: x['date'])
    
    # Combine lists: loss investments first, then gain investments
    selling_queue = loss_investments + gain_investments
    
    for investment in selling_queue:
        if remaining_to_sell <= 0:
            break
        #invest_shares = investment['shares']
        date_purchased = investment['date']
        if investment['shares_remaining'] <= remaining_to_sell:
            # Sell entire investment
            sold_shares = investment['shares_remaining']
            investment['sold'] = True
            remaining_to_sell -= sold_shares
            desc = f'Sell of {sold_shares} shares of {ticker} purchased on {date_purchased} for {description}'
        else:
            # Sell partial investment
            sold_shares = round(remaining_to_sell, 2)
            investment['shares_remaining'] = round(investment['shares_remaining'] - sold_shares, 4)
            if(investment['shares_remaining'] == 0):
                investment['sold'] = True
            remaining_to_sell = 0
            desc = f'Partial sell of {sold_shares} shares of {ticker} purchased on {date_purchased} for {description}'
            # desc = f'Partial sell of {sold_shares} shares of {ticker} purchased on {investment['date']} for {description}'
        
        # Calculate gain/loss for this lot
        lot_proceeds = round(sold_shares * price, 2)
        lot_cost = sold_shares * investment['price']
        lot_gain_loss = round(lot_proceeds - lot_cost, 2)
        transactions.append({
                'date': date,
                'type': 'sell',
                'ticker': ticker,
                'shares': sold_shares,
                'price': price,
                'amount': lot_proceeds,
                'gain_loss': lot_gain_loss,
                'gain_loss_pct': investment['return_pct'],
                'days_held': investment['days_held'],
                'description': desc
            })
        # Keep records of my gains and losses.
        record_gains_losses(lot_gain_loss, investment['days_held'], portfolio)
        
        realized_gain_loss += lot_gain_loss
        total_cost += lot_cost
        
        # Track weighted days held for reporting
        if 'days_held' in investment:
            days_held_weighted += investment['days_held'] * (sold_shares / shares_to_sell)
        
        if sold_shares > 0:
            portfolio.cash += lot_proceeds
    
    # Update portfolio holdings
    actual_shares_sold = shares_to_sell - remaining_to_sell
    # sale_proceeds = actual_shares_sold * price
    
    if actual_shares_sold > 0:
        portfolio.holdings[ticker]['shares_remaining'] -= actual_shares_sold
        # portfolio.cash += sale_proceeds
        return transactions
        
    return None

def update_positions(portfolio: Portfolio, prices, date):
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
            if investment['shares_remaining'] == 0:
                print(f"There are no shares remaining of investment: {investment}")
                continue
            current_date = pd.to_datetime(date)
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
