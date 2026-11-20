import type { OrderApi } from '../../orders/api/order-api';

export interface BillingApi {
  billedOrder(): OrderApi;
}
