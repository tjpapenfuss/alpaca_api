"""User router for REST endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from datetime import date, timedelta

from alpaca.trading.client import TradingClient
from api.dependencies import get_trading_client, get_current_user_id
from api.services.user_crud_service import get_loss_leaders

router = APIRouter(prefix="/api", tags=["users"])

@router.get("/loss_leaders", response_model=List[Dict[str, Any]])
async def loss_leaders_endpoint(
    days_back: Optional[int] = 1,
    drop_threshold: Optional[float] = 10.0,
    top_n: Optional[int] = 5,
    trading_client: TradingClient = Depends(get_trading_client),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get the top stocks with the most significant losses.
    
    Args:
        days_back: How many days to look back for start date (default: 1)
        drop_threshold: Percentage threshold for considering a stock as a loss leader (default: 10.0%)
        top_n: Number of top loss leaders to return (default: 5)
        trading_client: Alpaca trading client dependency
        current_user_id: ID of the current user
        
    Returns:
        List of dictionaries containing loss leader stock information
    """
    try:
        loss_leaders = await get_loss_leaders(
            days_back=days_back,
            drop_threshold=drop_threshold,
            top_n=top_n,
            current_user_id=current_user_id,
            trading_client=trading_client
        )
        return loss_leaders
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving loss leaders: {str(e)}")
