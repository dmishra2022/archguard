from conf.orders.domain import order
from conf.orders.port.order_store import OrderStore


class SqlOrderStore(OrderStore):
    def save(self, item: order.Order) -> None:
        del item
