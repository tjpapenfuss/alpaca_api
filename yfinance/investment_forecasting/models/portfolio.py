import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class Portfolio:
    def __init__(self, rebalance_frequency, rebalance_threshold, portfolio_allocation, last_rebalance_date, tickers, name="Default Portfolio"):
        """
        Initialize a portfolio with configuration settings and initial tickers.
        
        Parameters:
        -----------
        rebalance_frequency : str
            Frequency of portfolio rebalancing ('monthly', 'quarterly', 'yearly')
        rebalance_threshold : float
            Threshold (in percentage) that triggers rebalancing due to asset drift
        portfolio_allocation : dict or str
            Target allocation for the portfolio. Can be 'equal' or a dictionary with ticker:weight pairs
        tickers : list
            List of ticker symbols in the portfolio
        name : str, optional
            Name of the portfolio for identification purposes
        """
        # Basic portfolio properties
        self.name = name
        self.creation_date = datetime.now().strftime("%Y-%m-%d")
        self.cash = 0
        self.tickers = tickers
        
        # Rebalancing configuration
        self.rebalance_frequency = rebalance_frequency
        self.rebalance_threshold = rebalance_threshold
        self.portfolio_allocation = portfolio_allocation
        self.last_rebalance_date = last_rebalance_date
        
        # Storage for portfolio data
        self.holdings = {}
        self.portfolio_history = []
        self.transaction_history = []
        
        # Performance metrics
        self.initial_investment = 0
        self.total_deposits = 0
        self.total_withdrawals = 0
        self.long_term_realized_gains = 0
        self.short_term_realized_gains = 0
        self.long_term_realized_losses = 0
        self.short_term_realized_losses = 0
        self.tax_loss_harvesting_savings = 0
        
        # Risk metrics
        self.max_drawdown = 0
        self.volatility = 0
        
        # Initialize holdings structure
        self.initialize_holdings(tickers)
    
    def initialize_holdings(self, tickers):
        """
        Initialize the holdings dictionary with default values for each ticker.
        
        Parameters:
        -----------
        tickers : list
            List of ticker symbols to initialize in the portfolio
        """
        self.holdings = {ticker: 
            {
                'initial_shares_purchased': 0, 
                'shares_remaining': 0,
                'cost_basis': 0, 
                'investments': [], 
                'current_value': 0,
                'current_price': 0,
                'last_update_date': None,
                'unrealized_gain_loss': 0,
                'unrealized_gain_loss_pct': 0,
                'weight': 0,
                'dividend_income': 0,
                'sector': None,
                'asset_class': None
            } 
            for ticker in tickers
        }

    def add_cash(self, amount, transaction_date=None, description="Cash deposit"):
        """
        Add cash to the portfolio and record the transaction.
        
        Parameters:
        -----------
        amount : float
            Amount of cash to add (positive) or withdraw (negative)
        transaction_date : str, optional
            Date of the transaction. Defaults to current date
        description : str, optional
            Description of the transaction
            
        Returns:
        --------
        float
            Updated cash balance
        """
        if transaction_date is None:
            transaction_date = datetime.now().strftime("%Y-%m-%d")
            
        # Update cash balance
        self.cash += amount
        
        # Track deposits and withdrawals
        if amount > 0:
            self.total_deposits += amount
            transaction_type = "deposit"
        else:
            self.total_withdrawals += abs(amount)
            transaction_type = "withdrawal"
            
        # Record the transaction
        self.transaction_history.append({
            'date': transaction_date,
            'type': transaction_type,
            'amount': abs(amount),
            'description': description
        })
        
        return self.cash
    
    def calculate_total_value(self, prices_df, date):
        """
        Calculate total portfolio value including cash and holdings.
        Also updates current values in holdings.
        
        Parameters:
        -----------
        prices_df : pandas.DataFrame
            DataFrame of price data for all tickers
        date : str
            Date to use for prices
            
        Returns:
        --------
        float
            Total portfolio value (cash + holdings)
        """
        date_prices = prices_df.loc[date]
        total_holdings_value = 0
        
        # Update each holding's current value
        for ticker, holding in self.holdings.items():
            if ticker in date_prices and not pd.isna(date_prices[ticker]):
                price = date_prices[ticker]
                current_value = holding['shares_remaining'] * price
                
                # Update holding information
                holding['current_price'] = price
                holding['current_value'] = current_value
                holding['last_update_date'] = date
                
                # Calculate unrealized gain/loss
                if holding['cost_basis'] > 0 and holding['shares_remaining'] > 0:
                    holding['unrealized_gain_loss'] = current_value - (holding['cost_basis'] * holding['shares_remaining'])
                    holding['unrealized_gain_loss_pct'] = (holding['unrealized_gain_loss'] / 
                                                          (holding['cost_basis'] * holding['shares_remaining'])) * 100
                
                total_holdings_value += current_value
        
        # Calculate total portfolio value
        total_value = self.cash + total_holdings_value
        
        # Update holdings weights
        if total_value > 0:
            for ticker, holding in self.holdings.items():
                holding['weight'] = (holding['current_value'] / total_value) * 100
        
        return total_value
    
    def update_portfolio_history(self, prices, closest_date):
        """
        Update the portfolio history with current values and metrics.
        
        Parameters:
        -----------
        prices : pandas.DataFrame
            DataFrame of price data for all tickers
        closest_date : str
            Date to use for updating portfolio history
            
        Returns:
        --------
        list
            Updated portfolio history
        """
        portfolio_value = self.calculate_total_value(prices, closest_date)
        investments_value = portfolio_value - self.cash
        
        # Calculate additional metrics
        previous_value = self.portfolio_history[-1]['total_value'] if self.portfolio_history else 0
        daily_return = ((portfolio_value / previous_value) - 1) * 100 if previous_value > 0 else 0
        
        # Calculate running max drawdown
        if self.portfolio_history:
            peak_value = max([entry['total_value'] for entry in self.portfolio_history] + [portfolio_value])
            current_drawdown = ((portfolio_value / peak_value) - 1) * 100
            self.max_drawdown = min(self.max_drawdown, current_drawdown)
        
        gains_losses = self.long_term_realized_gains + self.short_term_realized_gains + \
                       self.long_term_realized_losses + self.short_term_realized_losses,
        # Append to history
        self.portfolio_history.append({
            'date': closest_date,
            'cash': self.cash,
            'investments_value': investments_value,
            'total_value': portfolio_value,
            'daily_return': daily_return,
            'cash_allocation': (self.cash / portfolio_value * 100) if portfolio_value > 0 else 0,
            'realized_gains_losses': gains_losses,
            'max_drawdown': self.max_drawdown
        })
        
        return self.portfolio_history
    
    def get_portfolio_history(self):
        """
        Return the complete portfolio history.
        
        Returns:
        --------
        list
            List of portfolio history entries
        """
        return self.portfolio_history
    
    def get_portfolio_holdings(self):
        """
        Return current portfolio holdings.
        
        Returns:
        --------
        dict
            Dictionary of current holdings
        """
        return self.holdings
    
    def get_asset_allocation(self):
        """
        Calculate current asset allocation percentages.
        
        Returns:
        --------
        dict
            Dictionary with asset classes and their allocation percentages
        """
        total_value = sum(holding['current_value'] for holding in self.holdings.values()) + self.cash
        
        # Group by asset class
        allocation = {'Cash': (self.cash / total_value * 100) if total_value > 0 else 0}
        
        for ticker, holding in self.holdings.items():
            asset_class = holding.get('asset_class', 'Unknown')
            if asset_class not in allocation:
                allocation[asset_class] = 0
            allocation[asset_class] += (holding['current_value'] / total_value * 100) if total_value > 0 else 0
            
        return allocation
    
    def get_sector_allocation(self):
        """
        Calculate current sector allocation percentages.
        
        Returns:
        --------
        dict
            Dictionary with sectors and their allocation percentages
        """
        total_value = sum(holding['current_value'] for holding in self.holdings.values())
        
        # Group by sector
        allocation = {}
        for ticker, holding in self.holdings.items():
            sector = holding.get('sector', 'Unknown')
            if sector not in allocation:
                allocation[sector] = 0
            allocation[sector] += (holding['current_value'] / total_value * 100) if total_value > 0 else 0
            
        return allocation
    
    def calculate_performance_metrics(self, end_date=None):
        """
        Calculate key performance metrics for the portfolio.
        
        Parameters:
        -----------
        end_date : str, optional
            End date for calculating metrics. Defaults to latest date in history
            
        Returns:
        --------
        dict
            Dictionary with various performance metrics
        """
        if not self.portfolio_history:
            return {
                'total_return': 0,
                'annualized_return': 0,
                'sharpe_ratio': 0,
                'volatility': 0,
                'max_drawdown': 0
            }
            
        # Determine date range
        start_history = self.portfolio_history[0]
        end_history = self.portfolio_history[-1] if end_date is None else next(
            (h for h in reversed(self.portfolio_history) if h['date'] <= end_date), 
            self.portfolio_history[-1]
        )
        
        start_date = start_history['date']
        end_date = end_history['date']
        
        # Extract daily returns
        returns = [entry['daily_return'] for entry in self.portfolio_history]
        
        # Calculate metrics
        total_return = ((end_history['total_value'] - self.total_deposits + self.total_withdrawals) / 
                        (self.total_deposits)) * 100 if self.total_deposits > 0 else 0
                        
        # Days between start and end
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        days = (end_dt - start_dt).days
        
        # Annualized return
        annualized_return = ((1 + total_return/100) ** (365/days) - 1) * 100 if days > 0 else 0
        
        # Volatility (annualized standard deviation of returns)
        volatility = np.std(returns) * np.sqrt(252) if returns else 0
        self.volatility = volatility
        
        # Sharpe ratio (assuming risk-free rate of 0 for simplicity)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'max_drawdown': self.max_drawdown,
            'long_term_realized_gains': self.long_term_realized_gains,
            'short_term_realized_gains': self.short_term_realized_gains,
            'short_term_realized_losses': self.short_term_realized_losses,
            'long_term_realized_losses': self.long_term_realized_losses,
            'tax_loss_harvesting_savings': self.tax_loss_harvesting_savings
        }
    
    def record_dividend(self, ticker, amount, date, description="Dividend payment"):
        """
        Record a dividend payment for a ticker.
        
        Parameters:
        -----------
        ticker : str
            Ticker symbol that paid the dividend
        amount : float
            Dividend amount
        date : str
            Date of the dividend payment
        description : str, optional
            Description of the dividend payment
        """
        if ticker in self.holdings:
            self.holdings[ticker]['dividend_income'] += amount
            self.cash += amount
            
            # Record transaction
            self.transaction_history.append({
                'date': date,
                'type': 'dividend',
                'ticker': ticker,
                'amount': amount,
                'description': description
            })
    
    def set_ticker_metadata(self, ticker, sector=None, asset_class=None):
        """
        Set metadata for a ticker in the portfolio.
        
        Parameters:
        -----------
        ticker : str
            Ticker symbol
        sector : str, optional
            Sector classification
        asset_class : str, optional
            Asset class (e.g., 'Equity', 'Bond', etc.)
        """
        if ticker in self.holdings:
            if sector:
                self.holdings[ticker]['sector'] = sector
            if asset_class:
                self.holdings[ticker]['asset_class'] = asset_class
    
    def get_transaction_history(self, transaction_type=None, start_date=None, end_date=None):
        """
        Get filtered transaction history.
        
        Parameters:
        -----------
        transaction_type : str, optional
            Filter by transaction type (buy, sell, deposit, withdrawal, dividend)
        start_date : str, optional
            Start date for filtering
        end_date : str, optional
            End date for filtering
            
        Returns:
        --------
        list
            Filtered transaction history
        """
        filtered = self.transaction_history
        
        if transaction_type:
            filtered = [t for t in filtered if t['type'] == transaction_type]
        
        if start_date:
            filtered = [t for t in filtered if t['date'] >= start_date]
            
        if end_date:
            filtered = [t for t in filtered if t['date'] <= end_date]
            
        return filtered
    
    def export_to_dataframe(self):
        """
        Export portfolio data to pandas DataFrames.
        
        Returns:
        --------
        tuple
            (holdings_df, history_df, transactions_df)
        """
        # Holdings DataFrame
        holdings_df = pd.DataFrame([
            {
                'ticker': ticker,
                **{k: v for k, v in data.items() if k != 'investments'}
            }
            for ticker, data in self.holdings.items()
        ])
        
        # History DataFrame
        history_df = pd.DataFrame(self.portfolio_history)
        
        # Transactions DataFrame
        transactions_df = pd.DataFrame(self.transaction_history)
        
        return holdings_df, history_df, transactions_df