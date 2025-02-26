import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import time
import config

api_key = config.ALPACA_API_KEY
api_secret = config.ALPACA_API_SECRET

trading_client = TradingClient(api_key, api_secret, paper=True)

account = trading_client.get_account()

# Use the Kaggle dataset. https://www.kaggle.com/datasets/andrewmvd/sp-500-stocks?resource=download

# Read the CSV file into a DataFrame
df = pd.read_csv('sp500_companies.csv')

# Select a reduced set of columns
reduced_df = df[['Symbol', 'Weight']][15:20]

# Print the reduced DataFrame
# print(reduced_df)

for index, row in reduced_df.iterrows():
    # Error handling for invalid symbols or insufficient funds
    try:
        # Create a market order request. This pulls the symbol and nortional from the S&P500 dataset
        market_order_data = MarketOrderRequest(
                            symbol=row['Symbol'],
                            notional=round(row['Weight']*10000, 2),
                            side=OrderSide.BUY,
                            time_in_force=TimeInForce.DAY
                            )

        # Market order submission. 
        market_order = trading_client.submit_order(
                        order_data=market_order_data
                    )
        print(row['Symbol'], row['Weight']*10000)
        # print(market_order)
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)

