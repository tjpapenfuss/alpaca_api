from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, GetOrderByIdRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
from datetime import datetime
import time
import pytz
import config
import uuid

if __name__ == '__main__':
    api_key = config.ALPACA_API_KEY
    api_secret = config.ALPACA_API_SECRET
    trading_client = TradingClient(api_key, api_secret, paper=True)
    # Get our position in AAPL.
    aapl_position = trading_client.get_open_position('AAPL')
    print(aapl_position)

# NEXT UP: Need to fina all my positions and all the orders for that postion to hydrate my Database. 

    # Get a list of all of our positions.
    # portfolio = trading_client.get_all_positions()

    # # Print the quantity of shares for each position.
    # for position in portfolio:
    #     print("{} shares of {}".format(position.qty, position.symbol))

    # params to filter orders by
    request_params =  GetOrdersRequest(
                     status=QueryOrderStatus.CLOSED,
                     side=OrderSide.BUY
                  )

    # orders that satisfy params
    orders = trading_client.get_orders(filter=request_params)
    # for order in orders:
    #     print(f"Executed a {order.client_order_id} of {order.symbol} for {order.notional} dollars for {order.filled_qty} shares")
    print(orders)