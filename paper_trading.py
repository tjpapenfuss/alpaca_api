from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus

import config

api_key = config.ALPACA_API_KEY
api_secret = config.ALPACA_API_SECRET

trading_client = TradingClient(api_key, api_secret, paper=True)

account = trading_client.get_account()

#print(account)

# market_order_data = MarketOrderRequest(
#                     symbol="SPY",
#                     qty=10,
#                     side=OrderSide.BUY,
#                     time_in_force=TimeInForce.DAY
#                     )

# # Market order
# market_order = trading_client.submit_order(
#                 order_data=market_order_data
#                )
# params to filter orders by
request_params = GetOrdersRequest(
                    status=QueryOrderStatus.OPEN,
                    side=OrderSide.SELL
                 )

# orders that satisfy params
orders = trading_client.get_orders(filter=request_params)
print(orders)

print(trading_client.get_all_positions())