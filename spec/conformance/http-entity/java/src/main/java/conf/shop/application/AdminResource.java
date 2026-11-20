package conf.shop.application;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;

@Path("/admin")
public class AdminResource {
  @GET
  public String status() {
    return "ok";
  }
}
