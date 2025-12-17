"""
Order API HTTP Client.

HTTP client for communicating with Order V2 APIs.
"""

import logging
from typing import Optional, Dict, Any

import httpx

from ...config.settings import settings
from ...domain.models import (
    OrderRequest,
    OrderResponse,
    CancelRequest,
)
from ...domain.interfaces import IOrderService
from ...domain.exceptions import OrderAPIError, OrderNotFoundError


logger = logging.getLogger("booking_agent.order_client")


class OrderClient(IOrderService):
    """HTTP client for Order V2 API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[int] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.base_url = (base_url or settings.order_api_url).rstrip("/")
        self.timeout = timeout or settings.order_api_timeout
        self.tenant_id = tenant_id or settings.default_tenant_id
        self.user_id = user_id or settings.default_user_id
        self.source = settings.source
        
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.tenant_id:
            headers["x-tenant-id"] = self.tenant_id
        if self.user_id:
            headers["x-user-id"] = self.user_id
        if self.source:
            headers["x-source"] = self.source
        return headers

    async def create_order(
        self,
        order: OrderRequest,
        sync: bool = False,
    ) -> OrderResponse:
        """
        Create a new order via Order V2 API.
        
        Args:
            order: Order request details
            sync: Process synchronously if True
            
        Returns:
            OrderResponse with created order data
        """
        url = f"{self.base_url}/v2/orders"
        params = {"sync": str(sync).lower()} if sync else {}
        
        logger.info(f"Creating order: {order.orderId}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=order.model_dump(mode="json", exclude_none=True),
                    headers=self._get_headers(),
                    params=params,
                )
                
                data = response.json()
                
                if response.status_code in (200, 201, 202):
                    logger.info(f"Order created successfully: {order.orderId}")
                    return OrderResponse(
                        success=True,
                        statusCode=response.status_code,
                        message=data.get("message", "Order created successfully"),
                        data=data.get("data"),
                    )
                else:
                    error_msg = data.get("message", f"Failed with status {response.status_code}")
                    logger.error(f"Order creation failed: {error_msg}")
                    raise OrderAPIError(error_msg, response.status_code)
                    
        except httpx.TimeoutException:
            raise OrderAPIError("Request timeout while creating order")
        except httpx.RequestError as e:
            raise OrderAPIError(f"Request error: {str(e)}")

    async def get_order(self, order_id: str) -> OrderResponse:
        """
        Get order by ID.
        
        Args:
            order_id: Unique order identifier
            
        Returns:
            OrderResponse with order data
        """
        url = f"{self.base_url}/v2/orders/{order_id}"
        
        logger.info(f"Fetching order: {order_id}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                )
                
                data = response.json()
                
                if response.status_code == 200:
                    return OrderResponse(
                        success=True,
                        statusCode=200,
                        message="Order retrieved successfully",
                        data=data.get("data"),
                    )
                elif response.status_code == 404:
                    raise OrderNotFoundError(f"Order not found: {order_id}")
                else:
                    error_msg = data.get("message", f"Failed with status {response.status_code}")
                    raise OrderAPIError(error_msg, response.status_code)
                    
        except httpx.TimeoutException:
            raise OrderAPIError("Request timeout while fetching order")
        except httpx.RequestError as e:
            raise OrderAPIError(f"Request error: {str(e)}")

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
            OrderResponse with list of orders
        """
        url = f"{self.base_url}/v2/orders"
        params: Dict[str, Any] = {"page": page, "limit": limit}
        
        if order_status:
            params["orderStatus"] = order_status
        if reference_id:
            params["referenceId"] = reference_id
            
        logger.info(f"Fetching orders: page={page}, limit={limit}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                )
                
                data = response.json()
                
                if response.status_code == 200:
                    return OrderResponse(
                        success=True,
                        statusCode=200,
                        message="Orders retrieved successfully",
                        data=data.get("data"),
                        meta=data.get("meta"),
                    )
                else:
                    error_msg = data.get("message", f"Failed with status {response.status_code}")
                    raise OrderAPIError(error_msg, response.status_code)
                    
        except httpx.TimeoutException:
            raise OrderAPIError("Request timeout while fetching orders")
        except httpx.RequestError as e:
            raise OrderAPIError(f"Request error: {str(e)}")

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
        url = f"{self.base_url}/v2/orders/{order_id}/cancel"
        
        logger.info(f"Cancelling order: {order_id}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=cancel_request.model_dump(mode="json", exclude_none=True),
                    headers=self._get_headers(),
                )
                
                data = response.json()
                
                if response.status_code == 200:
                    logger.info(f"Order cancelled successfully: {order_id}")
                    return OrderResponse(
                        success=True,
                        statusCode=200,
                        message=data.get("message", "Order cancelled successfully"),
                        data=data.get("data"),
                    )
                elif response.status_code == 404:
                    raise OrderNotFoundError(f"Order not found: {order_id}")
                else:
                    error_msg = data.get("message", f"Failed with status {response.status_code}")
                    raise OrderAPIError(error_msg, response.status_code)
                    
        except httpx.TimeoutException:
            raise OrderAPIError("Request timeout while cancelling order")
        except httpx.RequestError as e:
            raise OrderAPIError(f"Request error: {str(e)}")
