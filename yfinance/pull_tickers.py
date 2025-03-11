import pandas as pd

def extract_top_tickers_from_csv(csv_file, top_n=10):
    # Read the CSV file
    csv_data = pd.read_csv(csv_file)
    
    # Sort by Weight column in descending order
    sorted_data = csv_data.sort_values('Weight', ascending=False)
    
    # Take only the top n tickers
    top_tickers = sorted_data.head(top_n)
    
    # Extract the symbols
    symbols = top_tickers['Symbol'].tolist()
    
    # Join symbols with a space for yfinance
    # tickers_string = " ".join(symbols)
    
    print(f"Selected top {len(symbols)} tickers by weight: {symbols}")
    
    return symbols

# Read the CSV file to extract the symbols and weights
# Assuming the CSV file is named 'portfolio.csv'
def extract_weights_from_csv(csv_file):
    # Read the CSV file
    csv_data = pd.read_csv(csv_file)
    
    # Create a dictionary mapping Symbol to Weight with rounded values
    weights_dict = dict(zip(csv_data['Symbol'], csv_data['Weight']))
    
    return weights_dict

# Add weights to your existing ranked DataFrame
def add_weights_to_ranked_list(ranked_df, weights_dict):
    # Create a new column for the weights
    ranked_df['Portfolio_Weight'] = ranked_df['Ticker'].map(weights_dict)
    
    # Calculate the weighted impact on the portfolio
    # ranked_df['Weighted_Impact'] = ranked_df['Percent_Change'] * ranked_df['Portfolio_Weight']
    
    # Optional: Convert weights to percentage format for better readability
    ranked_df['Portfolio_Weight'] = round(ranked_df['Portfolio_Weight'] * 100, 2)
    
    return ranked_df