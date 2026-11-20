import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Order } from '../domain/order';
import type { OrderRepository } from '../application/ports/order-repository';
import { OrderEntity } from './order.entity';

@Injectable()
export class TypeOrmOrderRepository implements OrderRepository {
  constructor(@InjectRepository(OrderEntity) private readonly rows: Repository<OrderEntity>) {}

  async save(order: Order): Promise<void> {
    await this.rows.save({ id: order.id, amountCents: order.amountCents });
  }

  async findById(id: string): Promise<Order | null> {
    const row = await this.rows.findOneBy({ id });
    return row ? Order.place(row.id, row.amountCents) : null;
  }
}
