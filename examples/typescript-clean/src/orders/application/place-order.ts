import { Inject, Injectable } from '@nestjs/common';
import { Order } from '../domain/order';
import { ORDER_REPOSITORY, type OrderRepository } from './ports/order-repository';

@Injectable()
export class PlaceOrder {
  constructor(@Inject(ORDER_REPOSITORY) private readonly orders: OrderRepository) {}

  async execute(id: string, amountCents: number): Promise<Order> {
    const order = Order.place(id, amountCents);
    await this.orders.save(order);
    return order;
  }
}
