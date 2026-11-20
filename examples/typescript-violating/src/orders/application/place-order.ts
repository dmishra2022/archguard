import { Injectable } from '@nestjs/common';
import { Order } from '../domain/order';
import { TypeOrmOrderRepository } from '../infrastructure/typeorm-order-repository';

@Injectable()
export class PlaceOrder {
  constructor(private readonly orders: TypeOrmOrderRepository) {}

  async execute(id: string, amountCents: number): Promise<Order> {
    const order = Order.place(id, amountCents);
    await this.orders.save(order);
    return order;
  }
}
