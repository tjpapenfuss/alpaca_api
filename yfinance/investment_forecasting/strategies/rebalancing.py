import pandas as pd

def check_and_rebalance(portfolio, prices, investment_date, closest_trading_date, start_date, 
    transactions, rebalance_threshold, rebalance_frequency, last_rebalance_date, sold_tickers=None):
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
    if not portfolio['holdings']:
        print("No holdings to rebalance.")
        return
        
    # Check if it's time to rebalance based on frequency
    should_rebalance_time = False
    current_date = pd.to_datetime(investment_date)
    
    if last_rebalance_date is None:
        # First rebalance should be at least 3 months after start
        first_date = pd.to_datetime(start_date)
        if (current_date - first_date).days >= 90:  # At least 90 days after start
            should_rebalance_time = True
    else:
        last_rebalance = pd.to_datetime(last_rebalance_date)
        if rebalance_frequency == 'monthly':
            should_rebalance_time = (current_date.year > last_rebalance.year or 
                                    (current_date.year == last_rebalance.year and 
                                    current_date.month > last_rebalance.month))
        elif rebalance_frequency == 'quarterly':
            curr_quarter = (current_date.month - 1) // 3 + 1
            last_quarter = (last_rebalance.month - 1) // 3 + 1
            should_rebalance_time = (current_date.year > last_rebalance.year or 
                                    (current_date.year == last_rebalance.year and 
                                    curr_quarter > last_quarter))
        elif rebalance_frequency == 'yearly':
            should_rebalance_time = current_date.year > last_rebalance.year
            
    # If not time to rebalance, check drift threshold
    if not should_rebalance_time:
        # Calculate current allocation vs target allocation
        # Here we use closest trading date to make sure we are getting a date where stocks were traded. 
        date_prices = prices.loc[closest_trading_date]
        total_value = calculate_portfolio_value(portfolio, prices, closest_trading_date)
        current_allocation = {}
        
        for ticker, holding in portfolio['holdings'].items():
            if ticker in date_prices and not pd.isna(date_prices[ticker]) and holding['shares'] > 0:
                current_value = holding['shares'] * date_prices[ticker]
                current_allocation[ticker] = current_value / total_value * 100
        
        # Get target allocation
        target_allocation = self.calculate_allocation_weights()
        target_allocation = {k: v * 100 for k, v in target_allocation.items()}
        
        # Calculate maximum drift
        max_drift = 0
        for ticker, target_pct in target_allocation.items():
            if ticker in current_allocation:
                drift = abs(current_allocation[ticker] - target_pct)
                max_drift = max(max_drift, drift)
        
        should_rebalance_drift = max_drift > self.rebalance_threshold
    else:
        should_rebalance_drift = False
        
    # Perform rebalancing if needed
    if should_rebalance_time or should_rebalance_drift:
        self._perform_rebalance(portfolio, prices, date, transactions, sold_tickers)
        self.last_rebalance_date = date
        
