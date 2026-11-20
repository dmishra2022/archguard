import type { Order } from '@orders/domain/order';

export interface OrderStore {
  save(order: Order): void;
}
