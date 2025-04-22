-- Drop tables in order of dependencies
DROP TABLE IF EXISTS transaction_pairs;
DROP TABLE IF EXISTS transactions;
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

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
    client_order_id VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL,
    
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
    UNIQUE (user_id, client_order_id)
);

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
    
    -- Constraints
    UNIQUE (user_id, symbol)
);

-- Index for fast lookup
CREATE INDEX idx_positions_user_symbol ON positions(user_id, symbol);

-- Create a history table to track position changes over time (optional but useful)
-- CREATE TABLE position_history (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     position_id UUID NOT NULL,
--     user_id UUID NOT NULL,
--     symbol TEXT NOT NULL,
    
--     -- Position state at time of snapshot
--     total_shares DECIMAL(19, 8) NOT NULL,
--     average_entry_price DECIMAL(19, 4) NOT NULL,
--     market_value DECIMAL(19, 4),
--     unrealized_pl DECIMAL(19, 4),
    
--     -- When this snapshot was taken
--     recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
--     -- Event that triggered this snapshot
--     event_type TEXT NOT NULL, -- 'BUY', 'SELL', 'DIVIDEND', 'SPLIT', 'DAY_END', etc.
--     transaction_id UUID,      -- Reference to the transaction that caused this update
    
--     -- Foreign keys
--     FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE,
--     FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
--     FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
-- );