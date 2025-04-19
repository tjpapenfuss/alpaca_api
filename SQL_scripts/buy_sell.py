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

    conn = psycopg2.connect(
        host=db_config['host'],
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        port=db_config.get('port', 5432)
    )
    cur = conn.cursor()

    if user_id is None:
        print("User ID was not provided. Please provide a valid user ID.")

    for _, row in df.iterrows():
        side = row['side'].strip().upper()

        if 'BUY' in side:
            cur.execute("""
                INSERT INTO Buy (buy_order_id, user_id, symbol, buy_price, original_quantity, remaining_quantity, buy_datetime)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (buy_order_id) DO NOTHING
            """, (
                row['client_order_id'],
                user_id,
                row['symbol'],
                float(row['filled_avg_price']),
                float(row['filled_qty']),
                float(row['filled_qty']),
                row['filled_at']
            ))

        elif 'SELL' in side:
            # You’ll need to determine buy_order_id matching logic in a real-world use case
            # For now, we assume a placeholder buy_order_id = 1
            # cur.execute("""
            #     INSERT INTO Sell (buy_order_id, sell_price, sell_quantity, sell_datetime)
            #     VALUES (%s, %s, %s, %s)
            # """, (
            #     1,  # Replace with actual logic to fetch related buy_order_id
            #     float(row['filled_avg_price']),
            #     float(row['filled_qty']),
            #     row['filled_at']
            # ))
            print("Pausing Sell for now. ")

    conn.commit()
    cur.close()
    conn.close()

def buy_entries_for_tickers(df):
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
                    WHERE symbol = %s
                """, (ticker,))
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