from models.investment_model import InvestmentForecastingModel
import pandas as pd
import json
from datetime import datetime
from reporting.growth_viz import plot_results

GLOBAL_FOLDER_LOCATION = "/Users/tannerpapenfuss/finance_testing/alpaca_api/yfinance/investment_forecasting/"

# Function to run a simulation from a configuration file
def run_investment_simulation(config_file=None, config_dict=None, simulation='top_n'):
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
    if simulation is not 'spy_sim':
        results = model.run_simulation()
    else:
        results = model.spy_simulation()
    
    return results

if __name__ == '__main__':
    # Run with a config file
    config_file = f'{GLOBAL_FOLDER_LOCATION}config/config.json'
    spy_config = f'{GLOBAL_FOLDER_LOCATION}config/spy_config.json'

    error = False

    try:
        results = run_investment_simulation(config_file=config_file, simulation='top_n')
        port_df = pd.DataFrame(results['portfolio'])
        port_df.to_csv(f'{GLOBAL_FOLDER_LOCATION}output/portfolio.csv', index=False)
        transaction_df = pd.DataFrame(results['transactions'])
        transaction_df.to_csv(f'{GLOBAL_FOLDER_LOCATION}output/transactions.csv', index=False)
        history_df = pd.DataFrame(results['portfolio_history'])
        history_df['date'] = history_df['date'].apply(lambda x: datetime.strptime(x[:], '%Y-%m-%d'))
        history_df.to_csv(f'{GLOBAL_FOLDER_LOCATION}output/history.csv', index=False)
        print("metrics TOP N")
        print(results['performance_metrics'])
    except Exception as e:
        print(f"Error adding Top N benchmark: {e}")
        error = True

    # Download SPY data for benchmark
    try:
        # Create model and run simulation
        spy_results = run_investment_simulation(config_file=spy_config, simulation='spy_sim')
        spy_history_df = pd.DataFrame(spy_results['portfolio_history'])

        spy_history_df['date'] = spy_history_df['date'].apply(lambda x: datetime.strptime(x[:], '%Y-%m-%d'))
        print("metrics SPY")
        print(spy_results['performance_metrics'])
    except Exception as e:
        print(f"Error adding SPY benchmark: {e}")
        error = True
    
    if error is not True:
        # Now plot the results
        plot_results(top_n_df=history_df, spy_df=spy_history_df)
