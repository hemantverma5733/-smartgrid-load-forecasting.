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

engine = create_engine(
    db_url,
    pool_pre_ping=True if not db_url.startswith("sqlite") else False,
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
