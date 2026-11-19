package conf.shop.model;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;

@Entity
public class ProductEntity {
  @Id public Long id;
}
