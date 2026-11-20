from ..domain.order import Order
from ..port.order_store import OrderStore


class PlaceOrder:
    def __init__(self, store: OrderStore) -> None:
        self._store = store

    def place(self, order_id: str) -> None:
        self._store.save(Order(order_id))
