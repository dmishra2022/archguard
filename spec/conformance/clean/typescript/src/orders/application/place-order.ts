import { Order } from '../domain/order.js';
import type { OrderStore } from '../port/order-store.js';

export class PlaceOrder {
  constructor(private readonly store: OrderStore) {}

  place(id: string): void {
    this.store.save(new Order(id));
  }
}
