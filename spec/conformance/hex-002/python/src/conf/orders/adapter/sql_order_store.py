from conf.orders.domain.order import Order
from conf.orders.port.order_store import OrderStore


class SqlOrderStore(OrderStore):
    def save(self, order: Order) -> None:
        del order
