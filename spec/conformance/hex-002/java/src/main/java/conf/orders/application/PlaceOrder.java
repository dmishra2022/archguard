package conf.orders.application;

import conf.orders.adapter.SqlOrderStore;
import conf.orders.domain.Order;

public class PlaceOrder {
  private final SqlOrderStore store = new SqlOrderStore();

  public void place(String id) {
    store.save(new Order(id));
  }
}
