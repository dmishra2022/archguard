import { Column, Entity, PrimaryColumn } from 'typeorm';

@Entity('orders')
export class OrderEntity {
  @PrimaryColumn()
  id!: string;

  @Column('int')
  amountCents!: number;
}
