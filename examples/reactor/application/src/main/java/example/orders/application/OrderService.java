package example.orders.application;

public class OrderService {
  public example.orders.domain.Order load(String id) {
    return new example.orders.domain.Order(id);
  }
}
