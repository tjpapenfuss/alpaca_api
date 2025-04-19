import psycopg2
import pandas as pd
import config

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
