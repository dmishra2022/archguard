import { Order } from '@orders/domain/order';
import { SqlOrderStore } from '@orders/adapter/sql-order-store';

export class PlaceOrder {
  private readonly store = new SqlOrderStore();

  place(id: string): void {
    this.store.save(new Order(id));
  }
}
