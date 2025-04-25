# import strawberry
# from fastapi import FastAPI, Depends, HTTPException
# from strawberry.fastapi import GraphQLRouter
# from typing import List, Optional, TypeVar, Generic, Callable, Any, Dict
# import base64
# import json
# import sys
# from datetime import datetime, date, timedelta
# import os
# import uvicorn

# # Add parent directory to path to import your SQL functions
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# # Import Alpaca Trading Client
# from alpaca.trading.client import TradingClient

# # Assuming these functions are defined elsewhere in your project
# from SQL_scripts.buy_sell import insert_orders, buy_entries_for_tickers, get_all_symbols, get_account_positions
# from trading.trade_report import report, get_orders_v2
# from utils.stock_data import get_stock_data, find_top_loss_stocks
# from api.utils.pagination import paginate_results, Connection
# import config  # Assuming you have a config module with your Alpaca API keys

# @strawberry.type
# class Symbol:
#     symbol: str

# @strawberry.type
# class Position:
#     buy_order_id: str
#     symbol: str
#     buy_price: float
#     original_quantity: float
#     remaining_quantity: float
#     buy_datetime: datetime

# @strawberry.type
# class LossLeader:
#     symbol: str
#     percentage_drop: float
#     buy_price: float
#     current_price: float
#     quantity: float
#     dollar_loss: float
 
# # Define current user dependency
# async def get_current_user_id() -> str:
#     # In a real app, I would get this from the auth token
#     # For now, I'll just return a fixed user ID
#     return config.user_id 

# def get_trading_client() -> TradingClient:
#     """Create and return an Alpaca Trading client."""
#     return TradingClient(config.ALPACA_API_KEY, config.ALPACA_API_SECRET, paper=True)

# # Define GraphQL queries
# @strawberry.type
# class Query:
#     @strawberry.field
#     def symbols(self, user_id: str = strawberry.field(default_factory=get_current_user_id)) -> List[Symbol]:
#         symbols_list = get_all_symbols(user_id) 
#         return [Symbol(symbol=s) for s in symbols_list]
    
#     @strawberry.field
#     def position(self, symbol: str, user_id: str = strawberry.field(default_factory=get_current_user_id)) -> Optional[Position]:
#         positions_list = get_account_positions(user_id)
#         for p in positions_list:
#             if p["symbol"] == symbol:
#                 return Position(
#                     buy_order_id=p["buy_order_id"],
#                     symbol=p["symbol"],
#                     buy_price=p["buy_price"],
#                     original_quantity=p["original_quantity"],
#                     remaining_quantity=p["remaining_quantity"],
#                     buy_datetime=p["buy_datetime"]
#                 )
#         return None
    
#     @strawberry.field
#     def positions(
#         self, 
#         first: Optional[int] = 10,
#         after: Optional[str] = None,
#         user_id: str = strawberry.field(default_factory=get_current_user_id)
#     ) -> Connection[Position]:
#         """Get paginated account positions."""
#         # Get all positions
#         all_positions = get_account_positions(user_id)
        
#         # Use the utility function for pagination
#         return paginate_results(
#             items=all_positions,
#             first=first,
#             after=after,
#             converter_func=lambda p: Position(
#                 buy_order_id=p["buy_order_id"],
#                 symbol=p["symbol"],
#                 buy_price=p["buy_price"],
#                 original_quantity=p["original_quantity"],
#                 remaining_quantity=p["remaining_quantity"],
#                 buy_datetime=p["buy_datetime"]
#             )
#         )

#     @strawberry.field
#     async def loss_leaders(
#         self, 
#         first: Optional[int] = 10,
#         after: Optional[str] = None,
#         days_back: Optional[int] = 1,
#         drop_threshold: Optional[float] = 10.0,
#         user_id: str = strawberry.field(default_factory=get_current_user_id)
#     ) -> Connection[LossLeader]:
#         """Get paginated loss leader stocks."""
#         # Get loss leaders using your existing function
#         trading_client = get_trading_client()
#         all_loss_leaders = await get_loss_leaders(
#             days_back=days_back,
#             drop_threshold=drop_threshold,
#             top_n=100,  # Get more than needed for pagination
#             current_user_id=user_id,
#             trading_client=trading_client
#         )

#         # Use the utility function for pagination
#         return paginate_results(
#             items=all_loss_leaders,
#             first=first,
#             after=after,
#             converter_func=lambda item: LossLeader(
#                 symbol=item["symbol"],
#                 percentage_drop=item["percentage_drop"],
#                 buy_price=item["buy_price"],
#                 current_price=item["current_price"],
#                 quantity=item["quantity"],
#                 dollar_loss=item["dollar_loss"]
#             )
#         )
# # Create schema and GraphQL router
# schema = strawberry.Schema(query=Query)
# graphql_app = GraphQLRouter(schema)

# # Create FastAPI app
# app = FastAPI(title="Account Positions API")
# from fastapi.middleware.cors import CORSMiddleware

# # Update this in your app definition
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],  # Add your frontend URL here
#     allow_credentials=True,
#     allow_methods=["GET", "POST", "OPTIONS"],  # Make sure OPTIONS is included
#     allow_headers=["*"],  # Or specify the headers you want to allow
# )

# app.include_router(graphql_app, prefix="/graphql")


# @app.get("/")
# def read_root():
#     return {"message": "Welcome to Account Positions API. Visit /graphql for the GraphQL interface."}


# @app.get("/loss_leaders", response_model=List[Dict[str, Any]])
# async def get_loss_leaders(
#     days_back: Optional[int] = 1,
#     drop_threshold: Optional[float] = 10.0,
#     top_n: Optional[int] = 5,
#     trading_client: TradingClient = Depends(get_trading_client),
#     current_user_id: str = strawberry.field(default_factory=get_current_user_id)
# ):
#     """
#     Get the top stocks with the most significant losses.
    
#     Args:
#         days_back: How many days to look back for start date (default: 1)
#         drop_threshold: Percentage threshold for considering a stock as a loss leader (default: 10.0%)
#         top_n: Number of top loss leaders to return (default: 5)
#         trading_client: Alpaca trading client dependency
#         current_user_id: ID of the current user
        
#     Returns:
#         List of dictionaries containing loss leader stock information
#     """
#     try:
#         today = date.today().strftime("%Y-%m-%d")
#         start_date = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
#         # Get all available tickers for the user
#         tickers = get_all_symbols(user_id=config.user_id)
#         pickle_file = f"C:/Users/tjpap/sandbox/alpaca_api/pickle_files/test-{len(tickers)}-{start_date}-{today}.pkl"
#         prices_df = get_stock_data(start_date=start_date,
#                                end_date=today,
#                                tickers=tickers,
#                                # tickers_source=config.yfinance_config.get('tickers_source'),
#                                top_n=len(tickers),
#                                pickle_file=pickle_file
#                                )
#         print(current_user_id)
#         print(prices_df)
#         buys_df = buy_entries_for_tickers(user_id=current_user_id, df=prices_df)
        
#         # Find top loss leaders
#         loss_leaders = find_top_loss_stocks(buys_df, prices_df, drop_threshold=drop_threshold, top=top_n)
#         return loss_leaders
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error retrieving loss leaders: {str(e)}")

if __name__ == "__main__":
    from api.main import app
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000)