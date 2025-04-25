"""Order management functionality using SQLAlchemy."""
import logging
import pandas as pd
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from api.models import Transaction

class OrderManager:
    """
    A class to manage stock order operations using SQLAlchemy.
    """
    def __init__(self, db: Session, user_id: str = None, account_id: Optional[str] = None) -> None:
        """
        Initialize the OrderManager.
        
        Args:
            db: SQLAlchemy database session
            user_id: ID of the user
            account_id: Optional account ID
        """
        self.db = db
        self.user_id = user_id
        self.account_id = account_id
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up and configure logger for the class."""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def get_all_symbols(self) -> List[str]:
        """
        Get all distinct symbols for the user.
        
        Returns:
            List of symbol strings
        """
        try:
            query = self.db.query(Transaction.symbol).distinct()
            
            if self.user_id is not None:
                query = query.filter(Transaction.user_id == self.user_id)
                
                if self.account_id is not None:
                    query = query.filter(Transaction.account_id == self.account_id)
            else:
                self.logger.error("User ID must be provided.")
                return []
                
            symbols = query.all()
            return [symbol[0] for symbol in symbols]
            
        except Exception as e:
            self.logger.error(f"Error while fetching symbols: {e}")
            return []

    def insert_orders(self, df: pd.DataFrame) -> None:
        """
        Inserts buy/sell orders into database based on the side column.
        
        Args:
            df: DataFrame with order records
        """
        if self.user_id is None:
            self.logger.error("User ID was not provided. Please provide a valid user ID.")
            return
            
        try:
            for _, row in df.iterrows():
                side = row.get('side', '').strip().upper()
                
                # Skip cancelled orders
                if row.get('status') and 'CANCEL' in row['status'].strip().upper():
                    self.logger.info(f"Skipping cancelled order: {row.get('client_order_id')}")
                    continue
                
                # Prepare transaction data
                transaction_data = {
                    'client_order_id': row.get('client_order_id'),
                    'user_id': self.user_id or row.get('user_id'),
                    'account_id': self.account_id or None,
                    'symbol': row.get('symbol'),
                    'asset_id': row.get('asset_id'),
                    'asset_class': row.get('asset_class'),
                    'side': side,
                    # Add all other fields from your original insert_orders method
                    # ...
                }
                
                # Filter out None values
                transaction_data = {k: v for k, v in transaction_data.items() if v is not None}
                
                # Check if record already exists to prevent duplicates
                existing = self.db.query(Transaction).filter_by(
                    user_id=transaction_data['user_id'],
                    client_order_id=transaction_data['client_order_id']
                ).first()
                
                if not existing:
                    # Create new transaction
                    new_transaction = Transaction(**transaction_data)
                    self.db.add(new_transaction)
            
            # Commit all transactions
            self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error inserting transactions: {e}")
            self.db.rollback()

    def buy_entries_for_tickers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Retrieves buy entries for each ticker in the DataFrame.
        
        Args:
            df: DataFrame containing ticker columns
            
        Returns:
            DataFrame containing all buy entries with appropriate headers
        """
        tickers = df.columns.tolist()
        headers = ['client_order_id', 'symbol', 'filled_avg_price', 'filled_qty',
                  'remaining_qty', 'filled_at']
        
        all_rows = []
        
        try:
            for ticker in tickers:
                transactions = self.db.query(
                    Transaction.client_order_id,
                    Transaction.symbol,
                    Transaction.filled_avg_price,
                    Transaction.filled_qty,
                    Transaction.remaining_qty,
                    Transaction.filled_at
                ).filter(
                    Transaction.symbol == ticker,
                    Transaction.user_id == self.user_id
                ).all()
                
                all_rows.extend(transactions)
                
        except Exception as e:
            self.logger.error(f"Database error: {e}")
        
        if not all_rows:
            self.logger.info("No buy entries found for any ticker.")
            return pd.DataFrame(columns=headers)
            
        return pd.DataFrame(all_rows, columns=headers)

    def get_account_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all current positions for a specific user.
        
        Returns:
            A list of position dictionaries matching the Position GraphQL type structure
        """
        try:
            # Using raw SQL with SQLAlchemy for complex query
            result = self.db.execute(text("""
                SELECT
                    p.id,
                    p.symbol,
                    p.total_shares,
                    p.available_shares,
                    p.average_entry_price,
                    p.market_value,
                    p.last_price,
                    p.last_price_updated_at,
                    p.total_cost,
                    p.unrealized_pl,
                    p.unrealized_pl_percent,
                    p.realized_pl_ytd,
                    p.opened_at,
                    p.is_open
                FROM
                    positions p
                WHERE
                    p.user_id = :user_id
                    AND p.account_id = :account_id
                    AND p.is_open = TRUE
            """), {"user_id": self.user_id, "account_id": self.account_id})
            
            positions = []
            for row in result:
                positions.append({
                    "id": str(row.id),
                    "symbol": row.symbol,
                    "total_shares": float(row.total_shares) if row.total_shares is not None else 0.0,
                    "available_shares": float(row.available_shares) if row.available_shares is not None else 0.0,
                    "average_entry_price": float(row.average_entry_price) if row.average_entry_price is not None else 0.0,
                    "market_value": float(row.market_value) if row.market_value is not None else None,
                    "last_price": float(row.last_price) if row.last_price is not None else None,
                    "last_price_updated_at": row.last_price_updated_at,
                    "total_cost": float(row.total_cost) if row.total_cost is not None else 0.0,
                    "unrealized_pl": float(row.unrealized_pl) if row.unrealized_pl is not None else None,
                    "unrealized_pl_percent": float(row.unrealized_pl_percent) if row.unrealized_pl_percent is not None else None,
                    "realized_pl_ytd": float(row.realized_pl_ytd) if row.realized_pl_ytd is not None else None,
                    "opened_at": row.opened_at,
                    "is_open": bool(row.is_open),
                })
                
            return positions
            
        except Exception as e:
            self.logger.error(f"Error while fetching account positions: {e}")
            return []
        
    def get_position_transactions(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Retrieve all transactions for a specific symbol for the user.
        
        This retrieves the complete transaction history for a particular symbol,
        allowing you to see all buy orders associated with a position.
        
        Args:
            symbol: The stock symbol to retrieve transactions for
        
        Returns:
            A list of dictionaries containing transaction details for the position,
            matching the Transaction class structure
        """
        try:
            result = self.db.execute(text("""
                SELECT
                b.id,
                b.client_order_id,
                b.symbol,
                b.side,
                b.order_type,
                b.filled_qty,
                b.filled_avg_price,
                b.remaining_qty,
                b.created_at,
                b.filled_at,
                b.status,
                b.realized_gain_loss
                FROM
                transactions b
                WHERE
                b.user_id = :user_id
                AND b.account_id = :account_id
                AND b.symbol = :symbol
                ORDER BY b.created_at DESC
            """), {"user_id": self.user_id, "account_id": self.account_id, "symbol": symbol})
            
            transactions = []
            for row in result:
                transactions.append({
                    "id": row.id,
                    "client_order_id": row.client_order_id,
                    "symbol": row.symbol,
                    "side": row.side,
                    "order_type": row.order_type,
                    "filled_qty": float(row.filled_qty) if row.filled_qty else None,
                    "filled_avg_price": float(row.filled_avg_price) if row.filled_avg_price else None,
                    "remaining_qty": float(row.remaining_qty) if row.remaining_qty else None,
                    "created_at": row.created_at,
                    "filled_at": row.filled_at,
                    "status": row.status,
                    "realized_gain_loss": float(row.realized_gain_loss) if row.realized_gain_loss else None,
                })
                
            return transactions
                
        except Exception as e:
            self.logger.error(f"Error while fetching transactions for position {symbol}: {e}")
            return []