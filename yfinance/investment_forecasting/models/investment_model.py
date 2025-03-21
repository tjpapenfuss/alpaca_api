import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt

from ..utils.data_loader import download_stock_data, load_tickers_and_weights
from ..utils.date_utils import generate_investment_dates, get_closest_trading_day
from ..utils.reporting import calculate_performance_metrics
from ..strategies.tax_loss_harvesting import track_and_manage_positions
from ..strategies.rebalancing import check_and_rebalance
from ..models.portfolio import Portfolio

class InvestmentForecastingModel:
    def __init__(self, config):
        """
        Initialize the investment forecasting model with configuration parameters.
        
        Parameters:
        -----------
        config : dict
            Dictionary containing configuration parameters
        """
        # Store configuration
        self.config = config
        self.initial_investment = config.get('initial_investment', 10000)
        self.recurring_investment = config.get('recurring_investment', 1000)
        self.investment_frequency = config.get('investment_frequency', 'monthly')
        self.start_date = config.get('start_date', '2023-01-01')
        self.end_date = config.get('end_date', '2024-01-01')
        self.sell_trigger = config.get('sell_trigger', -10)
        
        # Rebalancing variables
        self.rebalance_frequency = config.get('rebalance_frequency', 'quarterly')
        self.rebalance_threshold = config.get('rebalance_threshold', 5)
        self.last_rebalance_date = None
        
        # Load tickers and allocation weights
        self.tickers, self.portfolio_allocation = load_tickers_and_weights(config)
        
        # Initialize data structures
        self.stock_data = None
        self.investment_dates = []
        self.portfolio = None
        self.transactions = []
        self.portfolio_history = []
        self.performance_metrics = {}
    
    def run_simulation(self):
        """
        Run the investment simulation based on configuration.
        """
        # Generate investment dates
        self.investment_dates = generate_investment_dates(
            self.start_date, 
            self.end_date, 
            self.investment_frequency
        )
        
        # Download historical stock data
        self.stock_data, valid_tickers, failed_tickers = download_stock_data(
            self.tickers, 
            self.start_date, 
            self.end_date
        )
        
        if not valid_tickers:
            print("No valid tickers. Exiting simulation.")
            return None
            
        # Update tickers list to only include valid ones
        self.tickers = valid_tickers
        
        # Extract adjusted close prices for analysis
        if "Adj Close" in self.stock_data.columns.levels[1]:
            prices = self.stock_data.xs("Adj Close", level=1, axis=1)
        else:
            print("Error: 'Adj Close' column missing in data. Falling back to 'Close'.")
            prices = self.stock_data.xs("Close", level=1, axis=1)
        
        # Initialize portfolio
        self.portfolio = Portfolio(self.tickers)
        portfolio_history = []
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
        
        self.portfolio.add_cash(initial_investment_amount)
        
        # Process each investment date
        for i, investment_date in enumerate(self.investment_dates):
            # Get the closest trading day (for weekends/holidays)
            closest_date = get_closest_trading_day(investment_date, prices)
            if closest_date is None:
                print(f"Warning: No trading data found near {investment_date}. Skipping investment.")
                continue
                
            # Add recurring investment (except for initial date which is already handled)
            if i > 0:
                self.portfolio.add_cash(self.recurring_investment)
                transactions.append({
                    'date': investment_date,
                    'type': 'deposit',
                    'amount': self.recurring_investment,
                    'description': f'{self.investment_frequency.capitalize()} investment'
                })
            
            # Execute trading strategy: tax loss harvesting and then rebalancing
            sold_tickers = track_and_manage_positions(
                self.portfolio, 
                prices, 
                closest_date, 
                transactions, 
                self.sell_trigger
            )
            
            # Invest available cash according to allocation
            self.portfolio.invest_available_cash(
                self.portfolio_allocation,
                prices,
                closest_date, 
                transactions,
                excluded_tickers=sold_tickers
            )
            
            # Rebalance portfolio if needed
            check_and_rebalance(
                self.portfolio,
                self.portfolio_allocation,
                prices, 
                closest_date, 
                transactions, 
                self.rebalance_frequency,
                self.rebalance_threshold,
                self.last_rebalance_date,
                self.start_date,
                sold_tickers
            )
            
            if hasattr(self, 'last_rebalance_date'):
                self.last_rebalance_date = closest_date

            # Record portfolio value for this date
            portfolio_value = self.portfolio.calculate_total_value(prices, closest_date)
            investments_value = portfolio_value - self.portfolio.cash
            
            portfolio_history.append({
                'date': closest_date,
                'cash': self.portfolio.cash,
                'investments_value': investments_value,
                'total_value': portfolio_value
            })
        
        # End of simulation - calculate final statistics
        final_date = get_closest_trading_day(self.end_date, prices)
        if final_date and final_date != self.investment_dates[-1]:
            # One final tracking update at the end date
            track_and_manage_positions(
                self.portfolio, 
                prices, 
                final_date, 
                transactions, 
                self.sell_trigger
            )
            
            portfolio_value = self.portfolio.calculate_total_value(prices, final_date)
            investments_value = portfolio_value - self.portfolio.cash
            
            portfolio_history.append({
                'date': final_date,
                'cash': self.portfolio.cash,
                'investments_value': investments_value,
                'total_value': portfolio_value
            })
        
        self.transactions = transactions
        self.portfolio_history = pd.DataFrame(portfolio_history)
        
        # Calculate performance metrics
        self.performance_metrics = calculate_performance_metrics(
            self.portfolio_history,
            self.transactions
        )
        
        return {
            'portfolio': self.portfolio,
            'transactions': transactions,
            'portfolio_history': self.portfolio_history,
            'performance_metrics': self.performance_metrics
        }
    
    def generate_report(self, report_generator=None):
        """Generate a summary report of the simulation."""
        if not hasattr(self, 'performance_metrics') or not self.performance_metrics:
            print("No simulation results found. Run simulation first.")
            return
        
        if report_generator:
            return report_generator(self)
        
        # Default simple report
        report = []
        report.append("Investment Simulation Report")
        report.append("=" * 30)
        report.append(f"Simulation Period: {self.start_date} to {self.end_date}")
        report.append(f"Initial Investment: ${self.initial_investment:,.2f}")
        report.append(f"Recurring Investment: ${self.recurring_investment:,.2f} ({self.investment_frequency})")
        report.append(f"Sell Trigger: {self.sell_trigger}%")
        report.append(f"Number of Tickers: {len(self.tickers)}")
        report.append("=" * 30)
        report.append("Performance Summary:")
        
        metrics = self.performance_metrics
        report.append(f"Total Deposits: ${metrics['total_deposits']:,.2f}")
        report.append(f"Final Portfolio Value: ${metrics['final_value']:,.2f}")
        report.append(f"Total Return: ${metrics['total_return']:,.2f} ({metrics['total_return_pct']:.2f}%)")
        report.append(f"Annualized Return: {metrics['annualized_return']:.2f}%")
        report.append(f"Realized Losses: ${metrics['realized_losses']:,.2f}")
        report.append(f"Estimated Tax Savings: ${metrics['tax_savings_estimate']:,.2f}")
        report.append(f"Number of Transactions: {metrics['num_transactions']}")
        
        return "\n".join(report)