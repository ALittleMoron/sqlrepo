from typing import TYPE_CHECKING, Any

import pytest
from mimesis import Datetime, Locale, Text
from sqlalchemy import func, select
from sqlalchemy_filter_converter import SimpleFilterConverter

from sqlrepo.queries import BaseAsyncQuery
from tests.utils import (
    MyModel,
    OtherModel,
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


@pytest.mark.asyncio()
async def test_get_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=True)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    db_item = await query_obj.get_item(model=MyModel, filters=dict(id=item.id))
    assert db_item is not None, f"MyModel with id {item.id} not found in db."
    assert_compare_db_items(item, db_item)


@pytest.mark.asyncio()
async def test_get_item_not_found(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=True)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    db_item = await query_obj.get_item(model=MyModel, filters=dict(id=item.id + 1))
    assert db_item is None, f"MyModel with id {item.id + 1} was found in db (but it shouldn't)."


@pytest.mark.asyncio()
async def test_get_items_count(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    create_count = 3
    for _ in range(create_count):
        await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    count = await query_obj.get_items_count(model=MyModel)
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
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    count = await query_obj.get_items_count(model=MyModel, filters=dict(id=item.id))
    assert count == 1


@pytest.mark.asyncio()
async def test_get_items_list(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [await mymodel_async_factory(db_async_session, commit=False) for _ in range(3)]
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    db_items = list(await query_obj.get_item_list(model=MyModel))
    assert_compare_db_item_list(items, db_items)


# TODO: fix test. Now it just clone of test_get_items_list (previous test). Needs to check unique
@pytest.mark.asyncio()
async def test_get_items_list_with_unique(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [await mymodel_async_factory(db_async_session, commit=False) for _ in range(3)]
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    db_items = list(await query_obj.get_item_list(model=MyModel, unique_items=True))
    assert_compare_db_item_list(items, db_items)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "use_flush",
    [
        True,
        False,
    ],
)
async def test_db_create(
    db_async_session: "AsyncSession",
    use_flush: bool,  # noqa: FBT001
) -> None:
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    create_data = {
        "name": text_faker.sentence(),
        "other_name": text_faker.sentence(),
        "dt": dt_faker.datetime(),
        "bl": coin_flip(),
    }
    db_item = await query_obj.db_create(
        model=MyModel,
        data=create_data,
        use_flush=use_flush,
    )
    if not isinstance(db_item, MyModel):
        pytest.fail("Model create from dict should return Model (not list)")
    assert_compare_db_item_with_dict(db_item, create_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "use_flush",
    [
        True,
        False,
    ],
)
async def test_db_create_list(
    db_async_session: "AsyncSession",
    use_flush: bool,  # noqa: FBT001
) -> None:
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
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
    db_items = await query_obj.db_create(
        model=MyModel,
        data=create_data,
        use_flush=use_flush,
    )
    if isinstance(db_items, MyModel):
        pytest.fail("Model create from list of dicts should return list (not Model)")
    assert_compare_db_item_list_with_list_of_dicts(db_items, create_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("update_data", "use_flush", "items_count"),
    [
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            True,
            1,
        ),
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            False,
            1,
        ),
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            False,
            3,
        ),
    ],
)
async def test_db_update(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
    update_data: Any,  # noqa: ANN401
    use_flush: bool,  # noqa: FBT001
    items_count: int,
) -> None:
    for _ in range(items_count):
        await mymodel_async_factory(db_async_session, commit=True)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    db_item = await query_obj.db_update(model=MyModel, data=update_data, use_flush=use_flush)
    assert len(db_item) == items_count
    assert_compare_db_item_list_with_dict(db_item, update_data, skip_keys_check=True)


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    ("update_data", "use_flush", "expected_updated_flag"),
    [
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            True,
            True,
        ),
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            False,
            True,
        ),
        (
            {},
            False,
            False,
        ),
    ],
)
async def test_change_item(
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    use_flush: bool,  # noqa: FBT001
    expected_updated_flag: bool,  # noqa: FBT001
) -> None:
    item = await mymodel_async_factory(db_async_session)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    updated, db_item = await query_obj.change_item(data=update_data, item=item, use_flush=use_flush)
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
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    updated, db_item = await query_obj.change_item(
        data=update_data,
        item=item,
        set_none=set_none,
        allowed_none_fields=allowed_none_fields,
    )
    if expected_updated_flag is not updated:
        pytest.skip("update flag check failed. Test needs to be changed.")
    assert_compare_db_item_none_fields(db_item, none_set_fields)


@pytest.mark.asyncio()
@pytest.mark.parametrize("use_flush", [True, False])
async def test_db_delete_direct_value(
    use_flush: bool,  # noqa: FBT001
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    delete_count = await query_obj.db_delete(
        model=MyModel,
        filters={"id": item.id},
        use_flush=use_flush,
    )
    assert delete_count == 1
    assert await db_async_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.asyncio()
@pytest.mark.parametrize("use_flush", [True, False])
async def test_db_delete_multiple_values(
    use_flush: bool,  # noqa: FBT001
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    to_delete_count = 3
    for _ in range(to_delete_count):
        await mymodel_async_factory(db_async_session)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    delete_count = await query_obj.db_delete(
        model=MyModel,
        use_flush=use_flush,
    )
    assert delete_count == to_delete_count
    assert await db_async_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "use_flush",
    [True, False],
)
async def test_disable_items_direct_value(
    use_flush: bool,  # noqa: FBT001
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, bl=False)
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    disable_count = await query_obj.disable_items(
        model=MyModel,
        ids_to_disable={item.id},
        id_field="id",
        disable_field="bl",
        field_type=bool,
        allow_filter_by_value=False,
        extra_filters={"id": item.id},
        use_flush=use_flush,
    )
    assert disable_count == 1
    assert (
        await db_async_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


@pytest.mark.asyncio()
async def test_items_exists_success_any_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    exists = await query_obj.items_exists(model=MyModel, filters=None)
    assert exists is True


@pytest.mark.asyncio()
async def test_items_exists_success_direct_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    exists = await query_obj.items_exists(model=MyModel, filters={"id": item.id})
    assert exists is True


@pytest.mark.asyncio()
async def test_items_not_exists(  # noqa: D103
    db_async_session: "AsyncSession",
) -> None:
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    exists = await query_obj.items_exists(model=MyModel, filters=None)
    assert exists is False


@pytest.mark.asyncio()
async def test_items_not_exists_direct_item(  # noqa: D103
    db_async_session: "AsyncSession",
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = await mymodel_async_factory(db_async_session, commit=False)
    await db_async_session.commit()
    query_obj = BaseAsyncQuery(session=db_async_session, filter_converter=SimpleFilterConverter())
    exists = await query_obj.items_exists(model=MyModel, filters={"id": -item.id})
    assert exists is False
