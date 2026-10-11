package io.archguard.fixtures.out;

/**
 * Micronaut Data repository recognised by ancestry alone: extending {@link
 * io.micronaut.data.repository.CrudRepository} is enough to earn the {@code micronaut.repository}
 * tag even without an {@code @Repository} annotation on the interface.
 */
public interface MicronautRepository
    extends io.micronaut.data.repository.CrudRepository<
        io.archguard.fixtures.domain.MicronautEntity, Long> {}
