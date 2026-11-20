from conf.orders.adapter.sql_order_store import SqlOrderStore
from conf.orders.domain.order import Order


class PlaceOrder:
    def __init__(self) -> None:
        self._store = SqlOrderStore()

    def place(self, order_id: str) -> None:
        self._store.save(Order(order_id))
