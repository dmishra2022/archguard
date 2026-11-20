from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from orders.domain import Order


class OrderLineIn(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PlaceOrderRequest(BaseModel):
    customer_id: str
    lines: List[OrderLineIn]


class OrderResponse(BaseModel):
    id: UUID
    customer_id: str
    total: Decimal

    @classmethod
    def from_domain(cls, order: Order) -> 'OrderResponse':
        return cls(id=order.id, customer_id=order.customer_id, total=order.total)
