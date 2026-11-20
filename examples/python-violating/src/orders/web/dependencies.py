from sqlalchemy.orm import Session

from orders.application.place_order import PlaceOrder


def get_place_order() -> PlaceOrder:
    raise NotImplementedError('PlaceOrder is wired in orders.main')


def get_session() -> Session:
    raise NotImplementedError('Sessions are wired in orders.main')
