import type { Order } from '../domain/order.js';

export interface OrderStore {
  save(order: Order): void;
}
