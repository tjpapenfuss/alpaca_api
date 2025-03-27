# Investment Forecast Model

A Python-based investment simulation framework for backtesting investment strategies and tax-loss harvesting.

## Overview

Investment Forecast Model allows you to simulate investment strategies with customizable parameters. It supports:

- Lump sum and recurring investments
- Portfolio allocation strategies
- Tax-loss harvesting simulation
- Performance comparison against benchmarks
- Detailed reporting and visualization

This model is especially useful for analyzing the benefits of tax-loss harvesting strategies across different market conditions.

## Project Structure

```
investment_forecast/
├── config/          # Configuration management
├── models/          # Core simulation models
├── output/          # Output files from most recent run of main.py investment forcasting.
├── pickle_files/    # Sample outputs from yfinance to limit calling yfinance too many times. 
├── reporting/       # Helper files to create visuals for reporting on model runs
├── strategies/      # Investment strategies implementation
├── test_cases/      # House all test cases. Currently tests are located in portfolio_test.py
└── utils/           # Helper utilities
```

## Installation

1. Clone the repository
```bash
git clone https://github.com/username/investment-forecast.git
cd investment-forecast
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

## Required Dependencies

- pandas
- numpy
- yfinance
- matplotlib
- dateutil

## Basic Usage

```python
from investment_forecast import InvestmentForecastingModel

# Define your configuration
config = {
    'initial_investment': 100000,        # Initial lump-sum investment
    'recurring_investment': 1500,        # Amount to invest at regular intervals
    'investment_frequency': 'monthly',   # 'monthly' or 'bimonthly'
    'start_date': '2020-01-01',          # Start date for simulation
    'end_date': '2023-01-01',            # End date for simulation
    'tickers_source': 'sp500_companies.csv',  # Path to CSV with tickers
    'top_n': 250,                        # Number of top tickers to use
    'sell_trigger': -10,                 # Percentage decline to trigger a sell
    'portfolio_allocation': 'equal'      # Equal weight allocation
}

# Initialize and run model
model = InvestmentForecastingModel(config)
results = model.run_simulation()

# Generate and print report
print(model.generate_report())

# Plot portfolio growth
plt_figure = model.plot_portfolio_growth()
plt_figure.savefig('portfolio_growth.png')

# Export detailed results
model.export_results('simulation_results')

# View tax-loss harvesting summary
print(model.get_tax_loss_harvesting_summary())
```

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `initial_investment` | Initial lump sum investment amount | 10000 |
| `recurring_investment` | Amount to invest at regular intervals | 1000 |
| `investment_frequency` | Frequency of investments ('monthly' or 'bimonthly') | 'monthly' |
| `start_date` | Start date for the analysis (YYYY-MM-DD) | '2023-01-01' |
| `end_date` | End date for the analysis (YYYY-MM-DD) | '2024-01-01' |
| `tickers_source` | Path to CSV file with tickers or list of tickers | None |
| `top_n` | Number of top tickers to use (if using CSV) | 250 |
| `sell_trigger` | Percentage decline to trigger a sell (-10 means sell at 10% loss) | -10 |
| `portfolio_allocation` | Dict of ticker to weight or 'equal' | 'equal' |

## Custom Portfolio Allocation

You can specify custom allocation weights in three ways:

1. Equal weight allocation (default)
```python
config['portfolio_allocation'] = 'equal'
```

2. Custom weights as a dictionary
```python
config['portfolio_allocation'] = {
    'AAPL': 0.25,
    'MSFT': 0.25,
    'AMZN': 0.25,
    'GOOGL': 0.25
}
```

3. Weights from a CSV file
```python
config['portfolio_allocation'] = 'weights.csv'
```

The CSV file should have columns for ticker symbols and weights.

## Advanced Usage

### Custom Tax-Loss Harvesting Strategy

You can customize the tax-loss harvesting strategy by adjusting the `sell_trigger` parameter:

```python
# More aggressive tax-loss harvesting (sell at 5% loss)
config['sell_trigger'] = -5

# Less aggressive tax-loss harvesting (sell at 15% loss)
config['sell_trigger'] = -15
```

### Performance Analysis

The model provides detailed performance metrics:

```python
# Run simulation
model = InvestmentForecastingModel(config)
results = model.run_simulation()

# Access performance metrics
metrics = model.performance_metrics
print(f"Total Return: {metrics['total_return_pct']:.2f}%")
print(f"Annualized Return: {metrics['annualized_return']:.2f}%")
print(f"Estimated Tax Savings: ${metrics['tax_savings_estimate']:,.2f}")
```

### Portfolio History Analysis

You can analyze the portfolio history over time:

```python
# Get portfolio history as a pandas DataFrame
portfolio_df = model.portfolio_history

# Analyze monthly returns
monthly_returns = portfolio_df.set_index('date')['total_value'].pct_change()
print(f"Average Monthly Return: {monthly_returns.mean() * 100:.2f}%")
print(f"Monthly Volatility: {monthly_returns.std() * 100:.2f}%")
```

## Reporting

The model generates several reports:

1. **Performance Summary**: Overall metrics of the simulation
2. **Tax-Loss Harvesting Summary**: Details of tax-loss harvesting transactions
3. **CSV Exports**: Detailed transaction and portfolio history data
4. **Visualization**: Portfolio growth charts comparing against benchmark indices

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
