import { OrderDao } from '../persistence/order-dao';

export class OrderService {
  count(): number {
    return new OrderDao().rows();
  }
}
