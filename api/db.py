"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from dotenv import load_dotenv

load_dotenv()

# Get database configuration from environment variables
db_config = {
    'host': os.getenv('db_config.host', 'localhost'),
    'dbname': os.getenv('db_config.dbname'),
    'user': os.getenv('db_config.user'),
    'password': os.getenv('db_config.password'),
    'port': int(os.getenv('db_config.port'))
}

# Build the connection string based on environment variable or config
if os.getenv("DATABASE_URL"):
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # Format for PostgreSQL
    DATABASE_URL = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    
    # Keep SQLite as fallback if needed
    if not all([db_config['user'], db_config['dbname']]):
        DATABASE_URL = "sqlite:///./sql_app.db"

# Different connection arguments for different database types
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Dependency to get database session.
    
    Yields:
        Session: A SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()