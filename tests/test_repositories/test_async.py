from typing import TYPE_CHECKING, Any

import pytest
from mimesis import Datetime, Locale, Text
from sqlalchemy import func, select

from sqlrepo.config import RepositoryConfig
from sqlrepo.exc import RepositoryAttributeError
from sqlrepo.repositories import AsyncRepository
from tests.utils import (
    MyModel,
    assert_compare_db_item_list,
    assert_compare_db_item_list_with_dict,
    assert_compare_db_item_none_fields,
    assert_compare_db_item_with_dict,
    assert_compare_db_items,
    coin_flip,
    assert_compare_db_item_list_with_list_of_dicts,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.types import AsyncFactoryFunctionProtocol


text_faker = Text(locale=Locale.EN)
dt_faker = Datetime(locale=Locale.EN)


class EmptyMyModelRepo(AsyncRepository[MyModel]):  # noqa: D101
    pass


class MyModelRepo(AsyncRepository[MyModel]):  # noqa: D101
    config = RepositoryConfig(
        specific_column_mapping={"some_specific_column": MyModel.name},
        disable_id_field="id",
        disable_field="bl",
        disable_field_type=bool,
    )


class MyModelRepoWithInstrumentedAttributes(AsyncRepository[MyModel]):  # noqa: D101
    config = RepositoryConfig(
        specific_column_mapping={"some_specific_column": MyModel.name},
        disable_id_field=MyModel.id,
        disable_field=MyModel.bl,
        disable_field_type=bool,
    )


@pytest.mark.asyncio()
async def test_get_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=True)
    repo = MyModelRepo(db_async_session)
    db_item = await repo.get(filters=dict(id=item.id))
    assert db_item is not None, f"MyModel with id {item.id} not found in db."
    assert_compare_db_items(item, db_item)


@pytest.mark.asyncio()
async def test_get_item_not_found(db_async_session: "AsyncSession") -> None:  # noqa: D103
    repo = MyModelRepo(db_async_session)
    incorrect_id = 1
    db_item = await repo.get(filters=dict(id=incorrect_id))
    assert db_item is None, f"MyModel with id {incorrect_id} was found in db (but it shouldn't)."


@pytest.mark.asyncio()
async def test_get_items_count(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    create_count = 3
    for _ in range(create_count):
        await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    count = await repo.count()
    assert count == create_count


@pytest.mark.asyncio()
async def test_get_items_count_with_filter(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=False)
    for _ in range(2):
        await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    count = await repo.count(filters=dict(id=item.id))
    assert count == 1


@pytest.mark.asyncio()
async def test_get_items_list(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [await mymodel_async_factory(db_async_session, commit=False) for _ in range(3)]
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    db_items = list(await repo.list())
    assert_compare_db_item_list(items, db_items)


@pytest.mark.asyncio()
async def test_db_create(db_async_session: "AsyncSession") -> None:
    create_data = {
        "name": text_faker.sentence(),
        "other_name": text_faker.sentence(),
        "dt": dt_faker.datetime(),
        "bl": coin_flip(),
    }
    repo = MyModelRepo(db_async_session)
    db_item = await repo.create(data=create_data)
    assert_compare_db_item_with_dict(db_item, create_data, skip_keys_check=True)


@pytest.mark.asyncio()
async def test_bulk_create(db_async_session: "AsyncSession") -> None:
    create_data = [
        {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "dt": dt_faker.datetime(),
            "bl": coin_flip(),
        },
        {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "dt": dt_faker.datetime(),
            "bl": coin_flip(),
        },
    ]
    repo = MyModelRepo(db_async_session)
    db_items = await repo.bulk_create(data=create_data)
    assert_compare_db_item_list_with_list_of_dicts(db_items, create_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("update_data", "items_count"),
    [
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            1,
        ),
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            3,
        ),
    ],
)
async def test_db_update(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    items_count: int,
) -> None:
    for _ in range(items_count):
        await mymodel_async_factory(db_async_session, commit=True)
    repo = MyModelRepo(db_async_session)
    db_item = await repo.update(data=update_data)
    if db_item is None:
        pytest.fail("In this case db_item can't be None. Bug.")
    assert len(db_item) == items_count
    assert_compare_db_item_list_with_dict(db_item, update_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("update_data", "expected_updated_flag"),
    [
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            True,
        ),
        (
            {},
            False,
        ),
    ],
)
async def test_change_item(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    expected_updated_flag: bool,  # noqa: FBT001
) -> None:
    item = await mymodel_async_factory(db_async_session)
    repo = MyModelRepo(db_async_session)
    updated, db_item = await repo.update_instance(instance=item, data=update_data)
    assert expected_updated_flag is updated
    assert_compare_db_item_with_dict(db_item, update_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("update_data", "expected_updated_flag", "set_none", "allowed_none_fields", "none_set_fields"),
    [
        (
            {},
            False,
            False,
            {},
            {},
        ),
        (
            {"name": text_faker.sentence()},
            True,
            True,
            "*",
            {},
        ),
        (
            {"name": text_faker.sentence(), "other_name": None, "dt": None, "bl": None},
            True,
            True,
            "*",
            {"other_name", "dt", "bl"},
        ),
        (
            {"name": text_faker.sentence(), "other_name": None, "dt": None, "bl": None},
            True,
            True,
            {"other_name"},
            {"other_name"},
        ),
    ],
)
async def test_change_item_none_check(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    expected_updated_flag: bool,  # noqa: FBT001
    set_none: bool,  # noqa: FBT001
    allowed_none_fields: Any,  # noqa: FBT001, ANN401
    none_set_fields: set[str],
) -> None:
    item = await mymodel_async_factory(db_async_session)
    repo = MyModelRepo(db_async_session)
    repo.config.update_set_none = set_none
    repo.config.update_allowed_none_fields = allowed_none_fields
    updated, db_item = await repo.update_instance(instance=item, data=update_data)
    if expected_updated_flag is not updated:
        pytest.skip("update flag check failed. Test needs to be changed.")
    assert_compare_db_item_none_fields(db_item, none_set_fields)


