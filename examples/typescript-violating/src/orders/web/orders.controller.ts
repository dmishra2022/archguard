import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { PlaceOrder } from '../application/place-order';
import { OrderEntity } from '../infrastructure/order.entity';
import { OrderResponse, PlaceOrderRequest } from './order.dto';

@Controller('orders')
export class OrdersController {
  constructor(
    private readonly placeOrder: PlaceOrder,
    @InjectRepository(OrderEntity) private readonly rows: Repository<OrderEntity>,
  ) {}

  @Post()
  async place(@Body() body: PlaceOrderRequest): Promise<OrderResponse> {
    const order = await this.placeOrder.execute(body.id, body.amountCents);
    return new OrderResponse(order.id, order.amountCents);
  }

  @Get(':id')
  async find(@Param('id') id: string): Promise<OrderEntity | null> {
    return this.rows.findOneBy({ id });
  }
}
