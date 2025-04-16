import pandas as pd
import pytz
import datetime as dt
from datetime import date

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

    
