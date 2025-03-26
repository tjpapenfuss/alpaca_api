from models.investment_model import InvestmentForecastingModel
import pandas as pd

# Function to run a simulation from a configuration file
def run_investment_simulation(config_file=None, config_dict=None):
    """
    Run an investment simulation from a configuration file or dictionary.
    
    Parameters:
    -----------
    config_file : str, optional
        Path to configuration file (JSON, YAML, etc.)
    config_dict : dict, optional
        Configuration dictionary
        
    Returns:
    --------
    dict
        Simulation results
    """
    # Load configuration from file if provided
    if config_file is not None:
        import json        
        # Determine file type and load accordingly
        if config_file.endswith('.json'):
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration file format: {config_file}")
    elif config_dict is not None:
        config = config_dict
    else:
        # Use default configuration
        from config.settings import DEFAULT_CONFIG
        config = DEFAULT_CONFIG
    
    # Create model and run simulation
    model = InvestmentForecastingModel(config)
    results = model.run_simulation()
    
    return results

if __name__ == '__main__':
    # Run with a config file
    config_file='/home/tanner/Desktop/finance_test/alpaca_api/yfinance/investment_forecasting/config/config.json'

    results = run_investment_simulation(config_file=config_file)

    print("Results are in")
    port_df = pd.DataFrame(results['portfolio'])
    port_df.to_csv('/home/tanner/Desktop/finance_test/alpaca_api/yfinance/investment_forecasting/output/portfolio.csv', index=False)
    transaction_df = pd.DataFrame(results['transactions'])
    transaction_df.to_csv('/home/tanner/Desktop/finance_test/alpaca_api/yfinance/investment_forecasting/output/transactions.csv', index=False)
    history_df = pd.DataFrame(results['portfolio_history'])
    history_df.to_csv('/home/tanner/Desktop/finance_test/alpaca_api/yfinance/investment_forecasting/output/history.csv', index=False)
    print("metrics")
    print(results['performance_metrics'])