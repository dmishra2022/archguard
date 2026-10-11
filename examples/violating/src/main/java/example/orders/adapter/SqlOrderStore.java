package example.orders.adapter;

public class SqlOrderStore implements example.orders.port.OrderStore {
  public example.orders.domain.Order load(String id) {
    return new example.orders.domain.Order(id);
  }
}
