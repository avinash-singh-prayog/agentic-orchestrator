"""
Transaction RCA Agent Routers.
"""

from app.routers import health, agent, transactions, rca, tickets

health_router = health.router
agent_router = agent.router
transactions_router = transactions.router
rca_router = rca.router
tickets_router = tickets.router