import { Controller, Get } from '@nestjs/common';
import { ProductEntity } from '../model/product-entity';

@Controller('products')
export class ProductResource {
  @Get()
  async get(): Promise<ProductEntity> {
    return new ProductEntity();
  }
}
