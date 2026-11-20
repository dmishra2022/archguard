import type { Order } from '../../orders/domain/order';

export function invoiceFor(order: Order): string {
  return `invoice-${order.id}`;
}
