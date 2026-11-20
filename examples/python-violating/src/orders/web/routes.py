from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from orders.application.place_order import PlaceOrder, PlaceOrderCommand
from orders.domain import OrderError
from orders.infrastructure.models import OrderRecord
from orders.web.dependencies import get_place_order, get_session
from orders.web.schemas import OrderResponse, PlaceOrderRequest

router = APIRouter(prefix='/orders', tags=['orders'])


@router.post('', response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(body: PlaceOrderRequest, place: PlaceOrder = Depends(get_place_order)) -> OrderResponse:
    command = PlaceOrderCommand(body.customer_id, [(line.sku, line.quantity, line.unit_price) for line in body.lines])
    try:
        order = place(command)
    except OrderError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    return OrderResponse.from_domain(order)


@router.get('/{order_id}')
def get_order(order_id: str, session: Session = Depends(get_session)) -> OrderRecord:
    record = session.get(OrderRecord, order_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return record
