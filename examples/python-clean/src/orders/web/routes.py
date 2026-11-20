from fastapi import APIRouter, Depends, HTTPException, status

from orders.application.place_order import PlaceOrder, PlaceOrderCommand
from orders.domain import OrderError
from orders.web.dependencies import get_place_order
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
