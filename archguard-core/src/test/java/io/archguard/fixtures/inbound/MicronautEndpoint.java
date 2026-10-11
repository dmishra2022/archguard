package io.archguard.fixtures.inbound;

/**
 * Mirrors {@link WebEndpoint} / {@link RestResource} but uses Micronaut 4 HTTP annotations so the
 * importer can exercise the Micronaut path end-to-end: class-level stereotype detection and
 * method-level HTTP routing recognition.
 */
@io.micronaut.http.annotation.Controller("/micronaut-orders")
public class MicronautEndpoint {
  @io.micronaut.http.annotation.Get("/{id}")
  public io.archguard.fixtures.domain.MicronautEntity load(long id) {
    return null;
  }

  @io.micronaut.http.annotation.Post
  public String create() {
    return "";
  }

  // Non-endpoint helper to prove the method-level filter actually filters.
  public io.archguard.fixtures.domain.MicronautEntity internalHelper() {
    return null;
  }
}
