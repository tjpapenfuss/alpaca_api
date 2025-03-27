import pandas as pd
import numpy as np
from datetime import datetime

from config.settings import DEFAULT_CONFIG, validate_config
from utils.data_loader import extract_top_tickers_from_csv, extract_weights_from_csv, download_stock_data
from utils.date_utils import generate_investment_dates, get_closest_trading_day
from utils.reporting import generate_report, plot_portfolio_growth, export_results
from models.portfolio import Portfolio
from strategies.tax_loss_harvesting import track_and_manage_positions
from utils.allocation import invest_available_cash, calculate_allocation_weights

class InvestmentForecastingModel:
    def __init__(self, config=None):
        """
        Initialize the investment forecasting model with configuration parameters.
        
        Parameters:
        -----------
        config : dict, optional
            Configuration dictionary with simulation parameters
        """
        # Use default config if none provided
        if config is None:
            config = DEFAULT_CONFIG
        else:
            config = validate_config(config)
        
        # Store configuration parameters
        self.config = config
        self.initial_investment = config.get('initial_investment', DEFAULT_CONFIG['initial_investment'])
        self.recurring_investment = config.get('recurring_investment', DEFAULT_CONFIG['recurring_investment'])
        self.investment_frequency = config.get('investment_frequency', DEFAULT_CONFIG['investment_frequency'])
        self.start_date = config.get('start_date', DEFAULT_CONFIG['start_date'])
        self.end_date = config.get('end_date', DEFAULT_CONFIG['end_date'])
        self.sell_trigger = config.get('sell_trigger', DEFAULT_CONFIG['sell_trigger'])
        self.top_n = config.get('top_n', DEFAULT_CONFIG['top_n'])
        self.tickers_source = config.get('tickers_source', DEFAULT_CONFIG['tickers_source'])
        self.pickle_file = config.get('pickle_file', None)
        
        # Rebalancing variables
        self.rebalance_frequency = config.get('rebalance_frequency', 'quarterly')
        self.rebalance_threshold = config.get('rebalance_threshold', 5)  

        # Get tickers from configuration
        self.tickers = extract_top_tickers_from_csv(
            csv_file=self.tickers_source, 
            top_n=self.top_n
        )
        
        # Initialize portfolio with allocation strategy
        self.portfolio_allocation = config.get('portfolio_allocation', 'equal')
        if(self.portfolio_allocation != 'equal'):
            # self.tickers = self._load_tickers_from_config(config)
            custom_allocation = extract_weights_from_csv(self.tickers_source, self.top_n)
            
            # Adjust allocation weights to exclude tickers that were just sold
            adjusted_weights = custom_allocation.copy()

            # Normalize remaining weights to sum to 1
            weight_sum = sum(adjusted_weights.values())
            if weight_sum > 0:  # Avoid division by zero
                self.portfolio_allocation = {k: float(f"{(v/weight_sum):.4f}") for k, v in adjusted_weights.items()}            
        
        self.portfolio = Portfolio(
            rebalance_frequency=self.rebalance_frequency, 
            rebalance_threshold=self.rebalance_threshold,
            portfolio_allocation=self.portfolio_allocation,
            tickers=self.tickers,
            name=config.get('portfolio_name', 'Simulation Portfolio')
        )
        
        # Initialize data structures
        self.stock_data = None
        self.investment_dates = []
        self.performance_metrics = {}
        self.prices_df = []
        
    def _load_tickers_from_config(self, config):
        """
        Load ticker symbols from the configuration.
        
        Parameters:
        -----------
        config : dict
            Configuration dictionary
            
        Returns:
        --------
        list
            List of ticker symbols
        """
        tickers_source = config.get('tickers_source', [])
        
        # Check if tickers are provided as a CSV file
        if isinstance(tickers_source, str) and tickers_source.endswith('.csv'):
            return extract_top_tickers_from_csv(
                tickers_source, 
                top_n=config.get('top_n', 250)
            )
        # Otherwise assume it's a list of tickers
        else:
            return tickers_source
        
    def get_investment_dates(self):
        """
        Generate dates for recurring investments based on frequency.
        
        Returns:
        --------
        list
            List of investment dates
        """
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
                
        self.investment_dates = generate_investment_dates(
            start_date=start,
            end_date=end, 
            frequency=self.investment_frequency
        )
        return self.investment_dates
        
    def run_simulation(self):
        """
        Run the investment simulation based on configuration.
        
        Returns:
        --------
        dict
            Simulation results including portfolio data, transactions, and performance metrics
        """
        # Generate investment dates
        self.get_investment_dates() 
        
        # Download historical stock data
        valid_tickers, self.stock_data = download_stock_data(
            self.tickers, 
            self.start_date, 
            self.end_date,
            pickle_file=self.pickle_file # TAKE THIS OUT IF YOU DON'T WANT TO USE THE PICKLE!!
        )

        if not valid_tickers:
            print("No valid tickers. Exiting simulation.")
            return None
            
        # Extract adjusted close prices for analysis
        self.prices_df = self._extract_price_data()
        if self.prices_df is None:
            return None
        
        # Ensure all dates are datetime
        self.prices_df.index = pd.to_datetime(self.prices_df.index)

        # Initialize portfolio with valid tickers
        self.portfolio.initialize_holdings(valid_tickers)
        
        # Make initial investment
        initial_date = self.investment_dates[0]
        self._make_initial_investment(initial_date)
        
        # Process each investment date
        self._process_investment_dates()
        
        # Calculate performance metrics
        self.calculate_performance_metrics()
        
        # Export portfolio data to DataFrames
        holdings_df, history_df, transactions_df = self.portfolio.export_to_dataframe()
        
        # Return simulation results
        return {
            'portfolio': holdings_df,
            'transactions': transactions_df,
            'portfolio_history': history_df,
            'performance_metrics': self.performance_metrics
        }
    
    def _extract_price_data(self, decimals=2):
        """
        Extract price data from stock data.
        
        Returns:
        --------
        pandas.DataFrame
            DataFrame of adjusted close prices
        """
        if "Close" in self.stock_data.columns.levels[1]:
            close_prices = self.stock_data.xs("Close", level=1, axis=1)
            return close_prices.round(decimals)
        else:
            print("Error: 'Close' column not found in data.")
            return None
    
    def _make_initial_investment(self, initial_date):
        """
        Make the initial investment into the portfolio.
        
        Parameters:
        -----------
        initial_date : datetime
            Date of the initial investment
        """
        # Add cash to portfolio and record transaction
        self.portfolio.add_cash(
            amount=self.initial_investment,
            transaction_date=initial_date,
            description='Initial investment'
        )
    
    def _process_investment_dates(self):
        """
        Process each investment date in the simulation.
        
        Parameters:
        -----------
        prices : pandas.DataFrame
            DataFrame of price data
        """
        for i, investment_date in enumerate(self.investment_dates):
            # Get the closest trading day (for weekends/holidays)
            closest_date = get_closest_trading_day(investment_date, self.prices_df)
            if closest_date is None:
                print(f"Warning: No trading data found near {investment_date}. Skipping investment.")
                continue
                
            # Add recurring investment (except for initial date which is already handled)
            if i > 0:
                self.portfolio.add_cash(
                    amount=self.recurring_investment,
                    transaction_date=investment_date,
                    description=f'{self.investment_frequency.capitalize()} investment'
                )
            
            # Run the investment cycle for this date
            self._run_investment_cycle(closest_date, investment_date)
            
            # Update portfolio history for this date
            self.portfolio.update_portfolio_history(self.prices_df, closest_date)
    
    def _run_investment_cycle(self, closest_date, investment_date):
        """
        Run a single investment cycle for a specific date.
        
        Parameters:
        -----------
        self.prices_df : pandas.DataFrame
            DataFrame of price data
        closest_date : str
            Closest trading date
        investment_date : datetime
            Original investment date
        """
        # Calculate target allocation weights
        allocation_weights = calculate_allocation_weights(self.portfolio)
        
        # 1. Track and manage positions - tax-loss harvesting
        transactions = self.portfolio.get_transaction_history()
        transactions, sold_tickers = track_and_manage_positions(
            self.portfolio, 
            self.prices_df, 
            closest_date, 
            transactions, 
            self.sell_trigger
        )
        
        # 2. Invest available cash according to allocation
        invest_available_cash(
            self.portfolio, 
            allocation_weights, 
            self.prices_df, 
            closest_date, 
            transactions, 
            excluded_tickers=sold_tickers
        )
        
        # 3. Check if rebalancing is needed and execute if necessary
        rebalance_tickers(
            portfolio=self.portfolio, 
            prices=self.prices_df, 
            investment_date=investment_date, 
            closest_trading_date=closest_date, 
            start_date=self.start_date, 
            sold_tickers=sold_tickers
        )
        
    def calculate_performance_metrics(self):
        """
        Calculate performance metrics for the simulation.
        
        Returns:
        --------
        dict
            Dictionary of performance metrics
        """    
        history_df = pd.DataFrame(self.portfolio.get_portfolio_history())

        if len(history_df) == 0:
            self.performance_metrics = {}
            return {}
        
        # Get all deposits
        transactions = self.portfolio.get_transaction_history(transaction_type='deposit')
        deposits = sum(t['amount'] for t in transactions)
        
        # Get final portfolio value
        final_value = history_df.iloc[-1]['total_value']
        
        # Calculate total return
        total_return = final_value - deposits
        total_return_pct = (final_value / deposits - 1) * 100 if deposits > 0 else 0
        
        # Get realized losses for tax-loss harvesting
        sell_transactions = self.portfolio.get_transaction_history(transaction_type='sell')
        realized_losses = sum(t.get('gain_loss', 0) for t in sell_transactions if t.get('gain_loss', 0) < 0)
        
        # Calculate annualized return
        start_date = pd.to_datetime(history_df.iloc[0]['date'])
        end_date = pd.to_datetime(history_df.iloc[-1]['date'])
        years = (end_date - start_date).days / 365.25
        annualized_return = ((1 + total_return_pct/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # Store metrics
        self.performance_metrics = {
            'total_deposits': deposits,
            'final_value': final_value,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annualized_return': annualized_return,
            'realized_losses': realized_losses,
            'tax_savings_estimate': realized_losses * -0.30,  # Assuming 30% tax rate
            'num_transactions': len(self.portfolio.get_transaction_history()),
            'long_term_realized_losses': self.portfolio.long_term_realized_losses,
            'short_term_realized_losses': self.portfolio.short_term_realized_losses,
            'long_term_realized_gains': self.portfolio.long_term_realized_gains,
            'short_term_realized_gains': self.portfolio.short_term_realized_gains
        }
        print("Realized Gains total:")
        print(sum(t.get('gain_loss', 0) for t in sell_transactions if t.get('gain_loss', 0) > 0))
        return self.performance_metrics

# Helper function for rebalancing to keep the class interface clean
def rebalance_tickers(portfolio: Portfolio, prices, investment_date, closest_trading_date, start_date, sold_tickers=None):
    """
    Check if rebalancing is needed and execute if necessary.
    
    Parameters:
    -----------
    portfolio : Portfolio
        Portfolio object
    prices : pandas.DataFrame
        DataFrame of price data
    investment_date : datetime
        Investment date
    closest_trading_date : str
        Closest trading date
    start_date : str
        Simulation start date
    sold_tickers : list, optional
        List of tickers that were recently sold and should be excluded from rebalancing
        
    Returns:
    --------
    list
        Updated transaction history
    """
    # Get current transaction history
    transactions = portfolio.get_transaction_history()
    
    # Perform rebalancing if needed
    from utils.rebalance import check_and_rebalance

    return check_and_rebalance(
        portfolio=portfolio,
        prices=prices,
        investment_date=investment_date,
        closest_trading_date=closest_trading_date,
        start_date=start_date,
        transactions=transactions,
        sold_tickers=sold_tickers or []
    )

