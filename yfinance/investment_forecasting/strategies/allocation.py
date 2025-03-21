from ..utils.data_loader import extract_weights_from_csv

def calculate_allocation_weights(tickers, portfolio_allocation, csv_path=None):
    """
    Calculate allocation weights for the portfolio.
    
    Args:
        tickers (list): List of ticker symbols
        portfolio_allocation: 'equal', dict of weights, or path to CSV
        csv_path (str, optional): Path to CSV file with weights
        
    Returns:
        dict: Mapping of tickers to their allocation weights
    """
    if portfolio_allocation == 'equal':
        # Equal weight allocation
        weight = 1.0 / len(tickers)
        return {ticker: weight for ticker in tickers}
    elif isinstance(portfolio_allocation, dict):
        # User-provided weights
        # Normalize to ensure weights sum to 1
        total_weight = sum(portfolio_allocation.values())
        return {t: w/total_weight for t, w in portfolio_allocation.items() if t in tickers}
    elif isinstance(portfolio_allocation, str) and portfolio_allocation.endswith('.csv'):
        # Load weights from CSV
        try:
            weights_dict = extract_weights_from_csv(csv_file=csv_path)
            # Filter for only our tickers and normalize
            filtered_weights = {t: weights_dict.get(t, 0) for t in tickers}
            total_weight = sum(filtered_weights.values())
            if total_weight > 0:
                return {t: w/total_weight for t, w in filtered_weights.items()}
            else:
                # Fall back to equal weight if no weights found
                weight = 1.0 / len(tickers)
                return {ticker: weight for ticker in tickers}
        except Exception as e:
            print(f"Error loading weights from CSV: {e}")
            # Fall back to equal weight
            weight = 1.0 / len(tickers)
            return {ticker: weight for ticker in tickers}