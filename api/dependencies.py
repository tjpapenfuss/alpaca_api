from typing import Optional, Dict, Any
import uuid
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import User, Account
from api.services.trading_client import get_alpaca_client
import re
from dotenv import load_dotenv
import os


# Replace with your actual JWT settings
SECRET_KEY = "your-secret-key"  # Should be in environment variables
ALGORITHM = "HS256"

def get_db_session():
    """Get a database session."""
    db = get_db()
    try:
        yield db
    finally:
        db.close()

# Default user ID for testing
DEFAULT_USER_ID = "test-user-id"

async def get_current_user_id() -> str:
    load_dotenv()
    # In a real app, I would get this from the auth token
    # For now, I'll just return a fixed user ID
    return os.getenv('user_id') 

async def get_current_account_id() -> str:
    load_dotenv()
    # In a real app, I would get this from the auth token
    # For now, I'll just return a fixed user ID
    return os.getenv('account_id')

def get_current_user(
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id)
) -> User:
    """Get the current user object."""
    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user

def get_user_account(
    account_id: str,
    db: Session = Depends(get_db_session),
    user_id: str = Depends(get_current_user_id)
) -> Account:
    """Get a user account and verify ownership."""
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == user_id
    ).first()
    
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or not owned by current user",
        )
    
    return account

def get_trading_client():
    """Get the trading client."""
    return get_alpaca_client()