package conf.billing.api;

import conf.orders.api.OrderApi;

public interface BillingApi {
  void invoice(OrderApi orders);
}
