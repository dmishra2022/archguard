from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4


class OrderError(ValueError):
    """A business rule of the order aggregate was violated."""


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise OrderError('quantity must be positive')

    @property
    def total(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Order:
    customer_id: str
    lines: List[OrderLine]
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.lines:
            raise OrderError('an order needs at least one line')

    @property
    def total(self) -> Decimal:
        return sum((line.total for line in self.lines), Decimal('0'))
