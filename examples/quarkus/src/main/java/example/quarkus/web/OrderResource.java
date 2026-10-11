package example.quarkus.web;

@jakarta.ws.rs.Path("/orders")
public class OrderResource {
  @jakarta.ws.rs.GET
  public String orders() {
    return "orders";
  }
}
