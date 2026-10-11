package io.archguard.framework;

import com.tngtech.archunit.core.domain.JavaClass;
import java.util.*;

/** Classification signals only; no assertion that a bean is active or a DI target resolved. */
public final class FrameworkClassifier {
  private FrameworkClassifier() {}

  public static Set<String> tags(JavaClass c) {
    Set<String> tags = new TreeSet<>();
    if (has(c, "org.springframework.web.bind.annotation.RestController")
        || has(c, "org.springframework.stereotype.Controller")) tags.add("spring.endpoint");
    if (has(c, "org.springframework.stereotype.Service")) tags.add("spring.service");
    if (has(c, "org.springframework.stereotype.Repository")
        || c.getAllRawInterfaces().stream()
            .anyMatch(i -> i.getName().equals("org.springframework.data.repository.Repository")))
      tags.add("spring.repository");
    if (has(c, "org.springframework.context.annotation.Configuration"))
      tags.add("spring.configuration");
    if (has(c, "jakarta.ws.rs.Path") || has(c, "javax.ws.rs.Path")) tags.add("jaxrs.endpoint");
    if (has(c, "jakarta.enterprise.context.ApplicationScoped")
        || has(c, "javax.enterprise.context.ApplicationScoped")) tags.add("cdi.bean");
    if (has(c, "jakarta.persistence.Entity") || has(c, "javax.persistence.Entity"))
      tags.add("persistence.entity");
    if (c.getAllRawSuperclasses().stream()
        .anyMatch(s -> s.getName().startsWith("io.quarkus.hibernate.orm.panache.")))
      tags.add("quarkus.panache");
    if (has(c, "io.micronaut.http.annotation.Controller")) tags.add("micronaut.endpoint");
    if (has(c, "io.micronaut.context.annotation.Factory")) tags.add("micronaut.factory");
    if (has(c, "io.micronaut.context.annotation.Bean")
        || has(c, "io.micronaut.context.annotation.Prototype")
        || has(c, "io.micronaut.context.annotation.Context"))
      tags.add("micronaut.bean");
    if (has(c, "io.micronaut.context.annotation.ConfigurationProperties"))
      tags.add("micronaut.configuration");
    if (has(c, "io.micronaut.data.annotation.Repository")
        || has(c, "io.micronaut.data.jdbc.annotation.JdbcRepository")
        || has(c, "io.micronaut.data.mongodb.annotation.MongoRepository")
        || c.getAllRawInterfaces().stream()
            .anyMatch(i -> i.getName().startsWith("io.micronaut.data.repository.")))
      tags.add("micronaut.repository");
    if (has(c, "io.micronaut.serde.annotation.Serdeable")) tags.add("micronaut.serde");
    if (has(c, "io.micronaut.data.annotation.MappedEntity")) tags.add("persistence.entity");
    return Set.copyOf(tags);
  }

  private static boolean has(JavaClass c, String annotation) {
    return c.isAnnotatedWith(annotation) || c.isMetaAnnotatedWith(annotation);
  }
}
