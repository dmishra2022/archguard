package example.orders.domain;

public record Order(String id) {
  public Order {
    if (id == null || id.isBlank()) throw new IllegalArgumentException("Order id is required");
  }
}
