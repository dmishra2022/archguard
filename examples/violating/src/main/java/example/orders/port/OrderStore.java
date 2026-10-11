package example.orders.port;

public interface OrderStore {
  example.orders.domain.Order load(String id);
}
