from models.portfolio import Portfolio

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
    actual_investment = shares_to_buy * price
    
    # Check if we have enough cash
    if actual_investment > portfolio.cash:
        shares_to_buy = portfolio.cash / price
        shares_to_buy = round(shares_to_buy, 2)
        actual_investment = shares_to_buy * price
    
    if shares_to_buy > 0:
        # Initialize holdings for this ticker if it doesn't exist
        if ticker not in portfolio.holdings:
            portfolio.holdings[ticker] = {
                'shares': 0,
                'investments': [],
                'cost_basis': 0
            }
            
        # Update portfolio
        portfolio.holdings[ticker]['shares'] += shares_to_buy
        
        # Track this specific investment separately
        purchase_record = {
            'date': date,
            'shares': shares_to_buy,
            'price': price,
            'cost': actual_investment,
            'current_value': actual_investment,
            'return_pct': 0,
            'days_held': 0,
            'sold': False
        }
        portfolio.holdings[ticker]['investments'].append(purchase_record)
        
        # Update average cost basis
        total_shares = portfolio.holdings[ticker]['shares']
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
    
    # Sort by purchase date (most recent first to reduce short-term gains)
    active_investments.sort(key=lambda x: x['date'], reverse=True)
    
    for investment in active_investments:
        if remaining_to_sell <= 0:
            break
            
        if investment['shares'] <= remaining_to_sell:
            # Sell entire investment
            sold_shares = investment['shares']
            investment['sold'] = True
            remaining_to_sell -= sold_shares
        else:
            # Sell partial investment
            sold_shares = remaining_to_sell
            investment['shares'] -= sold_shares
            remaining_to_sell = 0
        
        # Calculate gain/loss for this lot
        lot_proceeds = sold_shares * price
        lot_cost = sold_shares * (investment['cost'] / investment['shares'])
        lot_gain_loss = lot_proceeds - lot_cost
        
        realized_gain_loss += lot_gain_loss
        total_cost += lot_cost
        
        # Track weighted days held for reporting
        if 'days_held' in investment:
            days_held_weighted += investment['days_held'] * (sold_shares / shares_to_sell)
    
    # Update portfolio holdings
    actual_shares_sold = shares_to_sell - remaining_to_sell
    sale_proceeds = actual_shares_sold * price
    
    if actual_shares_sold > 0:
        portfolio.holdings[ticker]['shares'] -= actual_shares_sold
        portfolio.cash += sale_proceeds
        
        # Calculate percentage gain/loss
        if total_cost > 0:
            gain_loss_pct = (realized_gain_loss / total_cost) * 100
        else:
            gain_loss_pct = 0
        
        # Use weighted average days held or default to 0
        avg_days_held = round(days_held_weighted) if days_held_weighted > 0 else 0
        
        # Record transaction
        transaction = {
            'date': date,
            'type': 'sell',
            'ticker': ticker,
            'shares': actual_shares_sold,
            'price': price,
            'amount': sale_proceeds,
            'gain_loss': realized_gain_loss,
            'gain_loss_pct': gain_loss_pct,
            'days_held': avg_days_held,
            'description': description
        }
        
        transactions.append(transaction)
        return transaction
        
    return None