import unittest
import pandas as pd
import numpy as np
from models.portfolio import Portfolio
import yfinance as yf
import unittest
from utils.data_loader import extract_top_tickers_from_csv, extract_weights_from_csv
from utils.data_loader import download_stock_data

GLOBAL_CSV_SPY = '/Users/tannerpapenfuss/finance_testing/alpaca_api/sp500_companies.csv'
GLOBAL_TOP_N = 5

class TestPortfolio(unittest.TestCase):
    # Class variables to store data that's shared across all test methods
    stock_data = None
    tickers = None
    prices_df = None
    start_date = '2023-01-01'
    end_date = '2024-01-01'
    config = {
        'initial_investment': 100000,
        'recurring_investment': 3000,
        'rebalance_frequency': 'monthly',
        'start_date': '2023-01-01',
        'end_date': '2024-01-01',
        'sell_trigger': -10,
        'rebalance_threshold':5.0,  # 5% threshold for rebalancing
        'portfolio_allocation':'equal',
        'tickers_source': GLOBAL_CSV_SPY,  # Path to CSV with tickers
        'top_n': GLOBAL_TOP_N
    }

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all test methods in the class."""
        # Extract tickers
        cls.tickers = extract_top_tickers_from_csv(
            GLOBAL_CSV_SPY, 
            top_n=GLOBAL_TOP_N
        )
        
        # Download stock data once
        valid_tickers, cls.stock_data = download_stock_data(cls.tickers, cls.start_date, cls.end_date)
        
        # Create price dataframe
        if "Close" in cls.stock_data.columns.levels[1]:
            cls.prices_df = cls.stock_data.xs("Close", level=1, axis=1)
        else:
            print("Error: 'Close' columns found in data.")
            cls.prices_df = pd.DataFrame()  # Empty DataFrame as fallback
            
        # Ensure all dates are datetime
        cls.prices_df.index = pd.to_datetime(cls.prices_df.index)
        
    def setUp(self):
        """Set up test fixtures before each test method."""
        
        # Create a test portfolio with the class-level tickers
        self.portfolio = Portfolio(
            rebalance_frequency=self.config['rebalance_frequency'],
            rebalance_threshold=self.config['rebalance_threshold'],
            portfolio_allocation=self.config['portfolio_allocation'],
            tickers=self.__class__.tickers
        )
        
        # Initialize holdings
        self.portfolio.initialize_holdings(self.__class__.tickers)
        
        # Add initial cash
        self.portfolio.add_cash(10000)
        
        # Create empty transactions list
        self.transactions = []

    def test_add_cash(self):
        """Test adding cash to the portfolio."""
        initial_cash = self.portfolio.cash
        added_amount = 5000
        new_cash = self.portfolio.add_cash(added_amount)
        
        self.assertEqual(new_cash, initial_cash + added_amount)
        self.assertEqual(self.portfolio.cash, initial_cash + added_amount)

    def test_calculate_total_value(self):
        """Test calculating the total portfolio value."""
        # Add some holdings first
        date = self.__class__.prices_df.index[0]
        price = self.__class__.prices_df.loc[date, 'AAPL']
        
        # Buy some shares
        self.portfolio.buy_position(
            'AAPL', 10, price, date, self.transactions, "Test purchase"
        )
        
        # Calculate expected value
        expected_value = self.portfolio.cash + (10 * price)
        actual_value = self.portfolio.calculate_total_value(self.__class__.prices_df, date)
        
        self.assertAlmostEqual(actual_value, expected_value, places=2)

    def test_calculate_allocation_weights_equal(self):
        """Test calculating equal allocation weights."""
        weights = self.portfolio.calculate_allocation_weights()
        expected_weight = 1.0 / len(self.tickers)
        
        for ticker in self.tickers:
            self.assertAlmostEqual(weights[ticker], expected_weight, places=4)
            
    def test_calculate_allocation_weights_custom(self):
        """Test calculating custom allocation weights."""
        # Set custom allocation
        custom_allocation = extract_weights_from_csv(GLOBAL_CSV_SPY, GLOBAL_TOP_N)

        self.portfolio.portfolio_allocation = custom_allocation
        
        # Adjust allocation weights to exclude tickers that were just sold
        adjusted_weights = custom_allocation.copy()
                        
        # Normalize remaining weights to sum to 1
        weight_sum = sum(adjusted_weights.values())
        if weight_sum > 0:  # Avoid division by zero
            adjusted_weights = {k: float(f"{(v/weight_sum):.4f}") for k, v in adjusted_weights.items()}

        weights = self.portfolio.calculate_allocation_weights()
        for ticker in self.tickers:
            self.assertAlmostEqual(weights[ticker], adjusted_weights[ticker], places=4)

    def test_buy_position(self):
        """Test buying a position."""
        date = self.__class__.prices_df.index[0]
        price = self.__class__.prices_df.loc[date, 'AAPL']
        shares = 10
        initial_cash = self.portfolio.cash
        
        self.portfolio.buy_position(
            'AAPL', shares, price, date, self.transactions, "Test purchase"
        )
        
        # Check if shares were added
        self.assertEqual(self.portfolio.holdings['AAPL']['shares'], shares)
        
        # Check if cost basis was calculated correctly
        self.assertAlmostEqual(self.portfolio.holdings['AAPL']['cost_basis'], price, places=2)
        
        # Check if cash was reduced
        self.assertAlmostEqual(self.portfolio.cash, initial_cash - (shares * price), places=2)
        
        # Check if transaction was recorded
        self.assertEqual(len(self.transactions), 1)
        self.assertEqual(self.transactions[0]['type'], 'buy')
        self.assertEqual(self.transactions[0]['ticker'], 'AAPL')
        self.assertEqual(self.transactions[0]['shares'], shares)

    def test_sell_position(self):
        """Test selling a position."""
        # First buy a position
        date = self.__class__.prices_df.index[0]
        buy_price = self.__class__.prices_df.loc[date, 'AAPL']
        shares = 10
        
        self.portfolio.buy_position(
            'AAPL', shares, buy_price, date, self.transactions, "Test purchase"
        )
        
        # Move to a future date for selling
        sell_date = self.__class__.prices_df.index[30]  # 30 days later
        sell_price = self.__class__.prices_df.loc[sell_date, 'AAPL']
        initial_cash = self.portfolio.cash
        
        transaction = self.portfolio.sell_position(
            'AAPL', shares, sell_price, sell_date, self.transactions, "Test sale"
        )
        
        # Check if shares were removed
        self.assertEqual(self.portfolio.holdings['AAPL']['shares'], 0)
        
        # Check if cash was increased
        self.assertAlmostEqual(self.portfolio.cash, initial_cash + (shares * sell_price), places=2)
        
        # Check if transaction was recorded
        self.assertEqual(self.transactions[-1]['type'], 'sell')
        self.assertEqual(self.transactions[-1]['ticker'], 'AAPL')
        self.assertEqual(self.transactions[-1]['shares'], shares)
        
        # Check if gain/loss was calculated
        expected_gain_loss = (sell_price - buy_price) * shares
        self.assertAlmostEqual(transaction['gain_loss'], expected_gain_loss, places=2)

    def test_partial_sell(self):
        """Test selling part of a position."""
        # First buy a position
        date = self.__class__.prices_df.index[0]
        buy_price = self.__class__.prices_df.loc[date, 'AAPL']
        shares = 10
        
        self.portfolio.buy_position(
            'AAPL', shares, buy_price, date, self.transactions, "Test purchase"
        )
        
        # Sell half the position
        sell_date = self.__class__.prices_df.index[30]
        sell_price = self.__class__.prices_df.loc[sell_date, 'AAPL']
        shares_to_sell = 5
        
        transaction = self.portfolio.sell_position(
            'AAPL', shares_to_sell, sell_price, sell_date, self.transactions, "Test partial sale"
        )
        
        # Check if correct number of shares remain
        self.assertEqual(self.portfolio.holdings['AAPL']['shares'], shares - shares_to_sell)

    def test_invest_available_cash(self):
        """Test investing available cash according to allocation."""
        date = self.__class__.prices_df.index[0]
        allocation_weights = extract_weights_from_csv(GLOBAL_CSV_SPY, GLOBAL_TOP_N)
        initial_cash = self.portfolio.cash
        
        self.portfolio.invest_available_cash(
            allocation_weights, self.__class__.prices_df, date, self.transactions
        )
        # print(self.transactions)
        # Check if cash was fully invested (with possible small remainder)
        self.assertLess(self.portfolio.cash, 50)  # Less than $50 remaining
        self.assertGreater(self.portfolio.cash, 0)  # Did not go negative
        
        # Check if holdings were created for each ticker
        for ticker in self.tickers:
            self.assertGreater(self.portfolio.holdings[ticker]['shares'], 0)
            
        # Check if transactions were recorded
        self.assertEqual(len(self.transactions), GLOBAL_TOP_N)  # One transaction per ticker

    def test_portfolio_history(self):
        """Test tracking portfolio history."""
        date = self.__class__.prices_df.index[0]
        
        # Invest cash
        allocation_weights = extract_weights_from_csv(GLOBAL_CSV_SPY, GLOBAL_TOP_N)
        self.portfolio.invest_available_cash(
            allocation_weights, self.__class__.prices_df, date, self.transactions
        )
        
        # Update portfolio history
        self.portfolio.update_portfolio_history(self.__class__.prices_df, date)
        
        # Check if history was recorded
        self.assertEqual(len(self.portfolio.portfolio_history), 1)
        self.assertEqual(self.portfolio.portfolio_history[0]['date'], date)
        self.assertGreater(self.portfolio.portfolio_history[0]['investments_value'], 0)

    def test_rebalance(self):
        """Test portfolio rebalancing."""
        # First invest some cash
        initial_date = self.__class__.prices_df.index[0]
        allocation_weights = extract_weights_from_csv(GLOBAL_CSV_SPY, GLOBAL_TOP_N)
        
        self.portfolio.invest_available_cash(
            allocation_weights, self.__class__.prices_df, initial_date, self.transactions
        )
        
        # Add more cash to trigger rebalance
        self.portfolio.add_cash(5000)
        
        # Move to a future date for rebalancing
        rebalance_date = self.__class__.prices_df.index[89]  # 90 days later
        excluded_tickers = []
        
        # Record pre-rebalance values
        pre_holdings = {t: h['shares'] for t, h in self.portfolio.holdings.items()}
        
        # Perform rebalance
        self.portfolio.check_and_rebalance(
            self.__class__.prices_df, rebalance_date, rebalance_date, initial_date, 
            self.transactions, None, excluded_tickers
        )
        
        # Check if rebalance was performed (transactions should be added)
        self.assertGreater(len(self.transactions), GLOBAL_TOP_N)  # More than the initial investments
        
        # Check that cash was reinvested
        self.assertLess(self.portfolio.cash, 50)  # Less than $50 remaining
        print(self.transactions)

    def test_tax_loss_harvesting(self):
        """Test tax-loss harvesting functionality."""
        # First buy some positions
        date = self.__class__.prices_df.index[0]
        for ticker in self.tickers:
            price = self.__class__.prices_df.loc[date, ticker]
            self.portfolio.buy_position(
                ticker, 10, price, date, self.transactions, f"Buy {ticker}"
            )
        # Manually adjust one investment's return to trigger tax-loss harvesting
        self.portfolio.holdings['AAPL']['investments'][0]['cost'] = \
            self.portfolio.holdings['AAPL']['investments'][0]['cost'] * 1.15  # 15% loss
        
        # Set a sell trigger of -10%
        sell_trigger = -10
        
        # Track and manage positions
        future_date = self.__class__.prices_df.index[30]
        transactions_count_before = len(self.transactions)
        
        self.portfolio.track_and_manage_positions(
            self.__class__.prices_df, future_date, self.transactions, sell_trigger
        )

        # Check if a tax-loss harvesting sale was triggered
        self.assertGreater(len(self.transactions), transactions_count_before)
        self.assertEqual(self.transactions[-1]['type'], 'sell')
        self.assertEqual(self.transactions[-1]['ticker'], 'AAPL')
        self.assertTrue('tax-loss harvesting' in self.transactions[-1]['description'])

if __name__ == '__main__':
    unittest.main()
