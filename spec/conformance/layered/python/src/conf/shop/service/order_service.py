from conf.shop.persistence.order_dao import OrderDao


class OrderService:
    def count(self) -> int:
        return OrderDao().rows()
