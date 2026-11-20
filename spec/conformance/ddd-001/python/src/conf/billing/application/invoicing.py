import conf.orders.domain.order as order_model


def invoice_for(order: order_model.Order) -> str:
    return f'invoice-{order.id}'
