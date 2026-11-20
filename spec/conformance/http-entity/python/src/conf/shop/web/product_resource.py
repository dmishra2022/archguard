from fastapi import APIRouter

from conf.shop.model.product_entity import ProductEntity

router = APIRouter(prefix='/products')


@router.get('/{product_id}')
async def get_product(product_id: int) -> 'ProductEntity':
    return ProductEntity(id=product_id)
