from alpaca.data.requests import StockLatestQuoteRequest# Create stock historical data client

import config

from alpaca.data.historical import CryptoHistoricalDataClient, OptionHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Get the API key and secret from the config file
api_key = config.ALPACA_API_KEY
api_secret = config.ALPACA_API_SECRET

# no keys required for crypto data
crypto_client = CryptoHistoricalDataClient()
# keys required
stock_client = StockHistoricalDataClient(api_key, api_secret)
option_client = OptionHistoricalDataClient(api_key, api_secret)

# multi symbol request - single symbol is similar
multisymbol_request_params = StockLatestQuoteRequest(symbol_or_symbols=["SPY", "MSFT", "GOOG"])

latest_multisymbol_quotes = stock_client.get_stock_latest_quote(multisymbol_request_params)

gld_latest_ask_price = latest_multisymbol_quotes["GOOG"].ask_price

#print(gld_latest_ask_price)
#print(latest_multisymbol_quotes)

request_params = StockBarsRequest(
    symbol_or_symbols=["MSFT"],
    timeframe=TimeFrame.Day,
    start="2025-02-01"
)

bars = stock_client.get_stock_bars(request_params)

print(bars.df)

# request_params = CryptoBarsRequest(
#                         symbol_or_symbols=["BTC/USD", "ETH/USD"],
#                         timeframe=TimeFrame.Day,
#                         start="2022-07-01"
#                  )

# bars = client.get_crypto_bars(request_params)