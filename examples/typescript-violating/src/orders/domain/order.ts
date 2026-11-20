import { Logger } from '@nestjs/common';

export class Order {
  private static readonly log = new Logger('Order');

  private constructor(
    readonly id: string,
    readonly amountCents: number,
  ) {}

  static place(id: string, amountCents: number): Order {
    if (amountCents <= 0) throw new Error('Order amount must be positive');
    Order.log.log(`placing ${id}`);
    return new Order(id, amountCents);
  }
}
