"""Strawberry GraphQL schemas."""
import uuid
from typing import List, Optional
from datetime import datetime

import strawberry
from strawberry.types import Info
from api.db import SessionLocal

from api.dependencies import get_current_user_id, get_current_account_id, get_trading_client
from api.services.user_crud_service import (
    get_all_symbols,
    get_account_positions,
    get_loss_leaders
)
from SQL_scripts.buy_sell import OrderManager
from SQL_scripts.position import PositionManager
from api.utils.pagination import paginate_results, Connection


@strawberry.type
class User:
    """User representation."""
    user_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool
    profile_picture_url: Optional[str] = None


@strawberry.type
class Account:
    """Brokerage account representation."""
    id: str
    account_name: str
    account_type: str
    brokerage_name: str
    account_number: Optional[str] = None
    connection_status: str
    last_synced: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Symbol:
    """Stock symbol representation."""
    symbol: str


@strawberry.type
class Position:
    """Stock position representation."""
    id: str
    symbol: str
    total_shares: float
    available_shares: float
    average_entry_price: float
    market_value: Optional[float] = None
    last_price: Optional[float] = None
    last_price_updated_at: Optional[datetime] = None
    total_cost: float
    unrealized_pl: Optional[float] = None
    unrealized_pl_percent: Optional[float] = None
    realized_pl_ytd: Optional[float] = None
    opened_at: datetime
    is_open: bool
    account_name: Optional[str] = None


@strawberry.type
class Transaction:
    """Transaction representation."""
    id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    filled_qty: Optional[float] = None
    filled_avg_price: Optional[float] = None
    remaining_qty: Optional[float] = None
    created_at: datetime
    filled_at: Optional[datetime] = None
    status: str
    realized_gain_loss: Optional[float] = None
    account_name: Optional[str] = None


@strawberry.type
class LossLeader:
    """Loss leader stock representation."""
    symbol: str
    percentage_drop: float
    filled_avg_price: float
    current_price: float
    quantity: float
    dollar_loss: float


@strawberry.type
class HarvestRecommendation:
    """Tax-loss harvesting recommendation."""
    id: str
    ticker: str
    quantity: float
    original_price: float
    current_price: float
    unrealized_loss: float
    potential_tax_savings: float
    purchase_date: datetime
    alternative_stocks: Optional[List[str]] = None
    status: str
    generated_at: datetime
    expires_at: datetime


