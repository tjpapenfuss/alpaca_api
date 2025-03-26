import pandas as pd
import matplotlib.pyplot as plt
import models.portfolio as Portfolio

def record_gains_losses(lot_gain_loss, days_held, portfolio: Portfolio):
    """
    Record gains and losses for tax purposes.
    """
    if days_held < 365 and lot_gain_loss <= 0:
        portfolio.short_term_realized_losses += lot_gain_loss
    elif days_held >= 365 and lot_gain_loss <= 0:
        portfolio.long_term_realized_losses += lot_gain_loss
    elif days_held < 365 and lot_gain_loss > 0:
        portfolio.short_term_realized_gains += lot_gain_loss
    elif days_held >= 365 and lot_gain_loss > 0:
        portfolio.long_term_realized_gains += lot_gain_loss
    else:
        print("Error: Could not determine gain/loss type.")

def generate_report(model):
    """
    Generate a summary report of the simulation.
    """
    # Implementation...
    
def plot_portfolio_growth(portfolio_history, transactions):
    """
    Plot the portfolio growth over time with SPY benchmark comparison.
    """
    # Implementation...
    
def export_results(model, base_filename):
    """
    Export simulation results to CSV files.
    """
    # Implementation...