"""
Mock Carrier - Booking Service.

Simulates shipment creation and label generation for testing purposes.
"""

import asyncio
import logging
import random
import string
from datetime import datetime

from orchestrator.carrier_service.domain.models import (
    CarrierType,
    LabelResponse,
    ShipmentRequest,
)

logger = logging.getLogger("carrier.mock.booking")


class MockBookingService:
    """Mock implementation of booking/label generation."""

    # Base URL for mock labels
    LABEL_BASE_URL = "https://mock-carrier.example.com/labels"

    def _generate_tracking_number(self) -> str:
        """Generate a random tracking number."""
        random_suffix = "".join(random.choices(string.digits, k=10))
        return f"MOCK{random_suffix}"

    async def create_shipment(
        self, request: ShipmentRequest, service_code: str
    ) -> LabelResponse:
        """
        Create a shipment and generate a label.

        For mock: Generates a random tracking number and fake label URL.
        """
        # Simulate network latency for API call
        await asyncio.sleep(0.2)

        tracking_number = self._generate_tracking_number()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        label_url = f"{self.LABEL_BASE_URL}/{tracking_number}_{timestamp}.pdf"

        logger.info(
            f"Created shipment: {tracking_number} with service {service_code}"
        )

        return LabelResponse(
            tracking_number=tracking_number,
            label_url=label_url,
            carrier=CarrierType.MOCK,
        )
