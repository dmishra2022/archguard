package conf.orders.port;

import conf.orders.domain.Order;

public interface OrderStore {
  void save(Order order);
}
