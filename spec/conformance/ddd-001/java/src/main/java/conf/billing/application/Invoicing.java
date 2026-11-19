package conf.billing.application;

import conf.orders.domain.Order;

public class Invoicing {
  public String invoiceFor(Order order) {
    return "invoice-" + order.id();
  }
}
