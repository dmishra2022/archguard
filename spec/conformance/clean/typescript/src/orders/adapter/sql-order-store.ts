import type { Order } from '../domain/order.js';
import type { OrderStore } from '../port/order-store.js';

export class SqlOrderStore implements OrderStore {
  save(order: Order): void {
    void order;
  }
}
