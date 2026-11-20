package example.orders.application;

public class OrderService {
  private final example.orders.adapter.SqlOrderStore store;

  public OrderService(example.orders.adapter.SqlOrderStore store) {
    this.store = store;
  }

  public example.orders.domain.Order load(String id) {
    return store.load(id);
  }
}
