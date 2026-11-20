export class PlaceOrderRequest {
  id!: string;
  amountCents!: number;
}

export class OrderResponse {
  constructor(
    readonly id: string,
    readonly amountCents: number,
  ) {}
}
