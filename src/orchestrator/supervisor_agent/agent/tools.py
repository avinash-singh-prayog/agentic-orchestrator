"""
Supervisor Agent Tools - PineLabs Branch.
Only Transaction RCA Agent tool available.
"""
import logging
from langchain_core.tools import tool

# Import from app.client - this module is in agent/, client is in app/
import sys
import os

# Add parent directory to path for cross-package import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.transaction_rca_client import call_transaction_rca_via_slim

logger = logging.getLogger("supervisor_agent.tools")


@tool
async def call_transaction_rca_agent(transaction_context_json: str) -> str:
    """
    Call the Transaction RCA Agent to perform root cause analysis on an unprocessed transaction.
    IMPORTANT: The agent is stateless. The `transaction_context_json` must be a complete JSON string containing:
    - transaction_id: Unique transaction identifier
    - checkpoints: List of checkpoint objects with checkpoint_name, status, timestamp, details
    - merchant_config: Optional merchant configuration (TID, MDR, routing config)
    - merchant_data: Optional merchant master data (account, IFSC, bank details)
    - external_signals: Optional external dependency signals (bank health, rejections)
    - risk_indicators: Optional risk and compliance indicators
    - observational_notes: Optional observational notes
    
    The agent will return RCA analysis with classification, confidence, evidence, and human intervention prompt.
    """
    logger.info(f"Delegating to Transaction RCA Agent: {transaction_context_json[:100]}...")
    return await call_transaction_rca_via_slim(transaction_context_json)


SUPERVISOR_TOOLS = [call_transaction_rca_agent]

