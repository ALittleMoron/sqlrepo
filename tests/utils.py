import datetime
import random
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from sqlalchemy import ForeignKey, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy_utils import (
    create_database,
    database_exists,
    drop_database,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session


T = TypeVar("T")


def coin_flip() -> bool:
    """Coin flip: True or False."""
    return bool(random.getrandbits(1))


def create_db(uri: str) -> None:
    """Drop the database at ``uri`` and create a brand new one."""
    destroy_db(uri)
    create_database(uri)


def destroy_db(uri: str) -> None:
    """Destroy the database at ``uri``, if it exists."""
    if database_exists(uri):
        drop_database(uri)


def generate_datetime_list(
    *,
    n: int = 10,
    tz: Any = None,  # noqa: ANN401
) -> list[datetime.datetime]:
    """Generate list of datetimes of given length with or without timezone."""
    now = datetime.datetime.now(tz=tz)
    res = [now]
    for i in range(1, n):
        delta = datetime.timedelta(days=i)
        res.append(now + delta)
    return res


def assert_compare_db_items(item1: "DeclarativeBase", item2: "DeclarativeBase") -> None:
    """Assert if 2 models not compare to each other."""
    if item1 is item2:
        return
    assert (
        item1.__class__ == item2.__class__
    ), "item1 and item2 has different classes. Cant compare."
    item1_fields = set(inspect(item1.__class__).columns.keys())
    item2_fields = set(inspect(item2.__class__).columns.keys())
    assert item1_fields == item2_fields, ""
    for field in item1_fields:
        assert getattr(
            item1,
            field,
            float("nan"),
        ) == getattr(
            item2,
            field,
            float("nan"),
        ), f"field {field} is not compared. Different values."


def assert_compare_db_item_list(
    items1: Sequence["DeclarativeBase"],
    items2: Sequence["DeclarativeBase"],
) -> None:
    """Assert if 2 model lists not compare to each other."""
    assert len(items1) == len(items2), f"Different lists count: {len(items1)} != {len(items2)}"
    for item1, item2 in zip(
        sorted(items1, key=lambda x: x.id),  # type: ignore[reportAttributeAccessIssue]
        sorted(items2, key=lambda x: x.id),  # type: ignore[reportAttributeAccessIssue]
        strict=True,
    ):
        assert_compare_db_items(item1, item2)


def assert_compare_db_item_with_dict(
    item: "DeclarativeBase",
    data: dict[str, Any],
    *,
    skip_keys_check: bool = False,
) -> None:
    """Assert if model not compare to dict."""
    data_fields = set(data.keys())
    item_fields = set(inspect(item.__class__).columns.keys())
    msg = f"data fields ({data_fields}) are not compare to item fields ({item_fields})."
    if not skip_keys_check:
        assert set(data_fields).issubset(item_fields), msg
    for field, value in data.items():
        item_field_value = getattr(item, field, float("nan"))
        msg = (
            f'data ({field=} {value=}) not compare '
            f'to item ({field=} value={getattr(item, field, "<not present in item>")})'
        )
        assert item_field_value == value, msg


def assert_compare_db_item_list_with_dict(
    items: Sequence["DeclarativeBase"],
    data: dict[str, Any],
    *,
    skip_keys_check: bool = False,
) -> None:
    """Assert if list of models not compare to dict."""
    data_fields = set(data.keys())
    for item in items:
        item_class = item.__class__
        item_fields = set(inspect(item_class).columns.keys())
        msg = (
            f"data fields ({data_fields}) are not compare to item "
            f"({item_class}) fields ({item_fields})."
        )
        if not skip_keys_check:
            assert set(data_fields).issubset(item_fields), msg
        for field, value in data.items():
            item_field_value = getattr(item, field, float("nan"))
            msg = (
                f'data ({field=} {value=}) not compare '
                f'to item ({field=} value={getattr(item, field, "<not present in item>")})'
            )
            assert item_field_value == value, msg


def assert_compare_db_item_list_with_list_of_dicts(
    items: Sequence["DeclarativeBase"],
    data: Sequence[dict[str, Any]],
    *,
    skip_keys_check: bool = False,
) -> None:
    assert len(items) == len(data), "length of items and data is different."
    for item, data_ele in zip(items, data, strict=True):
        assert_compare_db_item_with_dict(item=item, data=data_ele, skip_keys_check=skip_keys_check)


def assert_compare_db_item_none_fields(item: "DeclarativeBase", none_fields: set[str]) -> None:
    """Assert compare model instance fields for none value."""
    for field in none_fields:
        item_value = getattr(item, field, float("nan"))
        msg = f'Field "{field}" is not None.'
        assert item_value is None, msg


def assert_compare_db_item_list_none_fields(
    items: Sequence["DeclarativeBase"],
    none_fields: set[str],
) -> None:
    """Assert compare list of model instances fields for none value."""
    for item in items:
        for field in none_fields:
            item_value = getattr(item, field, float("nan"))
            msg = f'Field "{field}" of item {item} is not None.'
            assert item_value is None, msg


def create_db_item_sync(
    session: "Session",
    model: type[T],
    params: dict[str, Any],
    *,
    commit: bool = False,
) -> T:
    """Create SQLAlchemy model item and add it to DB."""
    item = model(**params)
    session.add(item)
    try:
        session.commit() if commit else session.flush()
    except SQLAlchemyError:
        session.rollback()
        raise
    return item


async def create_db_item_async(
    session: "AsyncSession",
    model: type[T],
    params: dict[str, Any],
    *,
    commit: bool = False,
) -> T:
    """Create SQLAlchemy model item and add it to DB."""
    item = model(**params)
    session.add(item)
    try:
        await session.commit() if commit else await session.flush()
    except SQLAlchemyError:
        await session.rollback()
        raise
    return item


class NotModelClass:
    pass


class Base(DeclarativeBase):  # noqa: D101
    pass


class MyModel(Base):  # noqa: D101
    __tablename__ = "my_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    other_name: Mapped[str | None]
    dt: Mapped[datetime.datetime | None]
    bl: Mapped[bool | None]
    other_models: Mapped[list["OtherModel"]] = relationship(back_populates="my_model", uselist=True)

    @hybrid_property
    def full_name(self):
        return ((self.name or "") + "" + (self.other_name or "")).strip()

    @hybrid_method
    def get_full_name(self):
        return ((self.name or "") + "" + (self.other_name or "")).strip()


class OtherModel(Base):  # noqa: D101
    __tablename__ = "other_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    other_name: Mapped[str]
    my_model_id: Mapped[int | None] = mapped_column(ForeignKey("my_model.id", ondelete="CASCADE"))
    my_model: Mapped["MyModel"] = relationship(back_populates="other_models", uselist=False)

    @hybrid_property
    def full_name(self):
        return self.name + "" + self.other_name

    @hybrid_method
    def get_full_name(self):
        return self.name + "" + self.other_name
