import psycopg2
import pandas as pd
import config

def get_all_symbols(user_id):
    try:
        # Connect to your PostgreSQL database
        conn = psycopg2.connect(
            host=config.db_config['host'],
            dbname=config.db_config['dbname'],
            user=config.db_config['user'],
            password=config.db_config['password'],
            port=config.db_config.get('port', 5432)
        )
        cur = conn.cursor()

        # Execute query to get all distinct symbols
        cur.execute("SELECT DISTINCT symbol FROM Buy WHERE user_id = %s", (user_id,))
        symbols = cur.fetchall()

        # Close connections
        cur.close()
        conn.close()

        # Flatten and return as a list
        return [symbol[0] for symbol in symbols]

    except Exception as e:
        print("Error while fetching symbols:", e)
        return []
def insert_orders(df, db_config, user_id=None):
    """
    Inserts buy/sell orders into PostgreSQL database based on the side column.

    Args:
        df (pd.DataFrame): DataFrame with order records.
        db_config (dict): Dictionary with keys host, dbname, user, password, port.
    """
    # Establish connection to PostgreSQL database using credentials from db_config
    conn = psycopg2.connect(
        host=db_config['host'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        port=db_config.get('port', 5432)  # Default to port 5432 if not specified
    )
    cur = conn.cursor()  # Create a cursor to execute SQL commands

    # Validate user_id is provided
    if user_id is None:
        print("User ID was not provided. Please provide a valid user ID.")

    # Process each row in the dataframe of orders
    for _, row in df.iterrows():
        side = row['side'].strip().upper()  # Normalize order side to uppercase
        # Convert None to appropriate values for database insertion
        filled_avg_price = 0.0 if row['filled_avg_price'] is None else float(row['filled_avg_price'])
        filled_qty = 0.0 if row['filled_qty'] is None else float(row['filled_qty'])
        # print(row['status'])
        if 'CANCEL' in row['status'].strip().upper():
            print(row)
            continue  # Skip cancelled orders
        if 'BUY' in side:
            # Insert buy order into the Buy table
            # If order with this ID already exists, do nothing (ON CONFLICT)
            cur.execute("""
                INSERT INTO Buy (buy_order_id, user_id, symbol, buy_price, original_quantity, remaining_quantity, buy_datetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (buy_order_id) DO NOTHING
            """, (
                row['client_order_id'],
                user_id,
                row['symbol'],
                filled_avg_price,  # Convert price to float
                filled_qty,        # Convert quantity to float
                filled_qty,        # Initially, remaining = original
                row['filled_at']   # Timestamp when order was filled
            ))

        elif 'SELL' in side:
            # Insert sell order into the Sell table
            # Note: No conflict handling for sell orders
            cur.execute("""
                INSERT INTO Sell (sell_order_id, user_id, symbol, sell_price, sell_quantity, sell_datetime)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                row['client_order_id'],
                user_id,
                row['symbol'],
                filled_avg_price,  # Convert price to float
                filled_qty,        # Convert quantity to float
                row['filled_at'] if row['filled_at'] else None                 # Timestamp when order was filled
            ))
        else:
            print(f"Unknown order side '{side}' for order ID {row['client_order_id']}. Skipping this order.")

    # Commit transactions to the database
    conn.commit()
    # Clean up database resources
    cur.close()
    conn.close()

def buy_entries_for_tickers(user_id, df):
    """
    Retrieves buy entries for each ticker in the DataFrame and returns them in a DataFrame.
    
    Args:
        df: DataFrame containing ticker columns
        
    Returns:
        pd.DataFrame: DataFrame containing all buy entries with appropriate headers
    """
    tickers = df.columns.tolist()
    
    # Define the headers from the SQL query
    headers = ['buy_order_id', 'symbol', 'buy_price', 'original_quantity', 
               'remaining_quantity', 'buy_datetime']
    
    # Create an empty list to store all rows
    all_rows = []

    # Connect to your PostgreSQL database
    conn = psycopg2.connect(
        host=config.db_config['host'],
        dbname=config.db_config['dbname'],
        user=config.db_config['user'],
        password=config.db_config['password'],
        port=config.db_config.get('port', 5432)
    )
    try:
        with conn.cursor() as cur:
            for ticker in tickers:
                cur.execute("""
                    SELECT buy_order_id, symbol, buy_price, original_quantity, remaining_quantity, buy_datetime
                    FROM Buy
                    WHERE symbol = %s AND user_id = %s
                """, (ticker,user_id,))
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

def get_account_positions(user_id: int) -> list[dict]:
    """
    Retrieve all current positions for a specific user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        A list of position dictionaries containing symbol, quantity, and average price
    """
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(
            host=config.db_config['host'],
            dbname=config.db_config['dbname'],
            user=config.db_config['user'],
            password=config.db_config['password'],
            port=config.db_config.get('port', 5432)
        )
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        # Query to calculate current positions based on buys and sells
        # This is a simplified query and may need adjustment based on your schema
        query = """
        SELECT 
            b.symbol,
            b.buy_order_id,
            b.buy_price,
            b.original_quantity,
            b.remaining_quantity,
            b.buy_datetime
        FROM 
            Buy b
        WHERE 
            b.user_id = %s
        """
        
        cur.execute(query, (user_id,))
        positions = cur.fetchall()

        # Close connections
        cur.close()
        conn.close()
        # Convert to list of dictionaries
        result = []
        for pos in positions:
            result.append({
                "buy_order_id": pos["buy_order_id"],
                "symbol": pos["symbol"],
                "buy_price": float(pos["buy_price"]),
                "original_quantity": float(pos["original_quantity"]),
                "remaining_quantity": float(pos["remaining_quantity"]),
                "buy_datetime": pos["buy_datetime"]
            })
        
        return result

    except Exception as e:
        print("Error while fetching account positions:", e)
        return []