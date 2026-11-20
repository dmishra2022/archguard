from typing import Optional, Protocol
from uuid import UUID

from orders.domain import Order


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: UUID) -> Optional[Order]: ...
