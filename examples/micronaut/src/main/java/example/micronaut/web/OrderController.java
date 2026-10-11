package example.micronaut.web;

@io.micronaut.http.annotation.Controller("/orders")
public class OrderController {
  @io.micronaut.http.annotation.Get
  public String orders() {
    return "orders";
  }
}
