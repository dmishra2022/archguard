package conf.shop.web;

import conf.shop.persistence.OrderDao;
import conf.shop.service.OrderService;

public class OrderController {
  private final OrderService service = new OrderService();
  private final OrderDao dao = new OrderDao();

  public int count() {
    return service.count() + dao.rows();
  }
}
