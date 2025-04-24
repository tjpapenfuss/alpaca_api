-- Drop tables in reverse order of dependencies to avoid constraint violations
DROP TABLE IF EXISTS harvest_recommendations CASCADE;
DROP TABLE IF EXISTS stock_correlations CASCADE;
DROP TABLE IF EXISTS legacy_stock_data CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS transaction_pairs CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS Users CASCADE;



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

-- ACCOUNTS table
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- e.g., 'INDIVIDUAL', 'IRA', '401K', etc.
    brokerage_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(100) NULL,
    connection_status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'DISCONNECTED', 'ERROR', etc.
    -- api_credentials JSONB, -- Securely stored API credentials -- Maybe add this in later. For now, we'll use a placeholder
    last_synced TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    
    -- Constraints
    UNIQUE (user_id, account_number, brokerage_name)
);

-- Create indexes for faster lookups
CREATE INDEX idx_accounts_user_id ON accounts(user_id);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
    client_order_id VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL,
    account_id UUID,  -- Account ID for the transaction, can be NULL if not associated with a specific account
    
    -- Asset information
    symbol TEXT NOT NULL,
    asset_id TEXT,
    asset_class TEXT,
    
    -- Order details
    side TEXT NOT NULL,                    -- 'BUY' or 'SELL'
    order_type TEXT NOT NULL,              -- 'MARKET', 'LIMIT', etc.
    order_class TEXT,                      -- 'SIMPLE', 'BRACKET', etc.
    position_intent TEXT,                  -- 'BUY_TO_OPEN', 'SELL_TO_CLOSE', etc.
    
    -- Quantity and price
    notional DECIMAL(19, 4),               -- Dollar amount for the order
    filled_qty DECIMAL(19, 8),             -- Quantity filled
    filled_avg_price DECIMAL(19, 4),       -- Average price
    remaining_qty DECIMAL(19, 8),          -- Remaining unsold quantity (for BUY transactions)

    -- Limit and stop details (for non-market orders)
    limit_price DECIMAL(19, 4),
    stop_price DECIMAL(19, 4),
    
    -- Time details
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    filled_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    canceled_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status TEXT NOT NULL,                  -- 'FILLED', 'CANCELED', etc.
    
    -- Time in force
    time_in_force TEXT,                    -- 'DAY', 'GTC', etc.
    
    -- Tax and trade linking
    related_transaction_ids UUID[],        -- Changed to UUID array
    tax_lot_method TEXT,                   -- 'FIFO', 'LIFO', 'SPECIFIC_LOT'
    realized_gain_loss DECIMAL(19, 4),     -- For SELL transactions
    holding_period TEXT,                   -- 'SHORT_TERM', 'LONG_TERM'
    cost_basis DECIMAL(19, 4),             -- For tax calculations
    
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,  -- Added foreign key constraint
    UNIQUE (user_id, client_order_id)
);

-- Create index for account-based transaction lookups
CREATE INDEX idx_transactions_account_id ON transactions(account_id);

CREATE TABLE transaction_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
    user_id UUID NOT NULL,
    symbol TEXT NOT NULL,
    
    -- The sell transaction
    sell_transaction_id UUID NOT NULL,      
    
    -- The buy transaction(s) that were matched against this sell
    buy_transaction_id UUID NOT NULL,       
    
    -- How much of the buy was used to match against this sell
    quantity_matched DECIMAL(19, 8) NOT NULL,

    -- Cost basis of this particular match
    cost_basis DECIMAL(19, 4) NOT NULL,

    -- Proceeds from this particular match
    proceeds DECIMAL(19, 4) NOT NULL,

    -- Gain or loss
    realized_gain_loss DECIMAL(19, 4) NOT NULL,

    -- Tax information
    acquisition_date TIMESTAMP WITH TIME ZONE NOT NULL,
    disposal_date TIMESTAMP WITH TIME ZONE NOT NULL,
    holding_period_days INTEGER NOT NULL,
    is_long_term BOOLEAN NOT NULL,

    -- Integrity constraints
    UNIQUE(sell_transaction_id, buy_transaction_id),
    CHECK(quantity_matched > 0),

    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (sell_transaction_id) REFERENCES transactions(id),
    FOREIGN KEY (buy_transaction_id) REFERENCES transactions(id)
);

