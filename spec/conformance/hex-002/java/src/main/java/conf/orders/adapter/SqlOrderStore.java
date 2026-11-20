package conf.orders.adapter;

import conf.orders.domain.Order;
import conf.orders.port.OrderStore;

public class SqlOrderStore implements OrderStore {
  @Override
  public void save(Order order) {}
}
