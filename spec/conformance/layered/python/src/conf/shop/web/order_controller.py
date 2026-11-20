from conf.shop.persistence.order_dao import OrderDao
from conf.shop.service.order_service import OrderService


class OrderController:
    def __init__(self) -> None:
        self._service = OrderService()
        self._dao = OrderDao()

    def count(self) -> int:
        return self._service.count() + self._dao.rows()
