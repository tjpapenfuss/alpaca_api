
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import config
import json 
from datetime import date, timedelta

from SQL_scripts.buy_sell import insert_orders
from trading.trade_report import report
from utils.stock_data import get_stock_data




if __name__ == '__main__':
    api_key = config.ALPACA_API_KEY
    api_secret = config.ALPACA_API_SECRET
    trading_client = TradingClient(api_key, api_secret, paper=True)
    # df = report(api=trading_client, prevDays=30)
    # insert_orders(df=df, db_config=config.db_config)

    today = date.today().strftime("%Y-%m-%d")
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    prices_df = get_stock_data(start_date=yesterday,
                               end_date=today,
                               tickers_source=config.yfinance_config.get('tickers_source'),
                               top_n=config.yfinance_config.get('top_n'))
    print(prices_df)
