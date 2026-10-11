package example.quarkus.web;

@javax.ws.rs.Path("/orders")
public class OrderResource {
  @javax.ws.rs.GET
  public String orders() {
    return "orders";
  }
}
