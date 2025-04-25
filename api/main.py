from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from api.db import engine, Base
from api.schemas import schema
# Import all models to ensure they're registered with SQLAlchemy
from api.models import (
    User, Account, Transaction, TransactionPair, 
    Position, HarvestRecommendation, StockCorrelation, LegacyStockData
)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Create GraphQL app
graphql_app = GraphQLRouter(schema)

# Create FastAPI app
app = FastAPI(
    title="Stock Portfolio API",
    description="API for managing stock portfolios and tax-loss harvesting",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you'd want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GraphQL endpoint
app.include_router(graphql_app, prefix="/graphql")

# Add health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}