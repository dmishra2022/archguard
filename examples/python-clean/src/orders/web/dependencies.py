from orders.application.place_order import PlaceOrder


def get_place_order() -> PlaceOrder:
    raise NotImplementedError('PlaceOrder is wired in orders.main')
