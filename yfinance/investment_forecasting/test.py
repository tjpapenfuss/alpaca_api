import yfinance as yf

# spy_data = yf.download(
#                 tickers='AAPL',
#                 start='2025-01-01',
#                 end='2025-03-11',
#                 interval="1d",
#                 group_by='ticker'
#             )

# prices = spy_data.xs("Close", level=1, axis=1)
# print(prices)

import pandas as pd
test = pd.read_pickle('top-50-20-22.pkl')
print(test)