from typing import Callable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from orders.domain import Order, OrderLine
from orders.infrastructure.models import OrderLineRecord, OrderRecord


class SqlAlchemyOrderRepository:
    """Implements orders.ports.order_repository.OrderRepository with SQLAlchemy."""

    def __init__(self, sessions: Callable[[], Session]) -> None:
        self._sessions = sessions

    def add(self, order: Order) -> None:
        record = OrderRecord(
            id=str(order.id),
            customer_id=order.customer_id,
            lines=[OrderLineRecord(sku=l.sku, quantity=l.quantity, unit_price=l.unit_price) for l in order.lines],
        )
        with self._sessions() as session, session.begin():
            session.add(record)

    def get(self, order_id: UUID) -> Optional[Order]:
        with self._sessions() as session:
            record = session.get(OrderRecord, str(order_id))
            if record is None:
                return None
            lines = [OrderLine(l.sku, l.quantity, l.unit_price) for l in record.lines]
            return Order(record.customer_id, lines, UUID(record.id))
