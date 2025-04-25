"""SQLAlchemy models for the database schema."""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Numeric, String, Text, 
    ForeignKey, Integer, CheckConstraint, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from api.db import Base


class User(Base):
    """User model representing app users."""
    __tablename__ = "users"
    
    user_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    profile_picture_url = Column(String(255), nullable=True)
    
    # Relationships
    accounts = relationship("Account", back_populates="user")
    positions = relationship("Position", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")


class Account(Base):
    """Account model for brokerage accounts."""
    __tablename__ = "accounts"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    account_name = Column(String(100), nullable=False)
    account_type = Column(String(50), nullable=False)
    brokerage_name = Column(String(100), nullable=False)
    account_number = Column(String(100), nullable=True)
    connection_status = Column(String(50), nullable=False, default="ACTIVE")
    last_synced = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    positions = relationship("Position", back_populates="account")
    transactions = relationship("Transaction", back_populates="account")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'account_number', 'brokerage_name'),
    )


class Transaction(Base):
    """Model for stock transactions."""
    __tablename__ = "transactions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    client_order_id = Column(String(100), nullable=False)
    user_id = Column(UUID, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    
    # Asset information
    symbol = Column(Text, nullable=False)
    asset_id = Column(Text, nullable=True)
    asset_class = Column(Text, nullable=True)
    
    # Order details
    side = Column(Text, nullable=False)
    order_type = Column(Text, nullable=False)
    order_class = Column(Text, nullable=True)
    position_intent = Column(Text, nullable=True)
    
    # Quantity and price
    notional = Column(Numeric(19, 4), nullable=True)
    filled_qty = Column(Numeric(19, 8), nullable=True)
    filled_avg_price = Column(Numeric(19, 4), nullable=True)
    remaining_qty = Column(Numeric(19, 8), nullable=True)
    
    # Limit and stop details
    limit_price = Column(Numeric(19, 4), nullable=True)
    stop_price = Column(Numeric(19, 4), nullable=True)
    
    # Time details
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(Text, nullable=False)
    time_in_force = Column(Text, nullable=True)
    
    # Tax and trade linking
    related_transaction_ids = Column(ARRAY(UUID), nullable=True)
    tax_lot_method = Column(Text, nullable=True)
    realized_gain_loss = Column(Numeric(19, 4), nullable=True)
    holding_period = Column(Text, nullable=True)
    cost_basis = Column(Numeric(19, 4), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    buy_transaction_pairs = relationship("TransactionPair", foreign_keys="TransactionPair.buy_transaction_id", back_populates="buy_transaction")
    sell_transaction_pairs = relationship("TransactionPair", foreign_keys="TransactionPair.sell_transaction_id", back_populates="sell_transaction")
    harvest_recommendations = relationship("HarvestRecommendation", back_populates="transaction")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'client_order_id'),
    )


class TransactionPair(Base):
    """Model for matched buy/sell transaction pairs."""
    __tablename__ = "transaction_pairs"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    symbol = Column(Text, nullable=False)
    
    # Transaction references
    sell_transaction_id = Column(UUID, ForeignKey("transactions.id"), nullable=False)
    buy_transaction_id = Column(UUID, ForeignKey("transactions.id"), nullable=False)
    
    # Match details
    quantity_matched = Column(Numeric(19, 8), nullable=False)
    cost_basis = Column(Numeric(19, 4), nullable=False)
    proceeds = Column(Numeric(19, 4), nullable=False)
    realized_gain_loss = Column(Numeric(19, 4), nullable=False)
    
    # Tax information
    acquisition_date = Column(DateTime(timezone=True), nullable=False)
    disposal_date = Column(DateTime(timezone=True), nullable=False)
    holding_period_days = Column(Integer, nullable=False)
    is_long_term = Column(Boolean, nullable=False)
    
    # Relationships
    sell_transaction = relationship("Transaction", foreign_keys=[sell_transaction_id], back_populates="sell_transaction_pairs")
    buy_transaction = relationship("Transaction", foreign_keys=[buy_transaction_id], back_populates="buy_transaction_pairs")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('sell_transaction_id', 'buy_transaction_id'),
        CheckConstraint('quantity_matched > 0', name='check_quantity_positive'),
    )


class Position(Base):
    """Position model for stock holdings."""
    __tablename__ = "positions"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    account_id = Column(UUID, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    
    # Asset information
    symbol = Column(Text, nullable=False)
    asset_id = Column(Text, nullable=True)
    asset_class = Column(Text, nullable=True)
    
    # Position quantities and values
    total_shares = Column(Numeric(19, 8), nullable=False, default=0)
    available_shares = Column(Numeric(19, 8), nullable=False, default=0)
    average_entry_price = Column(Numeric(19, 4), nullable=False, default=0)
    market_value = Column(Numeric(19, 4), nullable=True)
    last_price = Column(Numeric(19, 4), nullable=True)
    last_price_updated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Cost basis
    total_cost = Column(Numeric(19, 4), nullable=False, default=0)
    
    # Performance metrics
    unrealized_pl = Column(Numeric(19, 4), nullable=True)
    unrealized_pl_percent = Column(Numeric(8, 4), nullable=True)
    realized_pl_ytd = Column(Numeric(19, 4), default=0)
    
    # Position dates
    opened_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Tax lot information
    default_tax_lot_method = Column(Text, default="FIFO")
    
    # Position status
    is_open = Column(Boolean, nullable=False, default=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    account = relationship("Account", back_populates="positions")
    harvest_recommendations = relationship("HarvestRecommendation", back_populates="position")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'symbol'),
    )


class HarvestRecommendation(Base):
    """Model for tax-loss harvesting recommendations."""
    __tablename__ = "harvest_recommendations"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    position_id = Column(UUID, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(UUID, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    ticker = Column(String(20), nullable=False)
    quantity = Column(Numeric(19, 8), nullable=False)
    original_price = Column(Numeric(19, 4), nullable=False)
    current_price = Column(Numeric(19, 4), nullable=False)
    unrealized_loss = Column(Numeric(19, 4), nullable=False)
    potential_tax_savings = Column(Numeric(19, 4), nullable=False)
    purchase_date = Column(DateTime(timezone=True), nullable=False)
    alternative_stocks = Column(JSONB, nullable=True)
    status = Column(String(50), nullable=False, default="OPEN")
    generated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Relationships
    position = relationship("Position", back_populates="harvest_recommendations")
    transaction = relationship("Transaction", back_populates="harvest_recommendations")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('unrealized_loss <= 0', name='check_unrealized_loss_negative'),
        CheckConstraint('potential_tax_savings >= 0', name='check_tax_savings_positive'),
    )


class StockCorrelation(Base):
    """Model for stock correlation data."""
    __tablename__ = "stock_correlations"
    
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    ticker_a = Column(String(20), nullable=False)
    ticker_b = Column(String(20), nullable=False)
    correlation_coefficient = Column(Numeric(7, 6), nullable=False)
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    beta_similarity = Column(Numeric(10, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('ticker_a', 'ticker_b'),
        CheckConstraint('ticker_a < ticker_b', name='check_ticker_order'),
    )


class LegacyStockData(Base):
    """Model for historical stock price data."""
    __tablename__ = "legacy_stock_data"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), nullable=False)
    date = Column(Date, nullable=False)
    open_price = Column(Numeric(18, 4), nullable=False)
    close_price = Column(Numeric(18, 4), nullable=False)
    high_price = Column(Numeric(18, 4), nullable=False)
    low_price = Column(Numeric(18, 4), nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='unique_ticker_date'),
    )