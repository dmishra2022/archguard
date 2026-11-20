from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from conf.billing.api.billing_api import BillingApi


class OrderApi(Protocol):
    def billing(self) -> BillingApi: ...
