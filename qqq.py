import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import time
import config
import math

api_key = config.QQQ_API_KEY
api_secret = config.QQQ_API_SECRET
TOTAL_PORTFOLIO_VALUE = 495000

trading_client = TradingClient(api_key, api_secret, paper=True)

account = trading_client.get_account()

# Use the Kaggle dataset. https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks?resource=download

# Read the CSV file into a DataFrame
df = pd.read_csv('QQQ.csv')

# Select a reduced set of columns
reduced_df = df[['Holding Ticker', 'Weight']]

# half the portfolio in individual stocks. The other half in SPY ETF.
# market_order_data = MarketOrderRequest(
#                     symbol="SPY",
#                     notional=TOTAL_PORTFOLIO_VALUE/2,
#                     side=OrderSide.BUY,
#                     time_in_force=TimeInForce.DAY
#                     )

# # Market order submission for SPY ETF. 
# market_order = trading_client.submit_order(
#                 order_data=market_order_data
#             )
# print(f"Purchased SPY ETF for {TOTAL_PORTFOLIO_VALUE/2}")
for index, row in reduced_df.iterrows():
    # Error handling for invalid symbols or insufficient funds
    try:
        stock_symbol = row['Holding Ticker'].strip()
        # half the portfolio in individual stocks. The other half in SPY ETF. 
        stock_notional_purchase = math.floor((row['Weight']*TOTAL_PORTFOLIO_VALUE*0.01))
        # stock_notional_purchase = round((row['Weight']*TOTAL_PORTFOLIO_VALUE)/2, 2)
        # Create a market order request. This pulls the symbol and nortional from the S&P500 dataset
        market_order_data = MarketOrderRequest(
                            symbol=stock_symbol,
                            notional=stock_notional_purchase,
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY
                            )

        # Market order submission. 
        market_order = trading_client.submit_order(
                        order_data=market_order_data
                    )
        print(f"Purchased {stock_symbol} for {stock_notional_purchase}")
        # print(market_order)
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)

