"""
Aramex HTTP Client.

Async HTTP client with retry logic for Aramex API calls.
"""

import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Any, Dict, Optional

import httpx

from orchestrator.carrier_service.services.carriers.implementations.aramex.config import AramexConfig

logger = logging.getLogger("carrier.aramex.client")


class AramexClientError(Exception):
    """Base exception for Aramex client errors."""

    pass


class AramexAuthError(AramexClientError):
    """Authentication error (401)."""

    pass


class AramexClient:
    """Async HTTP client for Aramex API with retry logic."""

    SERVICEABILITY_ENDPOINT = "/ShippingAPI.V2/Location/Service_1_0.svc/json/IsAddressServiced"

    def __init__(self, config: AramexConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request_with_retry(
        self, method: str, endpoint: str, json_data: Dict[str, Any]
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry on 5xx errors."""
        client = await self._get_client()
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.request(
                    method=method,
                    url=endpoint,
                    json=json_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/xml",
                    },
                )

                # Check for auth errors
                if response.status_code == 401:
                    raise AramexAuthError("Invalid Aramex credentials")

                # Retry on 5xx errors
                if response.status_code >= 500:
                    if attempt < self.config.max_retries:
                        delay = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Aramex API returned {response.status_code}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{self.config.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    response.raise_for_status()

                return response

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    delay = 2**attempt
                    logger.warning(f"Request failed: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise AramexClientError(f"Request failed after {self.config.max_retries} retries: {e}")

        raise last_exception or AramexClientError("Unknown error")

    def _parse_serviceability_response(self, xml_content: str) -> Dict[str, Any]:
        """Parse XML serviceability response."""
        try:
            root = ET.fromstring(xml_content)

            # Handle namespaces - Aramex may use namespaces
            # Try to find elements with and without namespace
            has_errors = False
            is_serviced = False

            for elem in root.iter():
                tag_name = elem.tag.split("}")[-1]  # Remove namespace prefix
                if tag_name == "HasErrors":
                    has_errors = elem.text.lower() == "true" if elem.text else False
                elif tag_name == "IsServiced":
                    is_serviced = elem.text.lower() == "true" if elem.text else False

            return {"has_errors": has_errors, "is_serviced": is_serviced}

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML response: {e}")
            raise AramexClientError(f"Invalid XML response: {e}")

    async def check_serviceability(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check address serviceability with Aramex API.

        Args:
            request_data: Full Aramex API request structure

        Returns:
            Dict with 'has_errors' and 'is_serviced' keys
        """
        logger.debug(f"Checking serviceability: {request_data.get('Address', {}).get('PostCode')}")

        response = await self._request_with_retry(
            method="POST",
            endpoint=self.SERVICEABILITY_ENDPOINT,
            json_data=request_data,
        )

        result = self._parse_serviceability_response(response.text)
        logger.info(
            f"Serviceability result for {request_data.get('Address', {}).get('PostCode')}: "
            f"is_serviced={result['is_serviced']}"
        )
        return result
