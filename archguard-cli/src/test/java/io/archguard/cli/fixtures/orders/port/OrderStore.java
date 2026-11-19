package io.archguard.cli.fixtures.orders.port;

import io.archguard.cli.fixtures.orders.domain.Order;

public interface OrderStore {
  void save(Order order);
}
