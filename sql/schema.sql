-- sql/schema.sql

-- Accounts Table
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    account_number VARCHAR(50) UNIQUE NOT NULL,
    account_type VARCHAR(20),
    cash_balance DECIMAL(20,5) DEFAULT 0.0,
    margin_balance DECIMAL(20,5) DEFAULT 0.0,
    trading_mode VARCHAR(20) DEFAULT 'NORMAL',
    portfolio_margin_available DECIMAL(20,5) DEFAULT 0.0,
    internalization_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


UPDATE accounts SET trading_mode = 'NORMAL' WHERE account_id = 1;
UPDATE accounts SET trading_mode = 'RESTRICTED' WHERE account_id = 2;
UPDATE accounts SET trading_mode = 'CLOSED' WHERE account_id = 3;

INSERT INTO trading_permissions (trading_mode, asset_class, allow_buy, allow_sell, allow_short, allow_options, allow_spreads)
VALUES
('NORMAL', 'EQUITY', TRUE, TRUE, TRUE, TRUE, TRUE),
('NORMAL', 'OPTION', TRUE, TRUE, TRUE, TRUE, TRUE),
('RESTRICTED', 'EQUITY', TRUE, TRUE, FALSE, FALSE, FALSE),
('RESTRICTED', 'OPTION', FALSE, FALSE, FALSE, FALSE, FALSE),
('CLOSED', 'EQUITY', FALSE, FALSE, FALSE, FALSE, FALSE),
('CLOSED', 'OPTION', FALSE, FALSE, FALSE, FALSE, FALSE);


-- FIX Sessions Table
CREATE TABLE fix_sessions (
    session_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id) ON DELETE CASCADE,
    sender_comp_id VARCHAR(50) NOT NULL,
    target_comp_id VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Risk Settings Table
CREATE TABLE risk_settings (
    risk_setting_id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES fix_sessions(session_id) ON DELETE CASCADE,
    max_position_value DECIMAL(20,5),
    max_order_value DECIMAL(20,5),
    max_daily_volume INTEGER,
    max_order_volume INTEGER,
    max_messages_per_second INTEGER DEFAULT 100,
    prevent_wash_trades BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO risk_settings (session_id, max_messages_per_second, last_updated)
VALUES
(1, 50, CURRENT_TIMESTAMP),
(2, 100, CURRENT_TIMESTAMP);

-- Positions Table
CREATE TABLE positions (
    position_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id),
    session_id INTEGER REFERENCES fix_sessions(session_id),
    ticker VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    average_price DECIMAL(15,5),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    asset_class VARCHAR(20),
    UNIQUE (account_id, session_id, ticker)
);

-- Margin Requirements Table
CREATE TABLE margin_requirements (
    id SERIAL PRIMARY KEY,
    asset_class VARCHAR(20) NOT NULL, -- 'EQUITY', 'OPTION', 'FUTURE', etc.
    account_type VARCHAR(30) NOT NULL, -- 'CASH', 'MARGIN', 'DAY_TRADING_MARGIN', 'PORTFOLIO_MARGIN'
    initial_margin_rate DECIMAL(5,4) NOT NULL, -- e.g., 0.50 for 50%
    maintenance_margin_rate DECIMAL(5,4) NOT NULL, -- e.g., 0.25 for 25%
    UNIQUE (asset_class, account_type)
);

-- Instrument Margin Overrides Table
CREATE TABLE instrument_margin_overrides (
    id SERIAL PRIMARY KEY,
    instrument_id VARCHAR(50) NOT NULL REFERENCES instruments(ticker),
    initial_margin_rate DECIMAL(5,4) NOT NULL,
    maintenance_margin_rate DECIMAL(5,4) NOT NULL
);

-- Instruments Table
CREATE TABLE instruments (
    ticker VARCHAR(50) PRIMARY KEY,
    instrument_type VARCHAR(20) NOT NULL, -- 'EQUITY', 'OPTION', 'FUTURE'
    underlying_ticker VARCHAR(50),
    expiration_date DATE,
    strike_price DECIMAL(15,5),
    option_type VARCHAR(4), -- 'CALL' or 'PUT'
    contract_size INTEGER DEFAULT 100, -- Typically 100 for options
    exchange VARCHAR(50),
    currency VARCHAR(10) DEFAULT 'USD'
);

-- Orders Table
CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(account_id),
    session_id INTEGER REFERENCES fix_sessions(session_id),
    ticker VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'BUY' or 'SELL'
    quantity INTEGER NOT NULL,
    price DECIMAL(15,5),
    status VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'CANCELED', 'FILLED', etc.
    order_type VARCHAR(20) NOT NULL, -- 'LIMIT', 'MARKET', etc.
    asset_class VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    liquidity_tag VARCHAR(20) -- 'INTERNALIZED', 'EXTERNAL', etc.
);

