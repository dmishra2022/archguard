package io.archguard.fixtures.inbound;

@org.springframework.web.bind.annotation.RestController
public class WebEndpoint {
  @org.springframework.web.bind.annotation.GetMapping("/orders")
  public java.util.List<io.archguard.fixtures.domain.JpaEntity> load() {
    return java.util.List.of();
  }

  public io.archguard.fixtures.domain.JpaEntity internalHelper() {
    return null;
  }
}
