import { Body, Controller, Post } from '@nestjs/common';
import { PlaceOrder } from '../application/place-order';
import { OrderResponse, PlaceOrderRequest } from './order.dto';

@Controller('orders')
export class OrdersController {
  constructor(private readonly placeOrder: PlaceOrder) {}

  @Post()
  async place(@Body() body: PlaceOrderRequest): Promise<OrderResponse> {
    const order = await this.placeOrder.execute(body.id, body.amountCents);
    return new OrderResponse(order.id, order.amountCents);
  }
}
