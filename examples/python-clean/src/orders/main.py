from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from orders.application.place_order import PlaceOrder
from orders.infrastructure.models import Base
from orders.infrastructure.sqlalchemy_order_repository import SqlAlchemyOrderRepository
from orders.web import routes
from orders.web.dependencies import get_place_order


def create_app(database_url: str = 'sqlite://') -> FastAPI:
    engine = create_engine(database_url, connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    repository = SqlAlchemyOrderRepository(sessionmaker(bind=engine))
    app = FastAPI(title='Orders')
    app.include_router(routes.router)
    app.dependency_overrides[get_place_order] = lambda: PlaceOrder(repository)
    return app


app = create_app()
