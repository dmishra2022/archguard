from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from conf.orders.domain.order import Order


class OrderStore(Protocol):
    def save(self, order: Order) -> None: ...
