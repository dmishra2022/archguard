from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ProductEntity(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
