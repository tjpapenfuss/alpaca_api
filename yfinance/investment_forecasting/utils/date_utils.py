from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

def generate_investment_dates(start_date, end_date, frequency='monthly'):
    """
    Generate dates for recurring investments based on frequency.
    
    Parameters:
    -----------
    start_date : str
        Start date in 'YYYY-MM-DD' format
    end_date : str
        End date in 'YYYY-MM-DD' format
    frequency : str
        'monthly' or 'bimonthly'
    
    Returns:
    --------
    list
        List of date strings
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    dates = [start]  # Start with initial investment date
    current = start
    
    # Generate recurring investment dates
    while current < end:
        if frequency == 'monthly':
            current = current + relativedelta(months=1)
        elif frequency == 'bimonthly':
            current = current + relativedelta(months=2)
        else:
            raise ValueError("Investment frequency must be 'monthly' or 'bimonthly'")
        
        if current <= end:
            dates.append(current)
            
    return [d.strftime('%Y-%m-%d') for d in dates]

def get_closest_trading_day(date_str, prices_df):
    """
    Find the closest trading day to the given date.
    
    Parameters:
    -----------
    date_str : str
        Date in 'YYYY-MM-DD' format
    prices_df : DataFrame
        DataFrame with dates as index
    
    Returns:
    --------
    str
        Closest trading day in 'YYYY-MM-DD' format or None if not found
    """
    target_date = pd.to_datetime(date_str)
    
    # Try exact date first
    if target_date in prices_df.index:
        return date_str
        
    # Look for closest date within 5 days
    for i in range(1, 6):
        # Try dates after
        forward_date = target_date + pd.Timedelta(days=i)
        if forward_date in prices_df.index:
            return forward_date.strftime('%Y-%m-%d')
            
        # Try dates before
        backward_date = target_date - pd.Timedelta(days=i)
        if backward_date in prices_df.index:
            return backward_date.strftime('%Y-%m-%d')
            
    return None

def find_closest_date(target_date, date_index):
    """
    Find the closest date in the index to the target date.
    
    Parameters:
    -----------
    target_date : datetime
        Target date
    date_index : DatetimeIndex
        Index of dates to search
    
    Returns:
    --------
    datetime
        Closest date or None if not found
    """
    # Try exact date first
    if target_date in date_index:
        return target_date
        
    # Look for closest date within 5 days
    for i in range(1, 6):
        # Try dates after
        forward_date = target_date + pd.Timedelta(days=i)
        if forward_date in date_index:
            return forward_date
            
        # Try dates before
        backward_date = target_date - pd.Timedelta(days=i)
        if backward_date in date_index:
            return backward_date
            
    return None