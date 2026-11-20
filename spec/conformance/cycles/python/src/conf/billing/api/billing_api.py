from typing import Protocol

from conf.orders.api import order_api


class BillingApi(Protocol):
    def billed_order(self) -> order_api.OrderApi: ...
