import psycopg2
import pandas as pd
from typing import List, Optional, Union, Dict, Any
import logging

class OrderManager:
    """
    A class to manage stock order operations including inserting orders,
    retrieving buy entries, and getting account positions.
    """
    
    def __init__(self, db_config: Dict[str, Any], user_id: str = None, 
                 account_id: Optional[str] = None) -> None:
        """
        Initialize the StockDataLoader.
        
        Args:
            db_config: Dictionary containing PostgreSQL connection parameters
                       (host, database, user, password, port)
        """
        self.db_config = db_config
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
    
    def _get_connection(self):
        """
        Create and return a connection to the PostgreSQL database.
        
        Returns:
            A connection to the PostgreSQL database
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except psycopg2.Error as e:
            self.logger.error(f"Database connection error: {e}")
            raise
    
    def get_all_symbols(self) -> List[str]:
        try:
            # Connect to your PostgreSQL database
            conn = self._get_connection()
            cur = conn.cursor()

            # Execute query to get all distinct symbols

            # Check which parameters are provided and construct query accordingly
            if self.account_id is not None and self.user_id is not None:
                cur.execute(
                    "SELECT DISTINCT symbol FROM transactions WHERE user_id = %s AND account_id = %s", 
                    (self.user_id, self.account_id)
                )
            elif self.user_id is not None:
                cur.execute(
                    "SELECT DISTINCT symbol FROM transactions WHERE user_id = %s", 
                    (self.user_id,)
                )
            else:
                self.logger.error("Either user_id or both user_id and account_id must be provided.")
                return []       
            
            symbols = cur.fetchall()
            # Close connections
            cur.close()
            conn.close()

            # Flatten and return as a list
            return [symbol[0] for symbol in symbols]

        except Exception as e:
            self.logger.error("Error while fetching symbols: %s", e)
            return []
        
    def insert_orders(self, df: pd.DataFrame) -> None:
        """
        Inserts buy/sell orders into PostgreSQL database based on the side column.

        Args:
            df: DataFrame with order records
        """
        # Establish connection to PostgreSQL database using credentials from db_config
        # Validate user_id is provided
        if self.user_id is None:
            print("User ID was not provided. Please provide a valid user ID.")
            return

        conn = self._get_connection()
        cur = conn.cursor()  # Create a cursor to execute SQL commands

        # Process each row in the dataframe of orders
        for _, row in df.iterrows():
            side = row.get('side', '').strip().upper()  # Normalize order side to uppercase
            
            # Skip cancelled orders
            if row.get('status') and 'CANCEL' in row['status'].strip().upper():
                print(f"Skipping cancelled order: {row.get('client_order_id')}")
                continue
            
            # Prepare transaction data with all available fields, handling nulls
            transaction_data = {
                'client_order_id': row.get('client_order_id'),
                'user_id': self.user_id or row.get('user_id'),
                'account_id': self.account_id or None,
                'symbol': row.get('symbol'),
                'asset_id': row.get('asset_id'),
                'asset_class': row.get('asset_class'),
                'side': side,
                'order_type': row.get('order_type'),
                'order_class': row.get('order_class'),
                'position_intent': row.get('position_intent'),
                'notional': float(row.get('notional', 0.0)) if row.get('notional') is not None else None,
                'filled_qty': float(row.get('filled_qty', 0.0)) if row.get('filled_qty') is not None else None,
                'filled_avg_price': float(row.get('filled_avg_price', 0.0)) if row.get('filled_avg_price') is not None else None,
                'remaining_qty': float(row.get('filled_qty', 0.0)) if row.get('filled_qty') is not None else None,
                'limit_price': float(row.get('limit_price', 0.0)) if row.get('limit_price') is not None else None,
                'stop_price': float(row.get('stop_price', 0.0)) if row.get('stop_price') is not None else None,
                'created_at': None if pd.isna(row.get('created_at')) else row.get('created_at'),
                'filled_at': None if pd.isna(row.get('filled_at')) else row.get('filled_at'),
                'expired_at': None if pd.isna(row.get('expired_at')) else row.get('expired_at'),
                'expires_at': None if pd.isna(row.get('expires_at')) else row.get('expires_at'),
                'canceled_at': None if pd.isna(row.get('canceled_at')) else row.get('canceled_at'),
                'failed_at': None if pd.isna(row.get('failed_at')) else row.get('failed_at'),
                'status': row.get('status'),
                'time_in_force': row.get('time_in_force'),
                'related_transaction_ids': row.get('related_transaction_ids'),
                'tax_lot_method': row.get('tax_lot_method'),
                'realized_gain_loss': float(row.get('realized_gain_loss', 0.0)) if row.get('realized_gain_loss') is not None else None,
                'holding_period': row.get('holding_period'),
                'cost_basis': float(row.get('cost_basis', 0.0)) if row.get('cost_basis') is not None else None
            }
        
            # Construct query dynamically based on available fields
            fields = [k for k, v in transaction_data.items() if v is not None]
            placeholders = ['%s'] * len(fields)
            values = [transaction_data[field] for field in fields]
            
            # Insert order into the transactions table
            query = f"""
                INSERT INTO transactions ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT (user_id, client_order_id) DO NOTHING
            """
            
            try:
                cur.execute(query, values)
            except Exception as e:
                print(f"Error inserting transaction {row.get('client_order_id')}: {e}")
                # Optionally rollback on failure if you want to stop on first error
                # conn.rollback()
                # break

        # Commit transactions to the database
        conn.commit()
        # Clean up database resources
        cur.close()
        conn.close()

    def buy_entries_for_tickers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Retrieves buy entries for each ticker in the DataFrame and returns them in a DataFrame.
        
        Args:
            df: DataFrame containing ticker columns
            
        Returns:
            DataFrame containing all buy entries with appropriate headers
        """
        tickers = df.columns.tolist()
        
        # Define the headers from the SQL query
        headers = ['client_order_id', 'symbol', 'filled_avg_price', 'filled_qty', 
                'remaining_qty', 'filled_at']
        
        # Create an empty list to store all rows
        all_rows = []

        # Connect to your PostgreSQL database
        conn = self._get_connection()

        try:
            with conn.cursor() as cur:
                for ticker in tickers:
                    cur.execute("""
                        SELECT client_order_id, symbol, filled_avg_price, filled_qty, remaining_qty, filled_at
                        FROM transactions
                        WHERE symbol = %s AND user_id = %s
                    """, (ticker,self.user_id,))
                    rows = cur.fetchall()
                    if rows:
                        all_rows.extend(rows)

        except Exception as e:
            print("Database error:", e)
        finally:
            conn.close()
        
        # Create DataFrame from all rows
        import pandas as pd
        if not all_rows:
            print("No buy entries found for any ticker.")
            return pd.DataFrame(columns=headers)  # Return empty DataFrame with headers
        result_df = pd.DataFrame(all_rows, columns=headers)
        return result_df

    def get_account_positions(self) -> List[Dict[str, Any]]:
        """
        Retrieve all current positions for a specific user.
            
        Returns:
            A list of position dictionaries containing symbol, quantity, and average price
        """
        try:
            # Connect to PostgreSQL database
            conn = self._get_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Query to calculate current positions based on buys and sells
            # This is a simplified query and may need adjustment based on your schema
            query = """
            SELECT 
                b.symbol,
                b.client_order_id,
                b.filled_avg_price,
                b.filled_qty,
                b.remaining_qty,
                b.filled_at
            FROM 
                Buy b
            WHERE 
                b.user_id = %s
            """
            
            cur.execute(query, (self.user_id,))
            positions = cur.fetchall()

            # Close connections
            cur.close()
            conn.close()
            # Convert to list of dictionaries
            result = []
            for pos in positions:
                result.append({
                    "client_order_id": pos["client_order_id"],
                    "symbol": pos["symbol"],
                    "filled_avg_price": float(pos["filled_avg_price"]),
                    "filled_qty": float(pos["filled_qty"]),
                    "remaining_qty": float(pos["remaining_qty"]),
                    "filled_at": pos["filled_at"]
                })
            
            return result

        except Exception as e:
            print("Error while fetching account positions:", e)
            return []