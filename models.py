from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String
)

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column
)


class Base(DeclarativeBase):
    pass


class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )


class Movie(Base):

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    code: Mapped[int] = mapped_column(
        Integer,
        unique=True
    )

    title: Mapped[str] = mapped_column(
        String(500)
    )

    channel_message_id: Mapped[int] = mapped_column(
        BigInteger
    )