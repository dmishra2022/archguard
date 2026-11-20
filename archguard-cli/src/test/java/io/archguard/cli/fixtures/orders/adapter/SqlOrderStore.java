package io.archguard.cli.fixtures.orders.adapter;

import io.archguard.cli.fixtures.orders.domain.Order;
import io.archguard.cli.fixtures.orders.port.OrderStore;

public final class SqlOrderStore implements OrderStore {
  @Override
  public void save(Order order) {}
}
