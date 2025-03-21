#from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd

def generate_investment_dates(start_date, end_date, frequency='monthly'):
    """
    Generate dates for recurring investments based on frequency.
    """    
    dates = [start_date]  # Start with initial investment date
    current = start_date
    
    # Generate recurring investment dates
    while current < end_date:
        if frequency == 'monthly':
            current = current + relativedelta(months=1)
        elif frequency == 'bimonthly':
            current = current + relativedelta(months=0.5)
        else:
            raise ValueError("Investment frequency must be 'monthly' or 'bimonthly'")
        
        if current <= end_date:
            dates.append(current)
            
    investment_dates = [d.strftime('%Y-%m-%d') for d in dates]
    return investment_dates
    
def get_closest_trading_day(date_str, prices_df):
    """
    Find the closest trading day to the given date.
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