package conf.shop.service;

import conf.shop.persistence.OrderDao;

public class OrderService {
  public int count() {
    return new OrderDao().rows();
  }
}
