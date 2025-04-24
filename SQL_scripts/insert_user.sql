-- Manual for now. Will be replaced with a script to generate a UUID and insert a new user.
-- This script inserts a new user into the Users table.

-- Generate a UUID and insert a new user
INSERT INTO Users (
    user_id,
    username,
    email,
    first_name,
    last_name,
    password_hash,
    phone_number,
    created_at,
    last_login,
    is_active,
    profile_picture_url
) VALUES (
    gen_random_uuid(), -- Generates a random UUID (PostgreSQL)
    'your_username',   -- Replace with your preferred username
    'your.email@example.com', -- Replace with your email
    'YourFirstName',   -- Replace with your first name
    'YourLastName',    -- Replace with your last name
    '$2a$12$abcdefghijklmnopqrstuvwxyz123456', -- Replace with an actual password hash
    '+1234567890',     -- Replace with your phone number
    CURRENT_TIMESTAMP, -- Current timestamp for creation time
    CURRENT_TIMESTAMP, -- Current timestamp for last login time
    TRUE,              -- User is active
    'https://example.com/profile-pictures/default.png' -- Optional profile picture URL
);

-- Insert a sample Alpaca Markets account
INSERT INTO accounts (
    user_id,
    account_name,
    account_type,
    brokerage_name,
    account_number,
    connection_status,
    --api_credentials,
    last_synced
) VALUES (
    -- Replace this with your actual user_id from the Users table
    '{INSERT_USER_ID_HERE}'::UUID,
    '{INSERT_ACCOUNT_NAME_HERE}', -- Replace with your account name
    'INDIVIDUAL',
    '{Insert Brokerage Name Here}', -- Replace with your brokerage name
    '{If applicable, insert account number here}', -- Replace with your account number if applicable
    'ACTIVE', --Active is the default status
    -- '{"api_key": "your_api_key_here", "api_secret": "your_api_secret_here"}'::JSONB,
    NOW()
);