"""
Domain Interfaces for Booking Agent.

Abstract Base Classes defining the contract for order operations.
Follows Interface Segregation Principle.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import (
    OrderRequest,
    OrderResponse,
    CancelRequest,
)


class IOrderCreator(ABC):
    """Interface for creating orders."""

    @abstractmethod
    async def create_order(
        self,
        order: OrderRequest,
        sync: bool = False,
    ) -> OrderResponse:
        """
        Create a new order.

        Args:
            order: Order details
            sync: Process synchronously if True

        Returns:
            OrderResponse with created order data
        """
        pass


class IOrderFetcher(ABC):
    """Interface for fetching order details."""

    @abstractmethod
    async def get_order(self, order_id: str) -> OrderResponse:
        """
        Get order by ID.

        Args:
            order_id: Unique order identifier

        Returns:
            OrderResponse with order data
        """
        pass

    @abstractmethod
    async def get_orders(
        self,
        page: int = 1,
        limit: int = 20,
        order_status: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> OrderResponse:
        """
        Get paginated list of orders.

        Args:
            page: Page number
            limit: Items per page
            order_status: Filter by status
            reference_id: Filter by reference ID

        Returns:
            OrderResponse with list of orders and pagination meta
        """
        pass


class IOrderCanceller(ABC):
    """Interface for cancelling orders."""

    @abstractmethod
    async def cancel_order(
        self,
        order_id: str,
        cancel_request: CancelRequest,
    ) -> OrderResponse:
        """
        Cancel an order.

        Args:
            order_id: Order to cancel
            cancel_request: Cancellation details

        Returns:
            OrderResponse with cancellation status
        """
        pass


class IOrderService(IOrderCreator, IOrderFetcher, IOrderCanceller):
    """
    Composite interface for complete order operations.

    Extends all order-related interfaces.
    """
    pass
