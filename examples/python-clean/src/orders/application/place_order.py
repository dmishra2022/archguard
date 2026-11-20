from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence, Tuple

from orders.domain import Order, OrderLine
from orders.ports.order_repository import OrderRepository


@dataclass(frozen=True)
class PlaceOrderCommand:
    customer_id: str
    lines: Sequence[Tuple[str, int, Decimal]]


class PlaceOrder:
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    def __call__(self, command: PlaceOrderCommand) -> Order:
        order = Order(command.customer_id, [OrderLine(sku, qty, price) for sku, qty, price in command.lines])
        self._repository.add(order)
        return order
