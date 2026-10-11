package example.boot.web;

@org.springframework.web.bind.annotation.RestController
public class OrderController {
  @org.springframework.web.bind.annotation.GetMapping("/orders")
  public String orders() {
    return "orders";
  }
}
