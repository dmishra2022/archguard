package conf.shop.web;

import conf.shop.model.ProductEntity;
import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

@Path("/products")
public class ProductResource {
  @GET
  public ProductEntity get() {
    return new ProductEntity();
  }
}