def _perform_rebalance(self, portfolio, prices, date, transactions, excluded_tickers):
    """
    Rebalance the portfolio to match target allocation weights.
    Will sell overweight positions and buy underweight positions.
    """
    date_prices = prices.loc[date]
    total_value = self._calculate_portfolio_value(portfolio, prices, date)
    target_allocation = self.calculate_allocation_weights()
    
    # First, calculate current allocation and target values
    current_values = {}
    target_values = {}
    
    for ticker, holding in portfolio['holdings'].items():
        if ticker in date_prices and not pd.isna(date_prices[ticker]):
            current_values[ticker] = holding['shares'] * date_prices[ticker]
    
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
            # Completely sell positions that are no longer in target allocation
            self._sell_position(portfolio, ticker, portfolio['holdings'][ticker]['shares'], 
                            date_prices[ticker], date, transactions, "Rebalancing - Sell")
        elif current_value > target_values[ticker] * 1.02:  # Allow 2% buffer to reduce unnecessary trading
            # Sell partial position to reach target
            shares_to_sell = (current_value - target_values[ticker]) / date_prices[ticker]
            shares_to_sell = round(shares_to_sell, 2)  # Round to 2 decimal places for fractional shares
            
            if shares_to_sell > 0.01:  # Only sell if it's at least 0.01 shares
                self._sell_position(portfolio, ticker, shares_to_sell, 
                                date_prices[ticker], date, transactions, "Rebalancing - Trim")
    
    # Now buy underweight positions with available cash
    if portfolio['cash'] > 10:  # Only rebalance if we have at least $10 cash
        for ticker, target_value in target_values.items():
            current_value = current_values.get(ticker, 0)
            
            if ticker in excluded_tickers:
                continue  # Skip recently sold tickers
                
            if ticker in date_prices and not pd.isna(date_prices[ticker]):
                if current_value < target_value * 0.98:  # Allow 2% buffer
                    # Buy to reach target
                    amount_to_buy = min(target_value - current_value, portfolio['cash'])
                    shares_to_buy = amount_to_buy / date_prices[ticker]
                    shares_to_buy = round(shares_to_buy, 2)  # Round to 2 decimal places
                    
                    if shares_to_buy >= 0.01 and amount_to_buy > 10:  # Minimum purchase
                        self._buy_position(portfolio, ticker, shares_to_buy, 
                                        date_prices[ticker], date, transactions, "Rebalancing - Add")

def _sell_position(self, portfolio, ticker, shares_to_sell, price, date, transactions, description):
    """Helper method to sell a position and record the transaction."""
    # Handle fractional shares by selling from most recent investments first
    remaining_to_sell = shares_to_sell
    realized_gain_loss = 0
    average_cost = 0
    total_cost = 0
    days_held_weighted = 0
    
    # Find non-sold investments for this ticker
    active_investments = [inv for inv in portfolio['holdings'][ticker]['investments'] if not inv['sold']]
    
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
        portfolio['holdings'][ticker]['shares'] -= actual_shares_sold
        portfolio['cash'] += sale_proceeds
        
        # Calculate percentage gain/loss
        if total_cost > 0:
            gain_loss_pct = (realized_gain_loss / total_cost) * 100
        else:
            gain_loss_pct = 0
        
        # Use weighted average days held or default to 0
        avg_days_held = round(days_held_weighted) if days_held_weighted > 0 else 0
        
        # Record transaction
        transactions.append({
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
        })

def _buy_position(self, portfolio, ticker, shares_to_buy, price, date, transactions, description):
    """Helper method to buy a position and record the transaction."""
    actual_investment = shares_to_buy * price
    
    # Check if we have enough cash
    if actual_investment > portfolio['cash']:
        shares_to_buy = portfolio['cash'] / price
        shares_to_buy = round(shares_to_buy, 2)
        actual_investment = shares_to_buy * price
    
    if shares_to_buy > 0:
        # Initialize holdings for this ticker if it doesn't exist
        if ticker not in portfolio['holdings']:
            portfolio['holdings'][ticker] = {
                'shares': 0,
                'investments': [],
                'cost_basis': 0
            }
            
        # Update portfolio
        portfolio['holdings'][ticker]['shares'] += shares_to_buy
        
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
        portfolio['holdings'][ticker]['investments'].append(purchase_record)
        
        # Update average cost basis
        total_shares = portfolio['holdings'][ticker]['shares']
        current_basis = portfolio['holdings'][ticker]['cost_basis']
        new_basis = (current_basis * (total_shares - shares_to_buy) + actual_investment) / total_shares
        portfolio['holdings'][ticker]['cost_basis'] = new_basis
        
        # Update cash and record transaction
        portfolio['cash'] -= actual_investment
        transactions.append({
            'date': date,
            'type': 'buy',
            'ticker': ticker,
            'shares': shares_to_buy,
            'price': price,
            'amount': actual_investment,
            'description': description
        })