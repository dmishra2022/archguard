import type { BillingApi } from '../../billing/api/billing-api';

export interface OrderApi {
  billing(): BillingApi;
}
