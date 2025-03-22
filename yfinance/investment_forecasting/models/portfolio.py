import pandas as pd
import numpy as np
from utils.data_loader import extract_weights_from_csv
import math

class Portfolio:
    def __init__(self, rebalance_frequency, rebalance_threshold, portfolio_allocation, tickers):
        """
        Initialize a portfolio with a list of tickers.
        
        Parameters:
        -----------
        tickers : list
            List of ticker symbols
        """
        self.cash = 0
        self.rebalance_frequency = rebalance_frequency
        self.rebalance_threshold = rebalance_threshold
        self.portfolio_allocation = portfolio_allocation
        self.last_rebalance_date = None
        self.holdings = {}
        self.tickers = tickers
        self.portfolio_history = []
        
    def initialize_holdings(self, tickers):
        self.holdings = {ticker: {'shares': 0, 'cost_basis': 0, 'investments': []} 
                         for ticker in tickers}

    def add_cash(self, amount):
        """Add cash to the portfolio."""
        self.cash += amount
        return self.cash
    
    def calculate_total_value(self, prices_df, date):
        """Calculate total portfolio value including cash and holdings."""
        date_prices = prices_df.loc[date]
        
        holdings_value = 0
        for ticker, holding in self.holdings.items():
            if ticker in date_prices and not pd.isna(date_prices[ticker]):
                holdings_value += holding['shares'] * date_prices[ticker]
        
        return self.cash + holdings_value
    
    def update_portfolio_history(self, prices, closest_date):
        portfolio_value = self.calculate_total_value(prices, closest_date)
        self.portfolio_history.append({
                'date': closest_date,
                'cash': self.cash,
                'investments_value': portfolio_value - self.cash,
                'total_value': portfolio_value
            })
        return self.portfolio_history

    def get_portfolio_history(self):
        return self.portfolio_history

    def get_portfolio_holdings(self):
        return self.holdings

    def calculate_allocation_weights(self):
        """Calculate allocation weights for the portfolio."""
        if self.portfolio_allocation == 'equal':
            # Equal weight allocation
            weight = 1.0 / len(self.tickers)
            return {ticker: weight for ticker in self.tickers}
        elif isinstance(self.portfolio_allocation, dict):
            # User-provided weights
            adjusted_weights = self.portfolio_allocation.copy()
                                
            # Normalize remaining weights to sum to 1
            weight_sum = sum(adjusted_weights.values())
            if weight_sum > 0:  # Avoid division by zero
                adjusted_weights = {k: float(f"{(v/weight_sum):.4f}") for k, v in adjusted_weights.items()}
            return adjusted_weights
        else:
            print("ERRRROOOORRRR YOU CANNOT DO THIS. ")
            #elif isinstance(self.portfolio_allocation, str) and self.portfolio_allocation.endswith('.csv'):
            # Load weights from CSV
            # try:
            #     weights_dict = extract_weights_from_csv(self.portfolio_allocation)
            #     # Filter for only our tickers and normalize
            #     filtered_weights = {t: weights_dict.get(t, 0) for t in self.tickers}
            #     total_weight = sum(filtered_weights.values())
            #     if total_weight > 0:
            #         return {t: w/total_weight for t, w in filtered_weights.items()}
            #     else:
            #         # Fall back to equal weight if no weights found
            #         weight = 1.0 / len(self.tickers)
            #         return {ticker: weight for ticker in self.tickers}
            # except Exception as e:
            #     print(f"Error loading weights from CSV: {e}")
            #     # Fall back to equal weight
            #     weight = 1.0 / len(self.tickers)
            #     return {ticker: weight for ticker in self.tickers}

    def invest_available_cash(self, allocation_weights, prices, date, transactions, excluded_tickers=None):
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
        available_cash = self.cash
        
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
            shares_to_buy = round(shares_to_buy, 2)
            actual_investment = shares_to_buy * price
            
            # Only buy if at least 0.01 shares
            if shares_to_buy >= 0.01:
                # Initialize holdings for this ticker if it doesn't exist
                if ticker not in self.holdings:
                    self.holdings[ticker] = {
                        'shares': 0,
                        'investments': [],
                        'cost_basis': 0
                    }
                
                # Update portfolio
                self.holdings[ticker]['shares'] += shares_to_buy
                
                # Track this specific investment separately for tax-loss harvesting
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
                self.holdings[ticker]['investments'].append(purchase_record)
                    
                # Update average cost basis
                total_shares = self.holdings[ticker]['shares']
                current_basis = self.holdings[ticker]['cost_basis']
                new_basis = (current_basis * (total_shares - shares_to_buy) + actual_investment) / total_shares
                self.holdings[ticker]['cost_basis'] = new_basis
                    
                # Update cash and record transaction
                self.cash -= actual_investment
                print(self.cash)
                transactions.append({
                    'date': date,
                    'type': 'buy',
                    'ticker': ticker,
                    'shares': shares_to_buy,
                    'price': price,
                    'amount': actual_investment,
                    'description': f'Bought {shares_to_buy} shares of {ticker}'
                })
        return transactions
    
    def buy_position(self, ticker, shares_to_buy, price, date, transactions, description):
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
        if actual_investment > self.cash:
            shares_to_buy = self.cash / price
            shares_to_buy = round(shares_to_buy, 2)
            actual_investment = shares_to_buy * price
        
        if shares_to_buy > 0:
            # Initialize holdings for this ticker if it doesn't exist
            if ticker not in self.holdings:
                self.holdings[ticker] = {
                    'shares': 0,
                    'investments': [],
                    'cost_basis': 0
                }
                
            # Update portfolio
            self.holdings[ticker]['shares'] += shares_to_buy
            
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
            self.holdings[ticker]['investments'].append(purchase_record)
            
            # Update average cost basis
            total_shares = self.holdings[ticker]['shares']
            current_basis = self.holdings[ticker]['cost_basis']
            new_basis = (current_basis * (total_shares - shares_to_buy) + actual_investment) / total_shares
            self.holdings[ticker]['cost_basis'] = new_basis
            
            # Update cash and record transaction
            self.cash -= actual_investment
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
            
    def sell_position(self, ticker, shares_to_sell, price, date, transactions, description):
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
        
        if ticker not in self.holdings:
            return None
            
        # Find non-sold investments for this ticker
        active_investments = [inv for inv in self.holdings[ticker]['investments'] if not inv['sold']]
        
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
            self.holdings[ticker]['shares'] -= actual_shares_sold
            self.cash += sale_proceeds
            
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

    def perform_rebalance(self, prices, date, transactions, excluded_tickers):
        """
        Rebalance the portfolio to match target allocation weights.
        Will sell overweight positions and buy underweight positions.
        """
        date_prices = prices.loc[date]
        total_value = self.calculate_total_value(prices, date)
        target_allocation = self.calculate_allocation_weights()
        
        # First, calculate current allocation and target values
        current_values = {}
        target_values = {}
        
        for ticker, holding in self.holdings.items():
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
                self.sell_position(ticker,self.holdings[ticker]['shares'], 
                                date_prices[ticker], date, transactions, "Rebalancing - Sell")
            elif current_value > target_values[ticker] * 1.02:  # Allow 2% buffer to reduce unnecessary trading
                # Sell partial position to reach target
                shares_to_sell = (current_value - target_values[ticker]) / date_prices[ticker]
                shares_to_sell = round(shares_to_sell, 2)  # Round to 2 decimal places for fractional shares
                
                if shares_to_sell > 0.01:  # Only sell if it's at least 0.01 shares
                    self.sell_position(ticker, shares_to_sell, 
                                    date_prices[ticker], date, transactions, "Rebalancing - Trim")
        
        # Now buy underweight positions with available cash
        if self.cash > 10:  # Only rebalance if we have at least $10 cash
            for ticker, target_value in target_values.items():
                current_value = current_values.get(ticker, 0)
                
                if ticker in excluded_tickers:
                    continue  # Skip recently sold tickers
                    
                if ticker in date_prices and not pd.isna(date_prices[ticker]):
                    if current_value < target_value * 0.98:  # Allow 2% buffer
                        # Buy to reach target
                        amount_to_buy = min(target_value - current_value, self.cash)
                        shares_to_buy = amount_to_buy / date_prices[ticker]
                        shares_to_buy = round(shares_to_buy, 2)  # Round to 2 decimal places
                        
                        if shares_to_buy >= 0.01 and amount_to_buy > 10:  # Minimum purchase
                            self.buy_position(ticker, shares_to_buy, 
                                            date_prices[ticker], date, transactions, "Rebalancing - Add")
                                            
    # Need to repurpose this and put this in the portfolio class as a rebalance portfolio method.
    def check_and_rebalance(self, prices, investment_date, closest_trading_date, start_date, 
        transactions, last_rebalance_date, sold_tickers=None):
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
        if not self.holdings:
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
            if self.rebalance_frequency == 'monthly':
                should_rebalance_time = (current_date.year > last_rebalance.year or 
                                        (current_date.year == last_rebalance.year and 
                                        current_date.month > last_rebalance.month))
            elif self.rebalance_frequency == 'quarterly':
                curr_quarter = (current_date.month - 1) // 3 + 1
                last_quarter = (last_rebalance.month - 1) // 3 + 1
                should_rebalance_time = (current_date.year > last_rebalance.year or 
                                        (current_date.year == last_rebalance.year and 
                                        curr_quarter > last_quarter))
            elif self.rebalance_frequency == 'yearly':
                should_rebalance_time = current_date.year > last_rebalance.year
                
        # If not time to rebalance, check drift threshold
        if not should_rebalance_time:
            # Calculate current allocation vs target allocation
            # Here we use closest trading date to make sure we are getting a date where stocks were traded. 
            date_prices = prices.loc[closest_trading_date]
            total_value = self.calculate_total_value(prices, closest_trading_date)
            current_allocation = {}
            
            for ticker, holding in self.holdings.items():
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
            self.perform_rebalance(prices, closest_trading_date, transactions, sold_tickers)
            self.last_rebalance_date = closest_trading_date

    def track_and_manage_positions(self, prices, date, transactions, sell_trigger):
        """
        Track position performance and trigger sells based on loss threshold.
        This implements the tax-loss harvesting strategy.
        
        Returns:
            list: Tickers that were sold for tax-loss harvesting
        """
        date_prices = prices.loc[date]
        sold_tickers = []
        current_date = pd.to_datetime(date)
        
        for ticker, holding in self.holdings.items():
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
                current_value = investment['shares'] * current_price
                investment['current_value'] = current_value
                investment['return_pct'] = ((current_value / investment['cost']) - 1) * 100
                # Check if this specific investment meets the sell trigger
                if investment['return_pct'] <= sell_trigger:
                    # Sell this specific lot
                    investment['sold'] = True
                    
                    # Update portfolio
                    holding['shares'] -= investment['shares']
                    sale_proceeds = investment['shares'] * current_price
                    self.cash += sale_proceeds
                    
                    # Calculate loss for reporting
                    realized_loss = sale_proceeds - investment['cost']
                    # Record transaction
                    transactions.append({
                        'date': date,
                        'type': 'sell',
                        'ticker': ticker,
                        'shares': investment['shares'],
                        'price': current_price,
                        'amount': sale_proceeds,
                        'gain_loss': realized_loss,
                        'gain_loss_pct': investment['return_pct'],
                        'days_held': investment['days_held'],
                        'description': f'Sold {investment["shares"]} shares of {ticker} for tax-loss harvesting'
                    })
                    ticker_sold = True
            
            if ticker_sold:
                sold_tickers.append(ticker)
        
        return transactions, sold_tickers