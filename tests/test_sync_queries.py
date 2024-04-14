from typing import TYPE_CHECKING, Any

import pytest
from dev_utils.sqlalchemy.filters.converters import SimpleFilterConverter  # type: ignore
from mimesis import Datetime, Locale, Text

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
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    db_item = query_obj.get_item(model=MyModel, filters=dict(id=item.id))
    assert db_item is not None, f"MyModel with id {item.id} not found in db."
    assert_compare_db_items(item, db_item)


def test_get_item_not_found(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=True)
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    db_item = query_obj.get_item(model=MyModel, filters=dict(id=item.id + 1))
    assert db_item is None, f"MyModel with id {item.id + 1} was found in db (but it shouldn't)."


def test_get_items_count(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    for _ in range(3):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    count = query_obj.get_items_count(model=MyModel)
    assert count == 3


def test_get_items_count_with_filter(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    for _ in range(2):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    count = query_obj.get_items_count(model=MyModel, filters=dict(id=item.id))
    assert count == 1


def test_get_items_list(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    db_sync_session.commit()
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    db_items = list(query_obj.get_item_list(model=MyModel))
    assert_compare_db_item_list(items, db_items)


# TODO: fix test. Now it just clone of test_get_items_list (previous test). Needs to check unique
def test_get_items_list_with_unique(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    db_sync_session.commit()
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    db_items = list(query_obj.get_item_list(model=MyModel, unique_items=True))
    assert_compare_db_item_list(items, db_items)


@pytest.mark.parametrize(
    ("create_data", "use_flush"),
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
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
            },
            False,
        ),
        (
            {
                "name": text_faker.sentence(),
                "other_name": text_faker.sentence(),
                "dt": dt_faker.datetime(),
                "bl": coin_flip(),
                "other_models": [
                    OtherModel(
                        name=text_faker.sentence(),
                        other_name=text_faker.sentence(),
                    ),
                    OtherModel(
                        name=text_faker.sentence(),
                        other_name=text_faker.sentence(),
                    ),
                ],
            },
            False,
        ),
    ],
)
def test_create_item(
    db_sync_session: "Session",
    create_data: dict[str, Any],
    use_flush: bool,  # noqa: FBT001
) -> None:
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    db_item = query_obj.create_item(model=MyModel, data=create_data, use_flush=use_flush)
    assert_compare_db_item_with_dict(db_item, create_data, skip_keys_check=True)


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
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
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
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
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
    query_obj = BaseSyncQuery(db_sync_session, SimpleFilterConverter)
    updated, db_item = query_obj.change_item(
        data=update_data,
        item=item,
        set_none=set_none,
        allowed_none_fields=allowed_none_fields,
    )
    assert expected_updated_flag is updated
    assert_compare_db_item_none_fields(db_item, none_set_fields)