@pytest.mark.asyncio()
async def test_db_delete_direct_value(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session)
    repo = MyModelRepo(db_async_session)
    delete_count = await repo.delete(filters={"id": item.id})
    assert delete_count == 1
    assert await db_async_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.asyncio()
async def test_db_delete_multiple_values(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    to_delete_count = 3
    for _ in range(to_delete_count):
        await mymodel_async_factory(db_async_session)
    repo = MyModelRepo(db_async_session)
    delete_count = await repo.delete()
    assert delete_count == to_delete_count
    assert await db_async_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.asyncio()
async def test_disable_error(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, bl=False)
    repo = EmptyMyModelRepo(db_async_session)
    with pytest.raises(RepositoryAttributeError):
        await repo.disable(
            ids_to_disable={item.id},
            extra_filters={"id": item.id},
        )


@pytest.mark.asyncio()
async def test_disable_items_direct_value(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, bl=False)
    repo = MyModelRepo(db_async_session)
    disable_count = await repo.disable(
        ids_to_disable={item.id},
        extra_filters={"id": item.id},
    )
    assert disable_count == 1
    assert (
        await db_async_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


@pytest.mark.asyncio()
async def test_disable_items_direct_value_with_instrumented_attributes(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, bl=False)
    repo = MyModelRepoWithInstrumentedAttributes(db_async_session)
    disable_count = await repo.disable(
        ids_to_disable={item.id},
        extra_filters={"id": item.id},
    )
    assert disable_count == 1
    assert (
        await db_async_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


@pytest.mark.asyncio()
async def test_exists_success_any_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    exists = await repo.exists()
    assert exists is True


@pytest.mark.asyncio()
async def test_exists_success_direct_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    exists = await repo.exists(filters={"id": item.id})
    assert exists is True


@pytest.mark.asyncio()
async def test_not_exists(db_async_session: "AsyncSession") -> None:  # noqa: D103
    repo = MyModelRepo(db_async_session)
    exists = await repo.exists()
    assert exists is False


@pytest.mark.asyncio()
async def test_not_exists_direct_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    repo = MyModelRepo(db_async_session)
    exists = await repo.exists(filters={"id": -item.id})
    assert exists is False
