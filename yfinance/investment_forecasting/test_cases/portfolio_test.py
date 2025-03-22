import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from models.portfolio import Portfolio

class TestPortfolio(unittest.TestCase):
    def setUp(self):
        # Initialize a portfolio with some test tickers
        self.tickers = ['AAPL', 'MSFT', 'GOOGL']
        self.portfolio = Portfolio(self.tickers)
        
        # Create sample price data - a DataFrame with dates as index and tickers as columns
        dates = pd.date_range(start='2023-01-01', periods=30)
        data = {}
        for ticker in self.tickers:
            # Generate some random price data
            base_price = np.random.uniform(100, 200)
            data[ticker] = [base_price + np.random.uniform(-5, 5) for _ in range(len(dates))]
        
        self.prices_df = pd.DataFrame(data, index=dates)
        
        # Format dates as strings to match with the portfolio's expected format
        self.dates = [d.strftime('%Y-%m-%d') for d in dates]
        
        # Initialize an empty list for transactions
        self.transactions = []

    def test_initialization(self):
        """Test portfolio initialization."""
        self.assertEqual(self.portfolio.cash, 0)
        self.assertEqual(len(self.portfolio.holdings), 3)
        for ticker in self.tickers:
            self.assertEqual(self.portfolio.holdings[ticker]['shares'], 0)
            self.assertEqual(self.portfolio.holdings[ticker]['cost_basis'], 0)
            self.assertEqual(len(self.portfolio.holdings[ticker]['investments']), 0)

    def test_add_cash(self):
        """Test adding cash to the portfolio."""
        initial_cash = self.portfolio.cash
        added_amount = 10000
        new_cash = self.portfolio.add_cash(added_amount)
        
        self.assertEqual(new_cash, initial_cash + added_amount)
        self.assertEqual(self.portfolio.cash, initial_cash + added_amount)

    def test_calculate_total_value_empty_portfolio(self):
        """Test calculating total value with cash only."""
        self.portfolio.add_cash(5000)
        total_value = self.portfolio.calculate_total_value(self.prices_df, self.dates[0])
        
        self.assertEqual(total_value, 5000)  # Only cash, no holdings

    def test_calculate_total_value_with_holdings(self):
        """Test calculating total value with cash and holdings."""
        self.portfolio.add_cash(10000)
        
        # Buy some shares
        date = self.dates[0]
        price = self.prices_df.loc[date, 'AAPL']
        shares = 10
        
        # Manually update holdings to simulate a purchase
        self.portfolio.holdings['AAPL']['shares'] = shares
        self.portfolio.cash -= shares * price
        
        # Calculate expected total value
        expected_value = self.portfolio.cash + (shares * price)
        actual_value = self.portfolio.calculate_total_value(self.prices_df, date)
        
        self.assertAlmostEqual(actual_value, expected_value, places=2)

    def test_buy_position(self):
        """Test buying a position."""
        self.portfolio.add_cash(10000)
        date = self.dates[0]
        ticker = 'AAPL'
        shares = 10
        price = self.prices_df.loc[date, ticker]
        
        initial_cash = self.portfolio.cash
        expected_cost = shares * price
        
        self.portfolio.buy_position(
            ticker, shares, price, date, self.transactions,
            f"Bought {shares} shares of {ticker}"
        )
        
        # Check holdings were updated
        self.assertEqual(self.portfolio.holdings[ticker]['shares'], shares)
        self.assertAlmostEqual(self.portfolio.holdings[ticker]['cost_basis'], price, places=2)
        
        # Check cash was reduced
        self.assertAlmostEqual(self.portfolio.cash, initial_cash - expected_cost, places=2)
        
        # Check transaction was recorded
        self.assertEqual(len(self.transactions), 1)
        self.assertEqual(self.transactions[0]['type'], 'buy')
        self.assertEqual(self.transactions[0]['ticker'], ticker)
        self.assertEqual(self.transactions[0]['shares'], shares)
        print(self.transactions)

    # def test_buy_position_insufficient_cash(self):
    #     """Test buying with insufficient cash."""
    #     self.portfolio.add_cash(1000)
    #     date = self.dates[0]
    #     ticker = 'AAPL'
    #     shares = 100  # Intentionally too many shares
    #     price = self.prices_df.loc[date, ticker]
        
    #     initial_cash = self.portfolio.cash
        
    #     self.portfolio.buy_position(
    #         ticker, shares, price, date, self.transactions,
    #         f"Bought {shares} shares of {ticker}"
    #     )
        
    #     # Should buy as many shares as possible with available cash
    #     expected_shares = initial_cash / price
    #     expected_shares = round(expected_shares, 2)
        
    #     # Check holdings were updated correctly
    #     self.assertAlmostEqual(self.portfolio.holdings[ticker]['shares'], expected_shares, places=2)
        
    #     # Check cash is nearly zero (accounting for rounding)
    #     self.assertLess(self.portfolio.cash, 0.01)
        
    #     # Check transaction was recorded
    #     self.assertEqual(len(self.transactions), 1)
    #     self.assertEqual(self.transactions[0]['shares'], expected_shares)

    # def test_sell_position(self):
    #     """Test selling a position."""
    #     # First buy a position
    #     self.portfolio.add_cash(10000)
    #     date_buy = self.dates[0]
    #     date_sell = self.dates[10]  # Sell 10 days later
    #     ticker = 'MSFT'
    #     shares_buy = 10
    #     price_buy = self.prices_df.loc[date_buy, ticker]
        
    #     self.portfolio.buy_position(
    #         ticker, shares_buy, price_buy, date_buy, self.transactions,
    #         f"Bought {shares_buy} shares of {ticker}"
    #     )
        
    #     # Now sell half the position
    #     shares_sell = 5
    #     price_sell = self.prices_df.loc[date_sell, ticker]
    #     initial_cash = self.portfolio.cash
        
    #     transaction = self.portfolio.sell_position(
    #         ticker, shares_sell, price_sell, date_sell, self.transactions,
    #         f"Sold {shares_sell} shares of {ticker}"
    #     )
        
    #     # Check holdings were updated
    #     self.assertEqual(self.portfolio.holdings[ticker]['shares'], shares_buy - shares_sell)
        
    #     # Check cash was increased
    #     expected_proceeds = shares_sell * price_sell
    #     self.assertAlmostEqual(self.portfolio.cash, initial_cash + expected_proceeds, places=2)
        
    #     # Check transaction was recorded
    #     self.assertEqual(len(self.transactions), 2)
    #     self.assertEqual(self.transactions[1]['type'], 'sell')
    #     self.assertEqual(self.transactions[1]['ticker'], ticker)
    #     self.assertEqual(self.transactions[1]['shares'], shares_sell)
        
    #     # Verify the gain/loss calculation
    #     expected_gain_loss = (price_sell - price_buy) * shares_sell
    #     self.assertAlmostEqual(transaction['gain_loss'], expected_gain_loss, places=2)

    def test_invest_available_cash(self):
        """Test investing available cash according to allocation weights."""
        self.portfolio.add_cash(10000)
        date = self.dates[0]
        
        # Define allocation weights
        allocation_weights = {
            'AAPL': 0.5,
            'MSFT': 0.3,
            'GOOGL': 0.2
        }
        
        self.portfolio.invest_available_cash(
            allocation_weights, self.prices_df, date, self.transactions
        )
        
        # Check that cash was invested
        self.assertLess(self.portfolio.cash, 100)  # Small amount might remain due to rounding
        
        # Check that transactions were recorded (one for each ticker)
        self.assertEqual(len(self.transactions), 3)
        
        # Check that holdings were updated according to weights
        total_investment = 0
        for ticker in self.tickers:
            total_investment += self.portfolio.holdings[ticker]['shares'] * self.prices_df.loc[date, ticker]
            
        for ticker in self.tickers:
            ticker_value = self.portfolio.holdings[ticker]['shares'] * self.prices_df.loc[date, ticker]
            ticker_weight = ticker_value / total_investment
            self.assertAlmostEqual(ticker_weight, allocation_weights[ticker], places=1)

    def test_invest_with_excluded_tickers(self):
        """Test investing with excluded tickers."""
        self.portfolio.add_cash(10000)
        date = self.dates[0]
        
        # Define allocation weights
        allocation_weights = {
            'AAPL': 0.5,
            'MSFT': 0.3,
            'GOOGL': 0.2
        }
        
        # Exclude AAPL
        excluded_tickers = ['AAPL']
        
        self.portfolio.invest_available_cash(
            allocation_weights, self.prices_df, date, self.transactions, excluded_tickers
        )
        
        # Check that no AAPL was purchased
        self.assertEqual(self.portfolio.holdings['AAPL']['shares'], 0)
        
        # Check that only 2 transactions were recorded (MSFT and GOOGL)
        self.assertEqual(len(self.transactions), 2)
        
        # Verify the remaining weights were proportionally adjusted
        # MSFT should be ~60% (0.3/0.5) and GOOGL ~40% (0.2/0.5) of the invested amount
        total_investment = 0
        for ticker in ['MSFT', 'GOOGL']:
            total_investment += self.portfolio.holdings[ticker]['shares'] * self.prices_df.loc[date, ticker]
            
        msft_value = self.portfolio.holdings['MSFT']['shares'] * self.prices_df.loc[date, 'MSFT']
        msft_weight = msft_value / total_investment
        self.assertAlmostEqual(msft_weight, 0.6, places=1)
        
        googl_value = self.portfolio.holdings['GOOGL']['shares'] * self.prices_df.loc[date, 'GOOGL']
        googl_weight = googl_value / total_investment
        self.assertAlmostEqual(googl_weight, 0.4, places=1)

    def test_track_and_manage_positions(self):
        """Test tracking and managing positions with tax-loss harvesting."""
        # Setup: Buy positions and simulate price drop
        self.portfolio.add_cash(10000)
        buy_date = self.dates[0]
        
        # Buy some shares of each ticker
        for ticker in self.tickers:
            shares = 5
            price = self.prices_df.loc[buy_date, ticker]
            self.portfolio.buy_position(
                ticker, shares, price, buy_date, self.transactions,
                f"Bought {shares} shares of {ticker}"
            )
        
        # Fast forward to a later date and manually set prices to trigger tax-loss harvesting
        sell_date = self.dates[15]  # 15 days later
        
        # Create a copy of the price DataFrame and modify it to simulate price drops
        modified_prices = self.prices_df.copy()
        
        # Reduce AAPL price by 15% to trigger tax-loss harvesting
        original_aapl_price = self.prices_df.loc[buy_date, 'AAPL']
        modified_prices.loc[sell_date, 'AAPL'] = original_aapl_price * 0.85
        
        # Keep other prices stable or slightly increased
        modified_prices.loc[sell_date, 'MSFT'] = self.prices_df.loc[buy_date, 'MSFT'] * 1.05
        modified_prices.loc[sell_date, 'GOOGL'] = self.prices_df.loc[buy_date, 'GOOGL'] * 1.02
        
        # Set the tax-loss harvesting trigger at -10%
        sell_trigger = -10
        
        # Execute the tax-loss harvesting function
        initial_transactions_count = len(self.transactions)
        _, sold_tickers = self.portfolio.track_and_manage_positions(
            modified_prices, sell_date, self.transactions, sell_trigger
        )
        
        # Check that AAPL was sold for tax-loss harvesting
        self.assertIn('AAPL', sold_tickers)
        self.assertEqual(len(sold_tickers), 1)  # Only AAPL should trigger
        
        # Check that a sell transaction was recorded
        self.assertEqual(len(self.transactions), initial_transactions_count + 1)
        self.assertEqual(self.transactions[-1]['type'], 'sell')
        self.assertEqual(self.transactions[-1]['ticker'], 'AAPL')
        
        # Verify the AAPL position was fully liquidated
        self.assertEqual(self.portfolio.holdings['AAPL']['shares'], 0)
        
        # Verify other positions were not affected
        self.assertEqual(self.portfolio.holdings['MSFT']['shares'], 5)
        self.assertEqual(self.portfolio.holdings['GOOGL']['shares'], 5)

if __name__ == '__main__':
    unittest.main()