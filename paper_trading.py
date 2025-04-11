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

def extract_order_data(orders_data_string):
    """
    Extract symbol, filled price, and quantity of shares from order data string.
    
    Args:
        orders_data_string (str): String representation of order data
    
    Returns:
        list: List of tuples containing (symbol, filled_avg_price, filled_qty, notional)
    """
    import re
    
    results = []
    
    # Find all order entries in the data
    # Looking for symbol, filled_avg_price, filled_qty, and notional
    pattern = r"'symbol': '([^']+)'.*?'filled_avg_price': '([^']+)'.*?'filled_qty': '([^']+)'.*?'notional': '([^']+)'"
    
    # Find all matches in the data
    matches = re.findall(pattern, orders_data_string, re.DOTALL)
    
    # Process each match
    for match in matches:
        symbol = match[0]
        filled_avg_price = float(match[1])
        filled_qty = float(match[2])
        notional = float(match[3])
        
        results.append((symbol, filled_avg_price, filled_qty, notional))
    
    return results

if __name__ == '__main__':
    api_key = config.ALPACA_API_KEY
    api_secret = config.ALPACA_API_SECRET

    trading_client = TradingClient(api_key, api_secret, paper=True)

    account = trading_client.get_account()

    client_order_id=str(uuid.uuid4())

    market_order_data = MarketOrderRequest(
                        symbol="SPY",
                        notional=10,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY,
                        client_order_id=client_order_id
                        )

    # Market order
    market_order = trading_client.submit_order(
                    order_data=market_order_data
                    )
    print(f"Executed a {market_order.side} of {market_order.symbol} for {market_order.notional} dollars for {market_order.filled_qty} shares")
    time.sleep(1)
    est = pytz.timezone('US/Eastern')

    my_order = trading_client.get_order_by_client_id(client_id=client_order_id)
    if my_order.filled_at != None:
        timestamp = my_order.filled_at.astimezone(est).strftime("%m/%d/%Y, %H:%M:%S")
    else:
        print(f"Error adding Time.")
        timestamp = "Not Executed"
        
    #datetime.fromtimestamp(my_order.filled_at)
    
    #print(my_order)
    print(f"Executed a {my_order.side} at {timestamp} EST of {my_order.symbol} for {my_order.notional} dollars," +\
            f" {my_order.filled_qty} shares.")
    print(f"Order ID: {client_order_id}")
    print(my_order)
   # params to filter orders by
   # request_params =  GetOrdersRequest(
   #                   status=QueryOrderStatus.CLOSED,
   #                   side=OrderSide.BUY
   #                )

   # orders that satisfy params
   #orders = trading_client.get_orders(filter=request_params)
   # print(orders.symbol)

   # Example usage:
   # Assuming 'orders_data' contains the list of order dictionaries from your data
   # orders_data = [...]  # Your list of order dictionaries
   #print(orders)
   # Extract the data
   # extracted_data = extract_order_data(orders)

   # # Print the results in a more readable format
   # print("Symbol | Filled Price | Quantity")
   # print("-" * 40)
   # for symbol, price, qty in extracted_data:
   #    print(f"{symbol:<6} | ${price:<11.2f} | {qty:.8f}")

   # # Calculate total investment
   # total_investment = sum(price * qty for _, price, qty in extracted_data)
   # print(f"\nTotal Investment: ${total_investment:.2f}")

   # print(trading_client.get_all_positions())
   # print("Market Order")
   # print(market_order)
   # print("MO Data")
   # print(market_order_data)
   # print(f"My quanty is {market_order.filled_qty}")
   # print(f"My stock is {market_order.symbol}")