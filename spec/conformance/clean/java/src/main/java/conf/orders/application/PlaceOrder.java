package conf.orders.application;

import conf.orders.domain.Order;
import conf.orders.port.OrderStore;

public class PlaceOrder {
  private final OrderStore store;

  public PlaceOrder(OrderStore store) {
    this.store = store;
  }

  public void place(String id) {
    store.save(new Order(id));
  }
}
