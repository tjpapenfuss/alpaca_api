"""Position management functionality using SQLAlchemy."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import yfinance as yf

class PositionManager:
    """
    A class to manage stock positions using SQLAlchemy.
    
    This class handles the calculation and database operations related to
    investment positions, based on transaction history.
    """
    
    def __init__(self, db: Session, user_id: str = None, account_id: Optional[str] = None) -> None:
        """
        Initialize the PositionManager.
        
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
    
    def hydrate_positions(self) -> None:
        """
        Calculates and updates position information based on transaction history.
        
        This function:
        1. Gets all transactions for a user/account
        2. Groups them by symbol
        3. Calculates position metrics (shares, cost basis, etc.)
        4. Updates or creates position records in the database
        """
        if not self.user_id or not self.account_id:
            self.logger.error("Both user_id and account_id must be provided to hydrate positions")
            return
            
        try:
            # Get and group transactions
            symbols_data = self._get_grouped_transactions()
            
            # Process and update each position
            for symbol, data in symbols_data.items():
                position_metrics = self._calculate_position_metrics(data['transactions'])
                position_metrics['opened_at'] = data['opened_at']
                
                self._update_position_in_db(symbol, position_metrics)
                
            # Commit all changes
            self.db.commit()
            self.logger.info(f"Successfully hydrated positions for user {self.user_id}, account {self.account_id}")
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error while hydrating positions: {e}")

    def _get_grouped_transactions(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all transactions for the user/account and group them by symbol.
        
        Returns:
            Dictionary with symbols as keys and transaction data as values
        """
        
        transactions = self.db.execute(text("""
            SELECT
                id,
                symbol,
                side,
                filled_qty,
                filled_avg_price,
                status,
                filled_at,
                realized_gain_loss
            FROM
                transactions
            WHERE
                user_id = :user_id
                AND account_id = :account_id
                AND status = 'filled'
            ORDER BY
                filled_at ASC
        """), {"user_id": self.user_id, "account_id": self.account_id})

        symbols_data = {}
        for tx in transactions:
            symbol = tx.symbol
            
            if symbol not in symbols_data:
                symbols_data[symbol] = {
                    'opened_at': None,
                    'transactions': []
                }
            
            symbols_data[symbol]['transactions'].append(tx)
            
            # Track the earliest transaction time as position opened_at
            if tx.filled_at and (not symbols_data[symbol]['opened_at'] 
                                or tx.filled_at < symbols_data[symbol]['opened_at']):
                symbols_data[symbol]['opened_at'] = tx.filled_at
        
        return symbols_data

    def _calculate_position_metrics(self, transactions: List[Any]) -> Dict[str, Any]:
        """
        Calculate position metrics based on transaction history.
        
        Args:
            transactions: List of transaction records for a symbol
        
        Returns:
            Dictionary containing position metrics (shares, cost, P&L, etc.)
        """
        total_shares = 0.0
        total_cost = 0.0
        realized_pl_ytd = 0.0
        
        for tx in transactions:
            qty = float(tx.filled_qty) if tx.filled_qty else 0.0
            price = float(tx.filled_avg_price) if tx.filled_avg_price else 0.0
            
            if 'BUY' in tx.side:
                # Add shares to position
                total_shares += qty
                total_cost += qty * price
            elif 'SELL' in tx.side:
                # Remove shares and calculate P/L
                if total_shares > 0:
                    # Calculate realized gain/loss
                    if tx.realized_gain_loss is not None:
                        realized_pl_ytd += float(tx.realized_gain_loss)
                    else:
                        # Simple FIFO calculation if realized_gain_loss not in transaction
                        avg_cost = total_cost / total_shares if total_shares else 0
                        realized_pl_ytd += (price - avg_cost) * qty
                    
                    # Adjust total_shares and total_cost
                    proportion_sold = min(qty / total_shares, 1.0)
                    total_cost -= total_cost * proportion_sold
                    total_shares -= qty
        
        # Calculate average entry price
        average_entry_price = total_cost / total_shares if total_shares > 0 else 0.0
        is_open = total_shares > 0
        
        return {
            "total_shares": total_shares,
            "available_shares": total_shares,  # Assuming all shares are available
            "average_entry_price": average_entry_price,
            "total_cost": total_cost,
            "realized_pl_ytd": realized_pl_ytd,
            "is_open": is_open
        }

    def _update_position_in_db(self, symbol: str, position_data: Dict[str, Any]) -> None:
        """
        Update or create a position record in the database.
        
        Args:
            symbol: The stock symbol
            position_data: Dictionary with position metrics
        """
        # Check if position record exists
        position = self.db.execute(text("""
            SELECT id FROM positions
            WHERE user_id = :user_id
            AND account_id = :account_id
            AND symbol = :symbol
        """), {
            "user_id": self.user_id,
            "account_id": self.account_id,
            "symbol": symbol
        }).fetchone()
        
        if position:
            # Update existing position
            self.db.execute(text("""
                UPDATE positions
                SET total_shares = :total_shares,
                    available_shares = :available_shares,
                    average_entry_price = :average_entry_price,
                    total_cost = :total_cost,
                    realized_pl_ytd = :realized_pl_ytd,
                    opened_at = :opened_at,
                    is_open = :is_open,
                    last_updated_at = NOW()
                WHERE id = :position_id
            """), {
                "position_id": position.id,
                **position_data
            })
        else:
            # Create new position record
            self.db.execute(text("""
                INSERT INTO positions (
                    user_id,
                    account_id,
                    symbol,
                    total_shares,
                    available_shares,
                    average_entry_price,
                    total_cost,
                    realized_pl_ytd,
                    opened_at,
                    is_open,
                    last_updated_at
                ) VALUES (
                    :user_id,
                    :account_id,
                    :symbol,
                    :total_shares,
                    :available_shares,
                    :average_entry_price,
                    :total_cost,
                    :realized_pl_ytd,
                    :opened_at,
                    :is_open,
                    NOW()
                )
            """), {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": symbol,
                **position_data
            })
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific position for the user/account.
        
        Args:
            symbol: The stock symbol to retrieve position for
        
        Returns:
            Position data as a dictionary or None if not found
        """
        try:
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
                    AND p.symbol = :symbol
            """), {"user_id": self.user_id, "account_id": self.account_id, "symbol": symbol})
            
            row = result.fetchone()
            if not row:
                return None
                
            return {
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
            }
                
        except Exception as e:
            self.logger.error(f"Error while fetching position for {symbol}: {e}")
            return None
    
    def get_all_positions(self, include_closed: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieve all positions for a specific user/account.
        
        Args:
            include_closed: Whether to include closed positions (default: False)
        
        Returns:
            A list of position dictionaries
        """
        try:
            query = """
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
            """
            
            if not include_closed:
                query += " AND p.is_open = TRUE"
                
            result = self.db.execute(text(query), {
                "user_id": self.user_id, 
                "account_id": self.account_id
            })
            
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
            self.logger.error(f"Error while fetching positions: {e}")
            return []
    
    def update_position_market_data(self, symbol: str, last_price: float) -> bool:
        """
        Update market data for a position (last price, market value, unrealized P&L).
        
        Args:
            symbol: The stock symbol to update
            last_price: The current market price
            
        Returns:
            Boolean indicating success of the operation
        """
        try:
            # Get current position data
            position = self.get_position(symbol)
            if not position or not position['is_open']:
                return False
                
            total_shares = position['total_shares']
            avg_price = position['average_entry_price']
            total_cost = position['total_cost']
            
            # Calculate new values
            market_value = total_shares * last_price
            unrealized_pl = market_value - total_cost
            unrealized_pl_percent = (unrealized_pl / total_cost) * 100 if total_cost else 0
            
            # Update the position
            self.db.execute(text("""
                UPDATE positions
                SET last_price = :last_price,
                    market_value = :market_value,
                    unrealized_pl = :unrealized_pl,
                    unrealized_pl_percent = :unrealized_pl_percent,
                    last_price_updated_at = NOW(),
                    last_updated_at = NOW()
                WHERE user_id = :user_id
                AND account_id = :account_id
                AND symbol = :symbol
            """), {
                "user_id": self.user_id,
                "account_id": self.account_id,
                "symbol": symbol,
                "last_price": last_price,
                "market_value": market_value,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_percent": unrealized_pl_percent
            })
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating market data for position {symbol}: {e}")
            return False
        
    def get_last_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a given stock symbol using Yahoo Finance.
        
        Args:
            symbol: The stock ticker symbol (e.g., "AAPL", "ABEV3.SA")
            
        Returns:
            The current regular market price or None if the data can't be retrieved
        """
        try:
            stock = yf.Ticker(symbol)
            price_data = stock.info
            return price_data.get('regularMarketPrice')
        except Exception as e:
            # Log the error or handle it as appropriate for your application
            print(f"Error fetching price for {symbol}: {str(e)}")
            return None
            
    def update_position_with_new_transaction(self, transaction_id: str) -> bool:
        """
        Update position based on a single new transaction.
        
        Args:
            transaction_id: ID of the new transaction to process
            
        Returns:
            Boolean indicating success of the operation
        """
        if not self.user_id or not self.account_id:
            self.logger.error("Both user_id and account_id must be provided to update positions")
            return False
            
        try:
            # Get the transaction
            transaction = self.db.execute(text("""
                SELECT
                    id,
                    symbol,
                    side,
                    filled_qty,
                    filled_avg_price,
                    status,
                    filled_at,
                    realized_gain_loss
                FROM
                    transactions
                WHERE
                    id = :transaction_id
                    AND user_id = :user_id
                    AND account_id = :account_id
                    AND status = 'FILLED'
            """), {
                "transaction_id": transaction_id,
                "user_id": self.user_id,
                "account_id": self.account_id
            }).fetchone()
            
            if not transaction:
                self.logger.error(f"Transaction {transaction_id} not found or not in FILLED status")
                return False
                
            symbol = transaction.symbol
            
            # Get current position data
            position = self.get_position(symbol)
            
            # Create new position if it doesn't exist
            if not position:
                position_data = {
                    "total_shares": 0.0,
                    "available_shares": 0.0,
                    "average_entry_price": 0.0,
                    "total_cost": 0.0,
                    "realized_pl_ytd": 0.0,
                    "opened_at": transaction.filled_at,
                    "is_open": False  # Will be updated based on calculation
                }
            else:
                position_data = {
                    "total_shares": position["total_shares"],
                    "available_shares": position["available_shares"],
                    "average_entry_price": position["average_entry_price"],
                    "total_cost": position["total_cost"],
                    "realized_pl_ytd": position["realized_pl_ytd"] or 0.0,
                    "opened_at": position["opened_at"] or transaction.filled_at,
                    "is_open": position["is_open"]
                }
            
            # Process transaction
            qty = float(transaction.filled_qty) if transaction.filled_qty else 0.0
            price = float(transaction.filled_avg_price) if transaction.filled_avg_price else 0.0
            
            if 'BUY' in transaction.side:
                # Add shares to position
                position_data["total_shares"] += qty
                position_data["available_shares"] += qty
                position_data["total_cost"] += qty * price
                
                # Update average entry price
                if position_data["total_shares"] > 0:
                    position_data["average_entry_price"] = position_data["total_cost"] / position_data["total_shares"]
                    
                position_data["is_open"] = True
                
            elif 'SELL' in transaction.side:
                # Calculate realized P&L if not provided in transaction
                if transaction.realized_gain_loss is not None:
                    position_data["realized_pl_ytd"] += float(transaction.realized_gain_loss)
                elif position_data["total_shares"] > 0:
                    # Simple FIFO calculation
                    avg_cost = position_data["average_entry_price"]
                    position_data["realized_pl_ytd"] += (price - avg_cost) * qty
                
                # Remove shares
                if position_data["total_shares"] > 0:
                    proportion_sold = min(qty / position_data["total_shares"], 1.0)
                    position_data["total_cost"] -= position_data["total_cost"] * proportion_sold
                    position_data["total_shares"] -= qty
                    position_data["available_shares"] -= qty
                    
                    # Check if position is still open
                    position_data["is_open"] = position_data["total_shares"] > 0
            
            # Update the position in the database
            self._update_position_in_db(symbol, position_data)
            
            # If last price is available, update market data
            if position and position["last_price"] is not None:
                self.update_position_market_data(symbol, position["last_price"])
            
            self.db.commit()
            self.logger.info(f"Successfully updated position for {symbol} with transaction {transaction_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Error updating position with transaction {transaction_id}: {e}")
            return False