import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { PlaceOrder } from './application/place-order';
import { ORDER_REPOSITORY } from './application/ports/order-repository';
import { OrderEntity } from './infrastructure/order.entity';
import { TypeOrmOrderRepository } from './infrastructure/typeorm-order-repository';
import { OrdersController } from './web/orders.controller';

@Module({
  imports: [TypeOrmModule.forFeature([OrderEntity])],
  controllers: [OrdersController],
  providers: [PlaceOrder, { provide: ORDER_REPOSITORY, useClass: TypeOrmOrderRepository }],
})
export class OrdersModule {}
