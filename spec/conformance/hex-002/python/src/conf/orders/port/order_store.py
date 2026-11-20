from typing import Protocol

from conf.orders.domain.order import Order


class OrderStore(Protocol):
    def save(self, order: Order) -> None: ...
