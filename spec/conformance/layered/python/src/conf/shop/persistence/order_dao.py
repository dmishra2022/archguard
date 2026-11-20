from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from conf.shop.service.order_service import OrderService


class OrderDao:
    def rows(self) -> int:
        return 0

    def owner(self) -> Optional[OrderService]:
        return None
