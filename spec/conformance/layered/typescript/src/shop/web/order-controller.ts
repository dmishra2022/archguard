import { OrderDao } from '../persistence/order-dao';
import { OrderService } from '../service/order-service';

export class OrderController {
  private readonly service = new OrderService();
  private readonly dao = new OrderDao();

  count(): number {
    return this.service.count() + this.dao.rows();
  }
}
