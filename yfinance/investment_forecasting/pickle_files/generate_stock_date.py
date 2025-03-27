import yfinance as yf
import json
from utils.data_loader import extract_top_tickers_from_csv

# spy_data = yf.download(
#                 tickers='SPY',
#                 start='2020-01-01',
#                 end='2022-01-01',
#                 interval="1d",
#                 group_by='ticker'
#             )

# spy_data.to_pickle('spy-20-22.pkl')

tickers_source='/Users/tannerpapenfuss/finance_testing/alpaca_api/yfinance/investment_forecasting/sp500_companies.csv'

# Get tickers from configuration
tickers = extract_top_tickers_from_csv(
    csv_file=tickers_source, 
    top_n=50
)

ticker_50 = yf.download(
                tickers=tickers,
                start='2020-01-01',
                end='2022-01-01',
                interval="1d",
                group_by='ticker'
            )

ticker_50.to_pickle('top-50-20-22.pkl')
