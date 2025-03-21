# Default configuration settings
DEFAULT_CONFIG = {
    'initial_investment': 100000,
    'recurring_investment': 3000,
    'investment_frequency': 'monthly',
    'start_date': '2023-01-01',
    'end_date': '2024-01-01',
    'sell_trigger': -10,
    'tickers_source': 'c:/Users/tjpap/sandbox/alpaca_api/sp500_companies.csv',  # Path to CSV with tickers
    'top_n': 250
}

def validate_config(config):
    """Validate configuration parameters."""
    # Validation logic here
    return config