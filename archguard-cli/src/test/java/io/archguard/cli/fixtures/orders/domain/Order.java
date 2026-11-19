package io.archguard.cli.fixtures.orders.domain;

public final class Order {
  private final String id;

  public Order(String id) {
    this.id = id;
  }

  public String id() {
    return id;
  }
}
