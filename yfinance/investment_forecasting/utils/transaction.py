from models.portfolio import Portfolio
from utils.reporting import record_gains_losses

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
        shares_to_buy = round(shares_to_buy, 2)
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
            'amount': actual_investment,
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
        if investment['shares_remaining'] <= remaining_to_sell:
            # Sell entire investment
            sold_shares = investment['shares_remaining']
            investment['sold'] = True
            remaining_to_sell -= sold_shares
            desc = f'Sell of {sold_shares} shares of {ticker} purchased on __Insert Later__ for {description}'
        else:
            # Sell partial investment
            sold_shares = remaining_to_sell
            investment['shares_remaining'] = round(investment['shares_remaining'] - sold_shares, 4) 
            remaining_to_sell = 0
            desc = f'Partial sell of {sold_shares} shares of {ticker} purchased on __Insert Later__ for {description}'
            # desc = f'Partial sell of {sold_shares} shares of {ticker} purchased on {investment['date']} for {description}'
        
        # Calculate gain/loss for this lot
        lot_proceeds = round(sold_shares * price, 2)
        lot_cost = round(sold_shares * investment['price'], 2)
        lot_gain_loss = lot_proceeds - lot_cost
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
    
    # Update portfolio holdings
    actual_shares_sold = shares_to_sell - remaining_to_sell
    sale_proceeds = actual_shares_sold * price
    
    if actual_shares_sold > 0:
        portfolio.holdings[ticker]['shares_remaining'] -= actual_shares_sold
        portfolio.cash += sale_proceeds
        # # Calculate percentage gain/loss
        # if total_cost > 0:
        #     gain_loss_pct = (realized_gain_loss / total_cost) * 100
        # else:
        #     gain_loss_pct = 0
        
        # # Use weighted average days held or default to 0
        # avg_days_held = round(days_held_weighted) if days_held_weighted > 0 else 0
        
        # # Record transaction
        # transaction = {
        #     'date': date,
        #     'type': 'sell',
        #     'ticker': ticker,
        #     'shares': actual_shares_sold,
        #     'price': price,
        #     'amount': sale_proceeds,
        #     'gain_loss': realized_gain_loss,
        #     'gain_loss_pct': gain_loss_pct,
        #     'days_held': avg_days_held,
        #     'description': description
        # }
        
        # transactions.append(transaction)
        return transactions
        
    return None