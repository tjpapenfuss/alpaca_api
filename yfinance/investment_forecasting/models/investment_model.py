import pandas as pd
import numpy as np
from datetime import datetime

from ..config.settings import DEFAULT_CONFIG, validate_config
from ..strategies.allocation import calculate_allocation_weights
# from ..strategies.tax_loss_harvesting import track_and_manage_positions
from ..strategies.rebalancing import check_and_rebalance
from ..utils.data_loader import download_stock_data, extract_tickers_from_source, extract_top_tickers_from_csv
from ..utils.date_utils import generate_investment_dates, get_closest_trading_day
# from ..utils.portfolio_utils import invest_available_cash, calculate_portfolio_value
from ..utils.reporting import generate_report, plot_portfolio_growth, export_results
from ..models.portfolio import Portfolio

class InvestmentForecastingModel:
    def __init__(self, config):
        """
        Initialize the investment forecasting model with configuration parameters.
        """
        self.config = validate_config(config)
        self.initial_investment = config.get('initial_investment', DEFAULT_CONFIG['initial_investment'])
        self.recurring_investment = config.get('recurring_investment', DEFAULT_CONFIG['recurring_investment'])
        self.investment_frequency = config.get('investment_frequency', DEFAULT_CONFIG['investment_frequency'])
        self.start_date = config.get('start_date', DEFAULT_CONFIG['start_date'])
        self.end_date = config.get('end_date', DEFAULT_CONFIG['end_date'])
        self.sell_trigger = config.get('sell_trigger', DEFAULT_CONFIG['sell_trigger'])
        self.top_n = config.get('top_n', DEFAULT_CONFIG['top_n'])
        # Rebalancing variables
        self.rebalance_frequency = config.get('rebalance_frequency', 'quarterly')  # 'monthly', 'quarterly', 'yearly'
        self.rebalance_threshold = config.get('rebalance_threshold', 5)  # Maximum drift percentage before rebalancing
        self.last_rebalance_date = None

        # Load tickers
        if isinstance(config.get('tickers_source', ''), str) and config['tickers_source'].endswith('.csv'):
            self.tickers = extract_top_tickers_from_csv(
                config['tickers_source'], 
                top_n=config.get('top_n', 250)
            )
        else:
            self.tickers = config.get('tickers_source', [])
            
        # Set up portfolio
        self.portfolio_allocation = config.get('portfolio_allocation', 'equal')
        self.portfolio = Portfolio(self.rebalance_frequency, self.rebalance_threshold, \
            self.portfolio_allocation, self.tickers)
        
        # Initialize data structures
        self.stock_data = None
        self.investment_dates = []
        self.investments_tracker = []
        self.transactions = []
        
    def generate_investment_dates(self):
        """Generate dates for recurring investments based on frequency."""
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
                
        self.investment_dates = generate_investment_dates(start_date=start, \
            end_date=end, frequency=self.investment_frequency)
        return self.investment_dates
        
    def run_simulation(self):
        """
        Run the investment simulation based on configuration.
        """
        # Generate investment dates
        self.generate_investment_dates() 
        
        # Download historical stock data
        valid_tickers, self.stock_data = download_stock_data(self.tickers, self.start_date, self.end_date)

        if not valid_tickers:
            print("No valid tickers. Exiting simulation.")
            return
            
        # Calculate allocation weights
        allocation_weights = calculate_allocation_weights(self.tickers, self.portfolio_allocation, self.config['tickers_source'])
        
        # Extract adjusted close prices for analysis
        if "Adj Close" in self.stock_data.columns.levels[1]:
            prices = self.stock_data.xs("Adj Close", level=1, axis=1)
        else:
            print("Error: 'Adj Close' column missing in data. Falling back to 'Close'.")
            prices = self.stock_data.xs("Close", level=1, axis=1)
        
        # Initialize portfolio tracking
        self.portfolio.initialize_holdings(valid_tickers)
        transactions = []
        
        # Make initial investment
        initial_date = self.investment_dates[0]
        initial_investment_amount = self.initial_investment
        
        # Record initial investment transaction
        transactions.append({
            'date': initial_date,
            'type': 'deposit',
            'amount': initial_investment_amount,
            'description': 'Initial investment'
        })
        
        self.portfolio['cash'] += initial_investment_amount
        
        # Process each investment date
        for i, investment_date in enumerate(self.investment_dates):
            # Get the closest trading day (for weekends/holidays)
            closest_date = get_closest_trading_day(investment_date, prices)
            if closest_date is None:
                print(f"Warning: No trading data found near {investment_date}. Skipping investment.")
                continue
                
            # Add recurring investment (except for initial date which is already handled)
            if i > 0:
                self.portfolio['cash'] += self.recurring_investment
                transactions.append({
                    'date': investment_date,
                    'type': 'deposit',
                    'amount': self.recurring_investment,
                    'description': f'{self.investment_frequency.capitalize()} investment'
                })
            
            # First, track and manage positions - this will sell losing positions.
            # Keep track of tickers that were sold for tax-loss harvesting. 
            # Return the portfolio updates and the transactions so preserve changes. 
            transactions, sold_tickers = self.portfolio.track_and_manage_positions(prices, \
                closest_date, transactions, self.sell_trigger)
            
            # Then invest available cash according to allocation, excluding recently sold tickers
            transactions = self.portfolio.invest_available_cash(allocation_weights, prices, \
                closest_date, transactions, excluded_tickers=sold_tickers)
            
            # Rebalance my portfolio.
            #### THEN COME HERE. I need to update my portfolio class to have my rebalance info. 
            #### This should all be hosted as a portfolio and not within my Forecasting model. 
            transactions = self.portfolio.check_and_rebalance(prices=prices, investment_date=investment_date, \
                closest_trading_date=closest_date, start_date=self.start_date, transactions=transactions, rebalance_threshold=self.rebalance_threshold, \
                rebalance_frequency=self.rebalance_frequency, sold_tickers=sold_tickers)

            # Record portfolio value / history for this date
            self.portfolio.update_portfolio_history(prices, closest_date)
        
        # End of simulation - calculate final statistics
        # Taking out the final run. 
        # final_date = self._get_closest_trading_day(self.end_date, prices)
        # if final_date and final_date != self.investment_dates[-1]:
        #     # One final tracking update at the end date
        #     self._track_and_manage_positions(portfolio, prices, final_date, transactions)
        #     portfolio_value = self._calculate_portfolio_value(portfolio, prices, final_date)
        #     portfolio_history.append({
        #         'date': final_date,
        #         'cash': portfolio['cash'],
        #         'investments_value': portfolio_value - portfolio['cash'],
        #         'total_value': portfolio_value
        #     })
        
        # self.transactions = transactions
        # self.portfolio_history = pd.DataFrame(portfolio_history)
        
        # Calculate performance metrics
        self.calculate_performance_metrics()
        history = self.portfolio.get_portfolio_history()
        
        return {
            'portfolio': self.portfolio,
            'transactions': transactions,
            'portfolio_history': history,
            'performance_metrics': self.performance_metrics
        }
        
    def calculate_performance_metrics(self):
        """Calculate performance metrics for the simulation."""    
        history = self.portfolio.get_portfolio_history()

        if len(history) == 0:
            self.performance_metrics = {}
            return
        
        # Calculate total deposits
        deposits = sum(t['amount'] for t in self.transactions if t['type'] == 'deposit')
        
        # Calculate final value
        final_value = history.iloc[-1]['total_value']
        
        # Calculate total return
        total_return = final_value - deposits
        total_return_pct = (final_value / deposits - 1) * 100
        
        # Calculate realized tax losses
        realized_losses = sum(t['gain_loss'] for t in self.transactions 
                             if t['type'] == 'sell' and t.get('gain_loss', 0) < 0)
        
        # Calculate annualized return
        start_date = pd.to_datetime(history.iloc[0]['date'])
        end_date = pd.to_datetime(history.iloc[-1]['date'])
        years = (end_date - start_date).days / 365.25
        annualized_return = ((1 + total_return_pct/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        self.performance_metrics = {
            'total_deposits': deposits,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annualized_return': annualized_return,
            'realized_losses': realized_losses,
            'tax_savings_estimate': realized_losses * -0.30,  # Assuming 30% tax rate
            'num_transactions': len(self.transactions)
        }
        