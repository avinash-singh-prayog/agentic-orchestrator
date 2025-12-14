"""Mock Carrier - Booking Service."""

import asyncio
import logging
import random
import string
from datetime import datetime

from orchestrator.carrier_service.domain.models import CarrierCode, LabelResponse, ShipmentRequest

logger = logging.getLogger("carrier.mock.booking")


class MockBookingService:
    """Mock implementation of booking/label generation."""

    LABEL_BASE_URL = "https://mock-carrier.example.com/labels"

    def _generate_tracking_number(self) -> str:
        return f"MOCK{''.join(random.choices(string.digits, k=10))}"

    async def create_shipment(self, request: ShipmentRequest, service_code: str) -> LabelResponse:
        await asyncio.sleep(0.2)
        tracking_number = self._generate_tracking_number()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        label_url = f"{self.LABEL_BASE_URL}/{tracking_number}_{timestamp}.pdf"
        logger.info(f"Created shipment: {tracking_number} with service {service_code}")
        return LabelResponse(tracking_number=tracking_number, label_url=label_url, carrier=CarrierCode.MOCK)
