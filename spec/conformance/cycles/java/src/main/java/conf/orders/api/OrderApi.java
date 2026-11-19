package conf.orders.api;

import conf.billing.api.BillingApi;

public interface OrderApi {
  void markPaid(BillingApi billing);
}