CREATE TABLE positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    account_id UUID,  -- Added account_id column
    
    -- Asset information
    symbol TEXT NOT NULL,
    asset_id TEXT,
    asset_class TEXT,
    
    -- Position quantities and values
    total_shares DECIMAL(19, 8) NOT NULL DEFAULT 0,    -- Current total shares owned
    available_shares DECIMAL(19, 8) NOT NULL DEFAULT 0, -- Shares available (not reserved for pending orders)
    average_entry_price DECIMAL(19, 4) NOT NULL DEFAULT 0, -- Average purchase price
    market_value DECIMAL(19, 4),                        -- Current market value (can be updated periodically)
    last_price DECIMAL(19, 4),                          -- Last known price
    last_price_updated_at TIMESTAMP WITH TIME ZONE,     -- When the last price was updated
    
    -- Cost basis
    total_cost DECIMAL(19, 4) NOT NULL DEFAULT 0,      -- Total cost basis of current position
    
    -- Performance metrics
    unrealized_pl DECIMAL(19, 4),                       -- Unrealized profit/loss
    unrealized_pl_percent DECIMAL(8, 4),                -- Percentage gain/loss
    realized_pl_ytd DECIMAL(19, 4) DEFAULT 0,           -- Year-to-date realized profit/loss
    
    -- Position dates
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), -- When position was first opened
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), -- Last position update
    
    -- Tax lot information
    default_tax_lot_method TEXT DEFAULT 'FIFO',         -- FIFO, LIFO, etc.
    
    -- Position status
    is_open BOOLEAN NOT NULL DEFAULT TRUE,              -- Is position currently open
    closed_at TIMESTAMP WITH TIME ZONE,                 -- When position was fully closed
    
    -- Foreign keys
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,  -- Added account_id foreign key constraint
    
    -- Constraints
    UNIQUE (user_id, symbol)
);

-- Create index for account-based position lookups
CREATE INDEX idx_positions_account_id ON positions(account_id);
-- Index for fast lookup
CREATE INDEX idx_positions_user_symbol ON positions(user_id, symbol);

-- HARVEST_RECOMMENDATIONS table
CREATE TABLE harvest_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id UUID NOT NULL,
    transaction_id UUID,
    ticker VARCHAR(20) NOT NULL,
    quantity DECIMAL(19, 8) NOT NULL,
    original_price DECIMAL(19, 4) NOT NULL,
    current_price DECIMAL(19, 4) NOT NULL,
    unrealized_loss DECIMAL(19, 4) NOT NULL,
    potential_tax_savings DECIMAL(19, 4) NOT NULL,
    purchase_date TIMESTAMP WITH TIME ZONE NOT NULL,
    alternative_stocks JSONB, -- Stores suggested alternatives
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'EXECUTED', 'EXPIRED', 'REJECTED', etc.
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Foreign keys
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL,
    
    -- Constraints
    CHECK (unrealized_loss <= 0), -- Ensures we're only recommending positions with losses
    CHECK (potential_tax_savings >= 0) -- Tax savings should be positive
);

-- Create indexes for harvest recommendation lookups
CREATE INDEX idx_harvest_position_id ON harvest_recommendations(position_id);
CREATE INDEX idx_harvest_transaction_id ON harvest_recommendations(transaction_id);
CREATE INDEX idx_harvest_status ON harvest_recommendations(status);
CREATE INDEX idx_harvest_expires_at ON harvest_recommendations(expires_at);

-- STOCK_CORRELATIONS table
-- Setting this database table up for later use in correlation analysis. 
CREATE TABLE stock_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker_a VARCHAR(20) NOT NULL,
    ticker_b VARCHAR(20) NOT NULL,
    correlation_coefficient DECIMAL(7, 6) NOT NULL, -- Range from -1.0 to 1.0
    sector VARCHAR(100),
    industry VARCHAR(100),
    beta_similarity DECIMAL(10, 6),
    calculated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Ensure we don't have duplicate correlations (A-B is the same as B-A)
    UNIQUE (ticker_a, ticker_b),
    CHECK (ticker_a < ticker_b) -- Ensures consistent ordering to prevent duplicates
);

-- Create indexes for correlation lookups
CREATE INDEX idx_correlations_ticker_a ON stock_correlations(ticker_a);
CREATE INDEX idx_correlations_ticker_b ON stock_correlations(ticker_b);

CREATE TABLE legacy_stock_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    date DATE NOT NULL,
    open_price DECIMAL(18, 4) NOT NULL,
    close_price DECIMAL(18, 4) NOT NULL,
    high_price DECIMAL(18, 4) NOT NULL,
    low_price DECIMAL(18, 4) NOT NULL,
    volume BIGINT NOT NULL,
    
    -- Adding indices for common query patterns
    CONSTRAINT unique_ticker_date UNIQUE (ticker, date)
);

-- Index for faster queries when filtering by ticker
CREATE INDEX idx_legacy_stock_data_ticker ON legacy_stock_data(ticker);

-- Index for faster date range queries
CREATE INDEX idx_legacy_stock_data_date ON legacy_stock_data(date);

-- Comment on table
COMMENT ON TABLE legacy_stock_data IS 'Historical stock market data including daily OHLCV values';