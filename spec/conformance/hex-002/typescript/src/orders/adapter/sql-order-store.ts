import type { Order } from '@orders/domain/order';
import type { OrderStore } from '@orders/port/order-store';

export class SqlOrderStore implements OrderStore {
  save(order: Order): void {
    void order;
  }
}
