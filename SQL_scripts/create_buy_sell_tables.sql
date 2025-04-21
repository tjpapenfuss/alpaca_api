-- Drop tables in order of dependencies
DROP TABLE IF EXISTS Sell;
DROP TABLE IF EXISTS Buy;
DROP TABLE IF EXISTS Users;

-- Create Users table
CREATE TABLE Users (
    user_id UUID PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    profile_picture_url VARCHAR(255)
);

-- Create Buy table with user_id foreign key
CREATE TABLE Buy (
    buy_order_id VARCHAR(100) PRIMARY KEY,
    user_id UUID NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    buy_price DECIMAL(18, 6) NOT NULL,
    original_quantity DECIMAL(18, 6) NOT NULL,
    remaining_quantity DECIMAL(18, 6) NOT NULL,
    buy_datetime TIMESTAMP NOT NULL,
    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES Users(user_id)
        ON DELETE CASCADE
);

-- Create Sell table
CREATE TABLE Sell (
    sell_order_id VARCHAR(100) PRIMARY KEY,
    user_id UUID NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    buy_order_id VARCHAR(100) NULL,
    sell_price DECIMAL(18, 6) NOT NULL,
    sell_quantity DECIMAL(18, 6) NOT NULL,
    sell_datetime TIMESTAMP NOT NULL,
    CONSTRAINT fk_buy_order
        FOREIGN KEY (buy_order_id)
        REFERENCES Buy(buy_order_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES Users(user_id)
        ON DELETE CASCADE
);
