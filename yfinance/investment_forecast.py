import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import matplotlib.pyplot as plt
from pull_tickers import extract_weights_from_csv, extract_top_tickers_from_csv

class InvestmentForecastingModel:
    def __init__(self, config):
        """
        Initialize the investment forecasting model with configuration parameters.
        
        Parameters:
        -----------
        config : dict
            Dictionary containing configuration parameters:
            - initial_investment: Initial lump sum investment amount
            - recurring_investment: Amount to invest at regular intervals
            - investment_frequency: 'monthly' or 'bimonthly'
            - start_date: Start date for the analysis (YYYY-MM-DD)
            - end_date: End date for the analysis (YYYY-MM-DD)
            - tickers_source: Path to CSV file with tickers or list of tickers
            - top_n: Number of top tickers to use (if using CSV)
            - sell_trigger: Percentage decline to trigger a sell (-10 means sell at 10% loss)
            - portfolio_allocation: Dict of ticker to weight or 'equal'
        """
        self.config = config
        self.initial_investment = config.get('initial_investment', 10000)
        self.recurring_investment = config.get('recurring_investment', 1000)
        self.investment_frequency = config.get('investment_frequency', 'monthly')
        self.start_date = config.get('start_date', '2023-01-01')
        self.end_date = config.get('end_date', '2024-01-01')
        self.sell_trigger = config.get('sell_trigger', -10)
        
        # Load tickers
        if isinstance(config.get('tickers_source', ''), str) and config['tickers_source'].endswith('.csv'):
            self.tickers = extract_top_tickers_from_csv(
                config['tickers_source'], 
                top_n=config.get('top_n', 250)
            )
        else:
            self.tickers = config.get('tickers_source', [])
            
        # Set up portfolio allocation
        self.portfolio_allocation = config.get('portfolio_allocation', 'equal')
        
        # Initialize data structures
        self.stock_data = None
        self.investment_dates = []
        self.investments_tracker = []
        self.transactions = []
        self.portfolio_history = []
        
    def generate_investment_dates(self):
        """Generate dates for recurring investments based on frequency."""
        start = datetime.strptime(self.start_date, '%Y-%m-%d')
        end = datetime.strptime(self.end_date, '%Y-%m-%d')
        
        dates = [start]  # Start with initial investment date
        current = start
        
        # Generate recurring investment dates
        while current < end:
            if self.investment_frequency == 'monthly':
                current = current + relativedelta(months=1)
            elif self.investment_frequency == 'bimonthly':
                current = current + relativedelta(months=2)
            else:
                raise ValueError("Investment frequency must be 'monthly' or 'bimonthly'")
            
            if current <= end:
                dates.append(current)
                
        self.investment_dates = [d.strftime('%Y-%m-%d') for d in dates]
        return self.investment_dates
    
    def download_stock_data(self):
        """Download daily stock price data for the specified tickers and date range."""
        print(f"Downloading data for {len(self.tickers)} tickers...")
        
        # Add buffer days before start date to calculate returns properly
        start_buffer = datetime.strptime(self.start_date, '%Y-%m-%d') - timedelta(days=5)
        
        try:
            stock_data = yf.download(
                tickers=self.tickers, 
                start=start_buffer.strftime('%Y-%m-%d'), 
                end=self.end_date, 
                interval="1d", 
                group_by='ticker'
            )
            
            # Handle failed tickers
            valid_tickers = [ticker for ticker in self.tickers if ticker in stock_data.columns.levels[0]]
            failed_tickers = [ticker for ticker in self.tickers if ticker not in stock_data.columns.levels[0]]
            
            if failed_tickers:
                print(f"Failed to download data for {len(failed_tickers)} tickers.")
            
            print(f"Successfully downloaded data for {len(valid_tickers)} tickers.")
            self.tickers = valid_tickers
            self.stock_data = stock_data
            
            return valid_tickers, failed_tickers
            
        except Exception as e:
            print(f"Error downloading stock data: {e}")
            return [], self.tickers
    
    def calculate_allocation_weights(self):
        """Calculate allocation weights for the portfolio."""
        if self.portfolio_allocation == 'equal':
            # Equal weight allocation
            weight = 1.0 / len(self.tickers)
            return {ticker: weight for ticker in self.tickers}
        elif isinstance(self.portfolio_allocation, dict):
            # User-provided weights
            # Normalize to ensure weights sum to 1
            total_weight = sum(self.portfolio_allocation.values())
            return {t: w/total_weight for t, w in self.portfolio_allocation.items() if t in self.tickers}
        elif isinstance(self.portfolio_allocation, str) and self.portfolio_allocation.endswith('.csv'):
            # Load weights from CSV
            try:
                weights_dict = extract_weights_from_csv(self.portfolio_allocation)
                # Filter for only our tickers and normalize
                filtered_weights = {t: weights_dict.get(t, 0) for t in self.tickers}
                total_weight = sum(filtered_weights.values())
                if total_weight > 0:
                    return {t: w/total_weight for t, w in filtered_weights.items()}
                else:
                    # Fall back to equal weight if no weights found
                    weight = 1.0 / len(self.tickers)
                    return {ticker: weight for ticker in self.tickers}
            except Exception as e:
                print(f"Error loading weights from CSV: {e}")
                # Fall back to equal weight
                weight = 1.0 / len(self.tickers)
                return {ticker: weight for ticker in self.tickers}
    
    def run_simulation(self):
        """
        Run the investment simulation based on configuration.
        """
        # Generate investment dates
        self.generate_investment_dates()
        
        # Download historical stock data
        valid_tickers, _ = self.download_stock_data()
        if not valid_tickers:
            print("No valid tickers. Exiting simulation.")
            return
            
        # Calculate allocation weights
        allocation_weights = self.calculate_allocation_weights()
        
        # Extract adjusted close prices for analysis
        if "Adj Close" in self.stock_data.columns.levels[1]:
            prices = self.stock_data.xs("Adj Close", level=1, axis=1)
        else:
            print("Error: 'Adj Close' column missing in data. Falling back to 'Close'.")
            prices = self.stock_data.xs("Close", level=1, axis=1)
        
        # Initialize portfolio tracking
        portfolio = {
            'cash': 0,
            'holdings': {ticker: {'shares': 0, 'cost_basis': 0, 'investments': []} for ticker in valid_tickers}
        }
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
        
        portfolio['cash'] += initial_investment_amount
        
        # Process each investment date
        for i, investment_date in enumerate(self.investment_dates):
            # Get the closest trading day (for weekends/holidays)
            closest_date = self._get_closest_trading_day(investment_date, prices)
            if closest_date is None:
                print(f"Warning: No trading data found near {investment_date}. Skipping investment.")
                continue
                
            # Add recurring investment (except for initial date which is already handled)
            if i > 0:
                portfolio['cash'] += self.recurring_investment
                transactions.append({
                    'date': investment_date,
                    'type': 'deposit',
                    'amount': self.recurring_investment,
                    'description': f'{self.investment_frequency.capitalize()} investment'
                })
            
            # First, track and manage positions - this will sell losing positions
            # Keep track of tickers that were sold for tax-loss harvesting
            sold_tickers = self._track_and_manage_positions(portfolio, prices, closest_date, transactions)
            
            # Then invest available cash according to allocation, excluding recently sold tickers
            self._invest_available_cash(portfolio, allocation_weights, prices, closest_date, transactions, excluded_tickers=sold_tickers)
            
            # Record portfolio value for this date
            portfolio_value = self._calculate_portfolio_value(portfolio, prices, closest_date)
            portfolio_history.append({
                'date': closest_date,
                'cash': portfolio['cash'],
                'investments_value': portfolio_value - portfolio['cash'],
                'total_value': portfolio_value
            })
        
        # End of simulation - calculate final statistics
        final_date = self._get_closest_trading_day(self.end_date, prices)
        if final_date and final_date != self.investment_dates[-1]:
            # One final tracking update at the end date
            self._track_and_manage_positions(portfolio, prices, final_date, transactions)
            portfolio_value = self._calculate_portfolio_value(portfolio, prices, final_date)
            portfolio_history.append({
                'date': final_date,
                'cash': portfolio['cash'],
                'investments_value': portfolio_value - portfolio['cash'],
                'total_value': portfolio_value
            })
        
        self.portfolio = portfolio
        self.transactions = transactions
        self.portfolio_history = pd.DataFrame(portfolio_history)
        
        # Calculate performance metrics
        self._calculate_performance_metrics()
        
        return {
            'portfolio': portfolio,
            'transactions': transactions,
            'portfolio_history': self.portfolio_history,
            'performance_metrics': self.performance_metrics
        }
    
    def _get_closest_trading_day(self, date_str, prices_df):
        """Find the closest trading day to the given date."""
        target_date = pd.to_datetime(date_str)
        
        # Try exact date first
        if target_date in prices_df.index:
            return date_str
            
        # Look for closest date within 5 days
        for i in range(1, 6):
            # Try dates after
            forward_date = target_date + pd.Timedelta(days=i)
            if forward_date in prices_df.index:
                return forward_date.strftime('%Y-%m-%d')
                
            # Try dates before
            backward_date = target_date - pd.Timedelta(days=i)
            if backward_date in prices_df.index:
                return backward_date.strftime('%Y-%m-%d')
                
        return None
    
    def _invest_available_cash(self, portfolio, allocation_weights, prices, date, transactions, excluded_tickers=None):
        """
        Invest available cash according to target allocation weights.
        
        Args:
            excluded_tickers (list, optional): Tickers to exclude from purchase (e.g., recently sold)
        """
        if excluded_tickers is None:
            excluded_tickers = []
            
        date_prices = prices.loc[date]
        available_cash = portfolio['cash']
        
        # Skip if no available cash
        if available_cash <= 0:
            return
            
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
            adjusted_weights = {k: v/weight_sum for k, v in adjusted_weights.items()}
        
        # Calculate amount to invest in each ticker
        for ticker, weight in adjusted_weights.items():
            if ticker not in date_prices or pd.isna(date_prices[ticker]):
                continue
                
            # Calculate investment amount and number of shares
            investment_amount = available_cash * weight
            price = date_prices[ticker]
            shares_to_buy = investment_amount / price
            
            # Round down to nearest share and calculate actual investment
            shares_to_buy = int(shares_to_buy)
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
                    'description': f'Bought {shares_to_buy} shares of {ticker}'
                })
    
    def _track_and_manage_positions(self, portfolio, prices, date, transactions):
        """
        Track position performance and trigger sells based on loss threshold.
        This implements the tax-loss harvesting strategy.
        
        Returns:
            list: Tickers that were sold for tax-loss harvesting
        """
        date_prices = prices.loc[date]
        sold_tickers = []
        
        for ticker, holding in portfolio['holdings'].items():
            if ticker not in date_prices or pd.isna(date_prices[ticker]):
                continue
                
            current_price = date_prices[ticker]
            ticker_sold = False
            
            # Update each investment's current value and return
            for investment in holding['investments']:
                if investment['sold']:
                    continue
                    
                previous_value = investment['current_value']
                current_value = investment['shares'] * current_price
                investment['current_value'] = current_value
                investment['return_pct'] = ((current_value / investment['cost']) - 1) * 100
                investment['days_held'] += 1
                
                # Check if this specific investment meets the sell trigger
                if investment['return_pct'] <= self.sell_trigger:
                    # Sell this specific lot
                    investment['sold'] = True
                    
                    # Update portfolio
                    holding['shares'] -= investment['shares']
                    sale_proceeds = investment['shares'] * current_price
                    portfolio['cash'] += sale_proceeds
                    
                    # Calculate loss for reporting
                    realized_loss = sale_proceeds - investment['cost']
                    loss_pct = investment['return_pct']
                    
                    # Record transaction
                    transactions.append({
                        'date': date,
                        'type': 'sell',
                        'ticker': ticker,
                        'shares': investment['shares'],
                        'price': current_price,
                        'amount': sale_proceeds,
                        'gain_loss': realized_loss,
                        'gain_loss_pct': loss_pct,
                        'days_held': investment['days_held'],
                        'description': f'Sold {investment["shares"]} shares of {ticker} for tax-loss harvesting'
                    })
                    
                    ticker_sold = True
            
            if ticker_sold:
                sold_tickers.append(ticker)
        
        return sold_tickers
    
    def _calculate_portfolio_value(self, portfolio, prices, date):
        """Calculate total portfolio value including cash and holdings."""
        date_prices = prices.loc[date]
        
        holdings_value = 0
        for ticker, holding in portfolio['holdings'].items():
            if ticker in date_prices and not pd.isna(date_prices[ticker]):
                holdings_value += holding['shares'] * date_prices[ticker]
        
        return portfolio['cash'] + holdings_value
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics for the simulation."""
        if len(self.portfolio_history) == 0:
            self.performance_metrics = {}
            return
            
        history = self.portfolio_history
        
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
        
    def generate_report(self):
        """Generate a summary report of the simulation."""
        if not hasattr(self, 'performance_metrics'):
            print("No simulation results found. Run simulation first.")
            return
        
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
        report.append(f"Total Deposits: ${self.performance_metrics['total_deposits']:,.2f}")
        report.append(f"Final Portfolio Value: ${self.performance_metrics['final_value']:,.2f}")
        report.append(f"Total Return: ${self.performance_metrics['total_return']:,.2f} ({self.performance_metrics['total_return_pct']:.2f}%)")
        report.append(f"Annualized Return: {self.performance_metrics['annualized_return']:.2f}%")
        report.append(f"Realized Losses: ${self.performance_metrics['realized_losses']:,.2f}")
        report.append(f"Estimated Tax Savings: ${self.performance_metrics['tax_savings_estimate']:,.2f}")
        report.append(f"Number of Transactions: {self.performance_metrics['num_transactions']}")
        
        return "\n".join(report)
    
    def plot_portfolio_growth(self):
        """Plot the portfolio growth over time with SPY benchmark comparison."""
        if not hasattr(self, 'portfolio_history') or len(self.portfolio_history) == 0:
            print("No simulation results found. Run simulation first.")
            return
            
        plt.figure(figsize=(12, 6))
        
        # Convert dates to datetime for plotting
        dates = pd.to_datetime(self.portfolio_history['date'])
        
        # Plot total value
        plt.plot(
            dates, 
            self.portfolio_history['total_value'],
            label='Total Portfolio Value'
        )
        
        # Plot investments value (excluding cash)
        plt.plot(
            dates, 
            self.portfolio_history['investments_value'],
            label='Investments Value'
        )
        
        # Plot cash value
        plt.plot(
            dates, 
            self.portfolio_history['cash'],
            label='Cash'
        )
        
        # Calculate and plot cumulative deposits line
        deposits = [t for t in self.transactions if t['type'] == 'deposit']
        deposit_dates = [pd.to_datetime(d['date']) for d in deposits]
        deposit_amounts = [d['amount'] for d in deposits]
        
        cum_deposits = []
        curr_total = 0
        
        for date in dates:
                # Taking this out for now...only doing monthly contributions.
            # while deposit_dates and deposit_dates[0] <= date:
            if(deposit_amounts and deposit_dates):
                curr_total += deposit_amounts.pop(0)
                deposit_dates.pop(0)
            cum_deposits.append(curr_total)

        plt.plot(
            dates, 
            cum_deposits,
            label='Cumulative Deposits',
            linestyle='--'
        )
        
        # Download SPY data and add to the plot
        try:
            # Get first and last date from portfolio history
            start_date = dates.min() - pd.Timedelta(days=5)  # 5 days buffer before first date
            end_date = dates.max() + pd.Timedelta(days=1)    # 1 day buffer after last date
            
            # Download SPY data
            spy_data = yf.download(
                tickers='SPY',
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval="1d",
                group_by='ticker'
            )

            spy_close = spy_data.xs("Close", level=1, axis=1)
            
            if not spy_data.empty:
                # Use Close prices instead of Adj Close
                # spy_close = spy_data['Close']
                
                # Filter SPY data to match our portfolio dates
                spy_values = []
                first_deposit_amount = deposits[0]['amount'] if deposits else 0
                
                # Make a copy of cum_deposits to avoid modifying the original
                cum_deposits_copy = cum_deposits.copy()
                
                # Normalize SPY to match initial investment
                prev_spy_price = None
                for i, date in enumerate(dates):
                    # Find closest date in SPY data
                    closest_date = self._find_closest_date(date, spy_close.index)
                    if closest_date is not None:
                        # Make sure we get a scalar value
                        spy_price = float(spy_close.loc[closest_date, 'SPY'])
                        print(spy_price)
                        
                        if prev_spy_price is None:
                            prev_spy_price = spy_price
                            spy_values.append(first_deposit_amount)
                        else:
                            # Calculate value of initial investment if it had been invested in SPY over the past period
                            spy_return = spy_price / prev_spy_price

                            # Add recurring investments with a more straightforward approach
                            current_deposit = cum_deposits_copy[i]
                            previous_deposit = first_deposit_amount if i == 0 else cum_deposits_copy[i-1]
                            new_investment = current_deposit - previous_deposit
                            
                            if i > 0 and new_investment > 0:
                                # For new money, we start fresh (no returns yet)
                                spy_values.append(spy_values[-1] * spy_return + new_investment)
                            else:
                                # Just the return on existing investment with the return over the period.
                                spy_values.append(spy_values[-1] * spy_return)
                            
                            prev_spy_price = spy_price
                    else:
                        # If no spy data for this date, use previous value
                        spy_values.append(spy_values[-1] if spy_values else first_deposit_amount)
                print(spy_values)
                print("SPY VALUES")
                plt.plot(
                    dates,
                    spy_values,
                    label='S&P 500 (SPY) Equivalent',
                    color='green',
                    linestyle='-.',
                    linewidth=2
                )
        except Exception as e:
            print(f"Error adding SPY benchmark: {e}")
            import traceback
            traceback.print_exc()
        
        plt.title('Portfolio Growth vs S&P 500')
        plt.xlabel('Date')
        plt.ylabel('Value ($)')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        return plt

    def _find_closest_date(self, target_date, date_index):
        """Find the closest date in the index to the target date."""
        # Try exact date first
        if target_date in date_index:
            return target_date
            
        # Look for closest date within 5 days
        for i in range(1, 6):
            # Try dates after
            forward_date = target_date + pd.Timedelta(days=i)
            if forward_date in date_index:
                return forward_date
                
            # Try dates before
            backward_date = target_date - pd.Timedelta(days=i)
            if backward_date in date_index:
                return backward_date
                
        return None
    
    def get_tax_loss_harvesting_summary(self):
        """Generate a summary of tax-loss harvesting transactions."""
        if not hasattr(self, 'transactions'):
            print("No simulation results found. Run simulation first.")
            return
            
        # Filter sell transactions with losses
        loss_transactions = [t for t in self.transactions 
                           if t['type'] == 'sell' and t.get('gain_loss', 0) < 0]
        
        if not loss_transactions:
            return "No tax-loss harvesting transactions found."
            
        # Group by ticker
        by_ticker = {}
        for t in loss_transactions:
            ticker = t['ticker']
            if ticker not in by_ticker:
                by_ticker[ticker] = []
            by_ticker[ticker].append(t)
            
        # Create summary
        summary = []
        summary.append("Tax-Loss Harvesting Summary")
        summary.append("=" * 30)
        
        total_proceeds = 0
        total_losses = 0
        
        for ticker, transactions in by_ticker.items():
            ticker_proceeds = sum(t['amount'] for t in transactions)
            ticker_losses = sum(t['gain_loss'] for t in transactions)
            num_transactions = len(transactions)
            
            summary.append(f"{ticker}: {num_transactions} sales")
            summary.append(f"  Total Proceeds: ${ticker_proceeds:,.2f}")
            summary.append(f"  Total Losses: ${ticker_losses:,.2f}")
            summary.append(f"  Average Loss: {ticker_losses/ticker_proceeds*100:.2f}%")
            summary.append("")
            
            total_proceeds += ticker_proceeds
            total_losses += ticker_losses
            
        summary.append("=" * 30)
        summary.append(f"Overall Summary:")
        summary.append(f"Total Sales: {len(loss_transactions)}")
        summary.append(f"Total Proceeds: ${total_proceeds:,.2f}")
        summary.append(f"Total Losses: ${total_losses:,.2f}")
        summary.append(f"Estimated Tax Savings (30% rate): ${-total_losses*0.30:,.2f}")
        
        return "\n".join(summary)
    
    def export_results(self, base_filename):
        """Export simulation results to CSV files."""
        if not hasattr(self, 'portfolio_history'):
            print("No simulation results found. Run simulation first.")
            return
            
        # Export portfolio history
        self.portfolio_history.to_csv(f"{base_filename}_portfolio_history.csv", index=False)
        
        # Export transactions
        transactions_df = pd.DataFrame(self.transactions)
        transactions_df.to_csv(f"{base_filename}_transactions.csv", index=False)
        
        # Export performance metrics
        metrics_df = pd.DataFrame([self.performance_metrics])
        metrics_df.to_csv(f"{base_filename}_performance_metrics.csv", index=False)
        
        # Export summary report
        with open(f"{base_filename}_report.txt", 'w') as f:
            f.write(self.generate_report())
            f.write("\n\n")
            f.write(self.get_tax_loss_harvesting_summary())
            
        print(f"Results exported to {base_filename}_*.csv/txt files")



if __name__ == "__main__":
    # Configuration for simulation
    allocation_weights = extract_weights_from_csv('c:/Users/tjpap/sandbox/alpaca_api/sp500_companies.csv')
    config = {
        'initial_investment': 100000,        # Initial lump-sum investment
        'recurring_investment': 1500,        # Amount to invest at regular intervals
        'investment_frequency': 'monthly',   # 'monthly' or 'bimonthly'
        'start_date': '2020-01-01',          # Start date for simulation
        'end_date': '2025-03-11',            # End date for simulation
        'tickers_source': 'c:/Users/tjpap/sandbox/alpaca_api/sp500_companies.csv',  # Path to CSV with tickers
        'top_n': 250,                        # Number of top tickers to use
        'sell_trigger': -10,                 # Percentage decline to trigger a sell
        'portfolio_allocation': allocation_weights      # Equal weight allocation
    }
    
    # Initialize and run model
    model = InvestmentForecastingModel(config)
    results = model.run_simulation()
    
    # Print report
    print(model.generate_report())
    
    # Plot portfolio growth
    plt_figure = model.plot_portfolio_growth()
    plt_figure.savefig('portfolio_growth.png')
    
    # Export results
    model.export_results('simulation_results')
    
    # Print tax-loss harvesting summary
    print("\n" + model.get_tax_loss_harvesting_summary())