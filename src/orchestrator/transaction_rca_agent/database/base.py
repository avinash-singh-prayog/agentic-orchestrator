"""
Database base configuration and session management.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Database URL - REQUIRED
_raw_db_url = os.getenv("DATABASE_URL")
if not _raw_db_url:
    raise ValueError("DATABASE_URL environment variable is required but not set")

# Strip quotes that may be accidentally included in ECS task definitions
DATABASE_URL = _raw_db_url.strip('"').strip("'")

# Convert postgresql:// to postgresql+psycopg:// to use psycopg3 instead of psycopg2
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Database session context manager.
    
    Usage:
        with get_db() as db:
            # Use db session
            pass
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database - create all tables.
    Should be called at application startup.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")


def drop_db() -> None:
    """
    Drop all database tables.
    Use with caution - only for development/testing.
    """
    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped.")
