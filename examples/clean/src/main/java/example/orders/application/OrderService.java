package example.orders.application;

public class OrderService {
  private final example.orders.port.OrderStore store;

  public OrderService(example.orders.port.OrderStore store) {
    this.store = store;
  }

  public example.orders.domain.Order load(String id) {
    return store.load(id);
  }
}
