package io.archguard.cli.fixtures.orders.application;

import io.archguard.cli.fixtures.orders.adapter.SqlOrderStore;
import io.archguard.cli.fixtures.orders.domain.Order;

public final class PlaceOrder {
  private final SqlOrderStore store = new SqlOrderStore();

  public void place(String id) {
    store.save(new Order(id));
  }
}
