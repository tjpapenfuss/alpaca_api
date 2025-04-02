import yfinance as yf
import json
from utils.data_loader import extract_top_tickers_from_csv

spy_data = yf.download(
                tickers='SPY',
                start='2018-01-01',
                end='2025-04-01',
                interval="1d",
                group_by='ticker'
            )

spy_data.to_pickle('spy-18-25.pkl')

tickers_source='/Users/tannerpapenfuss/finance_testing/alpaca_api/yfinance/investment_forecasting/sp500_companies.csv'

# Get tickers from configuration
tickers = extract_top_tickers_from_csv(
    csv_file=tickers_source, 
    top_n=500
)

ticker_50 = yf.download(
                tickers=tickers,
                start='2018-01-01',
                end='2025-04-01',
                interval="1d",
                group_by='ticker'
            )

ticker_50.to_pickle('top-500-18-25.pkl')
