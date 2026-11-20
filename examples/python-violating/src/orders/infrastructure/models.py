from decimal import Decimal
from typing import List

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class OrderRecord(Base):
    __tablename__ = 'orders'

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64))
    lines: Mapped[List['OrderLineRecord']] = relationship(cascade='all, delete-orphan', lazy='selectin')


class OrderLineRecord(Base):
    __tablename__ = 'order_lines'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey('orders.id'))
    sku: Mapped[str] = mapped_column(String(64))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
