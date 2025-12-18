# Booking Agent

AI-powered order creation and management agent using LangGraph and A2A protocol.

## Features

- Create shipping orders via Order V2 API
- Get order status and details
- Cancel orders with refund processing
- SLIM transport for inter-agent communication

## Running

```bash
# HTTP only
python -m booking_agent.app.main http

# SLIM only  
python -m booking_agent.app.main slim

# Dual mode (HTTP + SLIM)
python -m booking_agent.app.main dual
```

## API Endpoints

- `GET /booking/v1/health` - Health check
- `POST /booking/v1/agent/run` - Run the booking agent
