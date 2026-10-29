import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL

# Fallback to sqlite if postgres is not available or if running tests
if os.getenv("TESTING") or not db_url:
    db_url = "sqlite:///./smartgrid.db"

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Attempt to connect to check if database is online. If offline and it's postgres, fallback to sqlite.
try:
    engine = create_engine(
        db_url,
        pool_pre_ping=True if not db_url.startswith("sqlite") else False,
        connect_args=connect_args
    )
    if not db_url.startswith("sqlite"):
        # Test connection
        with engine.connect() as conn:
            pass
        print(f"Connected to database successfully: {db_url}")
except Exception as e:
    print(f"Database connection failed ({e}). Falling back to SQLite...")
    db_url = "sqlite:///./smartgrid.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        db_url,
        pool_pre_ping=False,
        connect_args=connect_args
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