@strawberry.type
class Query:
    """GraphQL query root."""
    
    @strawberry.field
    def user(self, info: Info, user_id: str = strawberry.field(default_factory=get_current_user_id)) -> Optional[User]:
        """Get user information."""
        # Implementation would use a service to fetch the user
        # This is a placeholder for actual implementation
        # Use your user service to fetch user data
        # return get_user_by_id(current_user_id)
        return user_id  # Placeholder, replace with actual user fetching logic  
    
    @strawberry.field
    def accounts(self, info: Info, user_id: str = strawberry.field(default_factory=get_current_user_id)) -> List[Account]:
        """Get all accounts for the current user."""
        # Implementation would use a service to fetch accounts
        # This is a placeholder for actual implementation
        # return get_user_accounts(user_id)
        return []
    
    # @strawberry.field
    # def symbols(self, user_id: str = strawberry.field(default_factory=get_current_user_id)) -> List[Symbol]:
    #     """Get all symbols for the current user."""
    #     symbols_list = get_all_symbols(user_id)
    #     return [Symbol(symbol=s) for s in symbols_list]
    
    @strawberry.field
    def position_transactions(self, 
                symbol: str, 
                account_id: str = strawberry.field(default_factory=get_current_account_id),
                user_id: str = strawberry.field(default_factory=get_current_user_id)) -> List[Transaction]:
        """
        Get all position transactions for a given symbol.
        
        Returns a list of Position objects matching the specified symbol.
        """

        db = SessionLocal()
        try:
            orderer = OrderManager(db=db, user_id=user_id, account_id=account_id)
        finally:
            db.close()  
        positions_list = orderer.get_position_transactions(symbol=symbol)
        
        # Filter positions by the requested symbol
        symbol_positions = [p for p in positions_list if p["symbol"] == symbol]
        
        # Convert each matching position to a Position object
        result = []
        for p in symbol_positions:
            result.append(Transaction(
                id=str(p["id"]),
                client_order_id=p["client_order_id"],
                symbol=p["symbol"],
                side=p["side"],
                order_type=p["order_type"],
                filled_qty=p.get("filled_qty"),
                filled_avg_price=p.get("filled_avg_price"),
                remaining_qty=p.get("remaining_qty"),
                created_at=p["created_at"],
                filled_at=p.get("filled_at"),
                status=p["status"],
                
            ))
        return result
    
    @strawberry.field
    def positions(
        self,
        first: Optional[int] = 10,
        after: Optional[str] = None,
        account_id: str = strawberry.field(default_factory=get_current_account_id),
        user_id: str = strawberry.field(default_factory=get_current_user_id)
    ) -> Connection[Position]:
        """Get paginated account positions."""

        db = SessionLocal()
        try:
            position_mgr = PositionManager(db=db, user_id=user_id, account_id=account_id)
        finally:
            db.close()  
        all_positions = position_mgr.get_all_positions()
        return paginate_results(
            items=all_positions,
            first=first,
            after=after,
            converter_func=lambda p: Position(
                id=str(p["id"]),
                symbol=p["symbol"],
                total_shares=p["total_shares"],
                available_shares=p["available_shares"],
                average_entry_price=p["average_entry_price"],
                market_value=p.get("market_value"),
                last_price=p.get("last_price"),
                last_price_updated_at=p.get("last_price_updated_at"),
                total_cost=p["total_cost"],
                unrealized_pl=p.get("unrealized_pl"),
                unrealized_pl_percent=p.get("unrealized_pl_percent"),
                realized_pl_ytd=p.get("realized_pl_ytd", 0),
                opened_at=p["opened_at"],
                is_open=p["is_open"],
                account_name=p.get("account_name")
            )
        )
    @strawberry.field
    def single_position(
            self,
            symbol: str = not None,
            account_id: str = strawberry.field(default_factory=get_current_account_id),
            user_id: str = strawberry.field(default_factory=get_current_user_id)
        ) -> Optional[Position]:
        """
            Get a single position for a specific symbol.
            returns only the position for that specific symbol.
        """

        db = SessionLocal()
        try:
            position_mgr = PositionManager(db=db, user_id=user_id, account_id=account_id)
        finally:
            db.close()  
        last_price = position_mgr.get_last_price(symbol=symbol)
        print(f"Last price for {symbol}: {last_price}")
        position_mgr.update_position_market_data(symbol=symbol, last_price=last_price)

        position = position_mgr.get_position(symbol=symbol)
        if not position:
            print(f"No position found for symbol: {symbol}")
            return None
        
        return Position(
                id=str(position["id"]),
                symbol=position["symbol"],
                total_shares=position["total_shares"],
                available_shares=position["available_shares"],
                average_entry_price=position["average_entry_price"],
                market_value=position.get("market_value"),
                last_price=position.get("last_price"),
                last_price_updated_at=position.get("last_price_updated_at"),
                total_cost=position["total_cost"],
                unrealized_pl=position.get("unrealized_pl"),
                unrealized_pl_percent=position.get("unrealized_pl_percent"),
                realized_pl_ytd=position.get("realized_pl_ytd", 0),
                opened_at=position["opened_at"],
                is_open=position["is_open"],
                account_name=position.get("account_name")
            )

    @strawberry.field
    async def loss_leaders(
        self,
        first: Optional[int] = 10,
        after: Optional[str] = None,
        days_back: Optional[int] = 1,
        drop_threshold: Optional[float] = 10.0,
        account_id: str = strawberry.field(default_factory=get_current_account_id),
        user_id: str = strawberry.field(default_factory=get_current_user_id)
    ) -> Connection[LossLeader]:
        """Get paginated loss leader stocks."""
        trading_client = get_trading_client()
        all_loss_leaders = await get_loss_leaders(
            days_back=days_back,
            drop_threshold=drop_threshold,
            top_n=100,
            current_user_id=user_id,
            account_id=account_id,
            trading_client=trading_client
        )
        return paginate_results(
            items=all_loss_leaders,
            first=first,
            after=after,
            converter_func=lambda item: LossLeader(
                symbol=item["symbol"],
                percentage_drop=item["percentage_drop"],
                filled_avg_price=item["filled_avg_price"],
                current_price=item["current_price"],
                quantity=item["quantity"],
                dollar_loss=item["dollar_loss"]
            )
        )

    @strawberry.field
    def harvest_recommendations(
        self,
        first: Optional[int] = 10,
        after: Optional[str] = None,
        status: Optional[str] = "OPEN",
        user_id: str = strawberry.field(default_factory=get_current_user_id)
    ) -> Connection[HarvestRecommendation]:
        """Get paginated tax-loss harvest recommendations."""
        # Implementation would use a service to fetch recommendations
        # This is a placeholder for actual implementation
        # all_recommendations = get_harvest_recommendations(user_id, status)
        all_recommendations = []
        return paginate_results(
            items=all_recommendations,
            first=first,
            after=after,
            converter_func=lambda r: HarvestRecommendation(
                id=str(r["id"]),
                ticker=r["ticker"],
                quantity=r["quantity"],
                original_price=r["original_price"],
                current_price=r["current_price"],
                unrealized_loss=r["unrealized_loss"],
                potential_tax_savings=r["potential_tax_savings"],
                purchase_date=r["purchase_date"],
                alternative_stocks=r.get("alternative_stocks"),
                status=r["status"],
                generated_at=r["generated_at"],
                expires_at=r["expires_at"]
            )
        )

# Create schema
schema = strawberry.Schema(query=Query)