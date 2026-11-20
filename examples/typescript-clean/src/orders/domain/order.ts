export class Order {
  private constructor(
    readonly id: string,
    readonly amountCents: number,
  ) {}

  static place(id: string, amountCents: number): Order {
    if (amountCents <= 0) throw new Error('Order amount must be positive');
    return new Order(id, amountCents);
  }
}
