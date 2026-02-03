"""
Pytest configuration and fixtures.
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base, get_db
from database.models import (
    Transaction,
    RCAAnalysis,
    Ticket,
    AuditLog,
    SelfHealingAction,
)


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Create in-memory database
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def test_transaction(db_session):
    """Create a test transaction."""
    from datetime import datetime
    from database.models import TransactionStatus
    
    transaction = Transaction(
        transaction_id="TXN_TEST_001",
        merchant_id="MERCHANT_001",
        merchant_name="Test Merchant",
        transaction_value=1000.0,
        currency="INR",
        initiated_at=datetime.utcnow(),
        status=TransactionStatus.PENDING,
        checkpoints=[
            {"checkpoint_name": "ingestion", "status": "success"},
            {"checkpoint_name": "authorization", "status": "success"},
            {"checkpoint_name": "routing", "status": "pending"},
        ],
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction
