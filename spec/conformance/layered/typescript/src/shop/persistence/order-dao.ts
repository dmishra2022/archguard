import type { OrderService } from '../service/order-service';

export class OrderDao {
  rows(): number {
    return 0;
  }

  owner(): OrderService | null {
    return null;
  }
}
