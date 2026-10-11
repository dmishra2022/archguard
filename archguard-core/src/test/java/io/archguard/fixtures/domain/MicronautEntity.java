package io.archguard.fixtures.domain;

/**
 * Micronaut Data entity. The {@code @MappedEntity} annotation is mapped to the generic
 * {@code persistence.entity} tag by {@code FrameworkClassifier}, so the FW-002 HTTP-entity-leak
 * rule fires uniformly across JPA, Panache and Micronaut Data persistence stacks.
 */
@io.micronaut.data.annotation.MappedEntity
public class MicronautEntity {
  @io.micronaut.data.annotation.Id public long id;
}
