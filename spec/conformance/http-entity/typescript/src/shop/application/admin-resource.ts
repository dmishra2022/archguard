import { Controller, Get } from '@nestjs/common';

@Controller('admin')
export class AdminResource {
  @Get()
  status(): string {
    return 'ok';
  }
}
