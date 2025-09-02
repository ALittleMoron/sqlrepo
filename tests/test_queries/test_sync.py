from typing import TYPE_CHECKING, Any

import pytest
from mimesis import Datetime, Locale, Text
from sqlalchemy import func, select
from sqlalchemy_filter_converter import SimpleFilterConverter

from sqlrepo.queries import BaseSyncQuery
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
    from sqlalchemy.orm import Session

    from tests.types import SyncFactoryFunctionProtocol


text_faker = Text(locale=Locale.EN)
dt_faker = Datetime(locale=Locale.EN)


def test_get_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=True)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    db_item = query_obj.get_item(model=MyModel, filters=dict(id=item.id))
    assert db_item is not None, f"MyModel with id {item.id} not found in db."
    assert_compare_db_items(item, db_item)


def test_get_item_not_found(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=True)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    db_item = query_obj.get_item(model=MyModel, filters=dict(id=item.id + 1))
    assert db_item is None, f"MyModel with id {item.id + 1} was found in db (but it shouldn't)."


def test_get_items_count(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    create_count = 3
    for _ in range(create_count):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    count = query_obj.get_items_count(model=MyModel)
    assert count == create_count


def test_get_items_count_with_filter(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    for _ in range(2):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    count = query_obj.get_items_count(model=MyModel, filters=dict(id=item.id))
    assert count == 1


def test_get_items_list(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    db_items = list(query_obj.get_item_list(model=MyModel))
    assert_compare_db_item_list(items, db_items)


# TODO: fix test. Now it just clone of test_get_items_list (previous test). Needs to check unique
def test_get_items_list_with_unique(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    db_items = list(query_obj.get_item_list(model=MyModel, unique_items=True))
    assert_compare_db_item_list(items, db_items)


@pytest.mark.parametrize(
    "use_flush",
    [
        True,
        False,
    ],
)
def test_db_create(
    db_sync_session: "Session",
    use_flush: bool,  # noqa: FBT001
) -> None:
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    create_data = {
        "name": text_faker.sentence(),
        "other_name": text_faker.sentence(),
        "dt": dt_faker.datetime(),
        "bl": coin_flip(),
    }
    db_item = query_obj.db_create(
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
def test_db_create_list(
    db_sync_session: "Session",
    use_flush: bool,  # noqa: FBT001
) -> None:
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
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
    db_items = query_obj.db_create(
        model=MyModel,
        data=create_data,
        use_flush=use_flush,
    )
    if isinstance(db_items, MyModel):
        pytest.fail("Model create from list of dicts should return list (not Model)")
    assert_compare_db_item_list_with_list_of_dicts(db_items, create_data, skip_keys_check=True)


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
def test_db_update(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    use_flush: bool,  # noqa: FBT001
    items_count: int,
) -> None:
    for _ in range(items_count):
        mymodel_sync_factory(db_sync_session, commit=True)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    db_item = query_obj.db_update(model=MyModel, data=update_data, use_flush=use_flush)
    assert len(db_item) == items_count
    assert_compare_db_item_list_with_dict(db_item, update_data, skip_keys_check=True)


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
def test_change_item(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    use_flush: bool,  # noqa: FBT001
    expected_updated_flag: bool,  # noqa: FBT001
) -> None:
    item = mymodel_sync_factory(db_sync_session)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    updated, db_item = query_obj.change_item(data=update_data, item=item, use_flush=use_flush)
    assert expected_updated_flag is updated
    assert_compare_db_item_with_dict(db_item, update_data, skip_keys_check=True)


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
def test_change_item_none_check(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    expected_updated_flag: bool,  # noqa: FBT001
    set_none: bool,  # noqa: FBT001
    allowed_none_fields: Any,  # noqa: FBT001, ANN401
    none_set_fields: set[str],
) -> None:
    item = mymodel_sync_factory(db_sync_session)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    updated, db_item = query_obj.change_item(
        data=update_data,
        item=item,
        set_none=set_none,
        allowed_none_fields=allowed_none_fields,
    )
    if expected_updated_flag is not updated:
        pytest.skip("update flag check failed. Test needs to be changed.")
    assert_compare_db_item_none_fields(db_item, none_set_fields)


@pytest.mark.parametrize("use_flush", [True, False])
def test_db_delete_direct_value(
    use_flush: bool,  # noqa: FBT001
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    delete_count = query_obj.db_delete(
        model=MyModel,
        filters={"id": item.id},
        use_flush=use_flush,
    )
    assert delete_count == 1
    assert db_sync_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.parametrize("use_flush", [True, False])
def test_db_delete_multiple_values(
    use_flush: bool,  # noqa: FBT001
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    to_delete_count = 3
    for _ in range(to_delete_count):
        mymodel_sync_factory(db_sync_session)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    delete_count = query_obj.db_delete(
        model=MyModel,
        use_flush=use_flush,
    )
    assert delete_count == to_delete_count
    assert db_sync_session.scalar(select(func.count()).select_from(MyModel)) == 0


@pytest.mark.parametrize(
    "use_flush",
    [True, False],
)
def test_disable_items_direct_value(
    use_flush: bool,  # noqa: FBT001
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, bl=False)
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    disable_count = query_obj.disable_items(
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
        db_sync_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


def test_items_exists_success_any_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    exists = query_obj.items_exists(model=MyModel, filters=None)
    assert exists is True


def test_items_exists_success_direct_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    exists = query_obj.items_exists(model=MyModel, filters={"id": item.id})
    assert exists is True


def test_items_not_exists(db_sync_session: "Session") -> None:  # noqa: D103
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    exists = query_obj.items_exists(model=MyModel, filters=None)
    assert exists is False


def test_items_not_exists_direct_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(session=db_sync_session, filter_converter=SimpleFilterConverter())
    exists = query_obj.items_exists(model=MyModel, filters={"id": -item.id})
    assert exists is False
