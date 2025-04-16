import pandas as pd
import pytz
import datetime as dt
from datetime import date, timedelta

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus

# pass the API and prevDays (0 for today, 1 since yesterday...)
def report(api, prevDays):
    #
    # get all closed orders and import them into a dataframe
    #
    orderTotal = 500
    today = dt.date.today() - dt.timedelta(days=prevDays)
    today = dt.datetime.combine(today, dt.datetime.min.time())
    today = today.strftime("%Y-%m-%dT%H:%M:%SZ")
    #print(today)

    request_params =  GetOrdersRequest(
                    status=QueryOrderStatus.ALL,
                    limit=orderTotal,
                    after=today
                )

    # orders that satisfy params
    orders = api.get_orders(filter=request_params)

    if not orders:
        return
    dfOrders = pd.DataFrame()
    temp_store = []

    for o in orders:
        # convert dot notation to dict
        d = vars(o)
        # import dict into dataframe
        # df = pd.DataFrame.from_dict(d, orient='index')
        temp_store.append(d)
        # append to dataframe
        #dfOrders = dfOrders.concat(df, ignore_index=True)

    dfOrders = pd.DataFrame(temp_store)
    print(dfOrders)
    # select filled orders with buy or sell
    dfSel = dfOrders
    # choose a subset (use .copy() as we are slicing and to avoid warning)
    dfSel = dfSel[['client_order_id', 'submitted_at', 'filled_at', 'symbol', 'filled_qty', 'side', 'type', 'filled_avg_price', 'status']].copy()
    dfSel = dfSel[~dfSel['status'].str.contains('cancel')]
    # convert filled_at to date
    dfSel['submitted_at'] = pd.to_datetime(dfSel['submitted_at'], format="%Y-%m-%d %H:%M:%S")
    dfSel['filled_at']    = pd.to_datetime(dfSel['filled_at'], format="%Y-%m-%d %H:%M:%S")
    # convert to EST
    dfSel['submitted_at'] = dfSel['submitted_at'].dt.tz_convert('America/New_York')
    dfSel['filled_at']    = dfSel['filled_at'].dt.tz_convert('America/New_York')
    # remove millis
    dfSel['submitted_at'] = dfSel['submitted_at'].dt.strftime("%Y-%m-%d %H:%M:%S")
    dfSel['filled_at']    = dfSel['filled_at'].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Sort: https://kanoki.org/2020/01/28/sort-pandas-dataframe-and-series/
    # need to sort in order to perform the proper calculations
    # sort based on the following sequence of types: market then limit, then stop_limit
    dfSel['type'] = pd.Categorical(dfSel['type'], categories=["market", "limit", "stop_limit"])
    # sort first based on symbol, then type as per the list above, then submitted date
    dfSel.sort_values(by=['symbol', 'submitted_at', 'type'], inplace=True, ascending=True)

    # reset index
    dfSel.reset_index(drop=True, inplace=True)
    # drop the 'side' column
    # dfProfit = dfSel.drop('side', 1)
    return dfSel
    # show header row
    #print(tabulate(dfSel[:0], headers='keys', tablefmt='simple', showindex=False))

    
def get_orders_v2(api, prevDays, symbols=None):

    # First set the initial end_time for the orders
    # Set to the current time so we fetch all orders up until now
    # There's a limit to the number of orders received, but by selecting
    # direction='desc' the API will fetch orders from this date BACKWARDS

    today = (dt.date.today() - dt.timedelta(days=prevDays))
    #datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Create an empty list to store our full order list
    order_list = []

    # Set the 'chunk size' to the 500 max
    CHUNK_SIZE = 500
    last_submitted = None
    while True:
        # Get the max chunk
        params = {
            "status": QueryOrderStatus.ALL,
            "limit": CHUNK_SIZE,
            "after": today,
            "direction": 'desc',
        }

        if symbols is not None:
            params["symbols"] = symbols

        request_params = GetOrdersRequest(**params)

        # orders that satisfy params
        order_chunk = api.get_orders(filter=request_params)

        if order_chunk:
            # Have orders so add to list
            order_list.extend(order_chunk)
            # Detect if stuck in a loop
            last_submitted = order_chunk[-1].submitted_at

            if order_chunk[-1].submitted_at == order_chunk[len(order_chunk)-1].submitted_at:
                today = last_submitted + dt.timedelta(days=1)  # just bump a day to break the loop
            else:
                today = last_submitted

        else:
            # No more orders. Make a dataframe of entire list of orders
            # Then exit
            order_df = pd.DataFrame([order.model_dump() for order in order_list])
            break

    return order_df