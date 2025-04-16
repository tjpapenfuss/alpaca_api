-- Drop Sell first due to foreign key dependency on Buy
DROP TABLE IF EXISTS Sell;
DROP TABLE IF EXISTS Buy;

-- Create Buy table
CREATE TABLE Buy (
    buy_order_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    buy_price DECIMAL(18, 6) NOT NULL,
    original_quantity DECIMAL(18, 6) NOT NULL,
    remaining_quantity DECIMAL(18, 6) NOT NULL,
    buy_datetime TIMESTAMP NOT NULL
);

-- Create Sell table
CREATE TABLE Sell (
    sell_order_id VARCHAR(100) PRIMARY KEY,
    buy_order_id VARCHAR(100) NOT NULL,
    sell_price DECIMAL(18, 6) NOT NULL,
    sell_quantity DECIMAL(18, 6) NOT NULL,
    sell_datetime TIMESTAMP NOT NULL,
    CONSTRAINT fk_buy_order
        FOREIGN KEY (buy_order_id) 
        REFERENCES Buy(buy_order_id)
        ON DELETE CASCADE
);