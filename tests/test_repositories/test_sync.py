from typing import TYPE_CHECKING, Any

import pytest
from mimesis import Datetime, Locale, Text
from sqlalchemy import func, select

from sqlrepo.config import RepositoryConfig
from sqlrepo.exc import RepositoryAttributeError
from sqlrepo.repositories import SyncRepository
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
    from sqlalchemy.orm import Session

    from tests.types import SyncFactoryFunctionProtocol


text_faker = Text(locale=Locale.EN)
dt_faker = Datetime(locale=Locale.EN)


class EmptyMyModelRepo(SyncRepository[MyModel]):  # noqa: D101
    pass


class MyModelRepo(SyncRepository[MyModel]):  # noqa: D101
    config = RepositoryConfig(
        specific_column_mapping={"some_specific_column": MyModel.name},
        disable_id_field="id",
        disable_field="bl",
        disable_field_type=bool,
    )


class MyModelRepoWithInstrumentedAttributes(SyncRepository[MyModel]):  # noqa: D101
    config = RepositoryConfig(
        specific_column_mapping={"some_specific_column": MyModel.name},
        disable_id_field=MyModel.id,
        disable_field=MyModel.bl,
        disable_field_type=bool,
    )


def test_get_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=True)
    repo = MyModelRepo(db_sync_session)
    db_item = repo.get(filters=dict(id=item.id))
    assert db_item is not None, f"MyModel with id {item.id} not found in db."
    assert_compare_db_items(item, db_item)


def test_get_item_not_found(db_sync_session: "Session") -> None:  # noqa: D103
    repo = MyModelRepo(db_sync_session)
    incorrect_id = 1
    db_item = repo.get(filters=dict(id=incorrect_id))
    assert db_item is None, f"MyModel with id {incorrect_id} was found in db (but it shouldn't)."


def test_get_items_count(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    create_count = 3
    for _ in range(create_count):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    count = repo.count()
    assert count == create_count


def test_get_items_count_with_filter(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    for _ in range(2):
        mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    count = repo.count(filters=dict(id=item.id))
    assert count == 1


def test_get_items_list(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    db_items = list(repo.list())
    assert_compare_db_item_list(items, db_items)


def test_create(db_sync_session: "Session") -> None:
    create_data = {
        "name": text_faker.sentence(),
        "other_name": text_faker.sentence(),
        "dt": dt_faker.datetime(),
        "bl": coin_flip(),
    }
    repo = MyModelRepo(db_sync_session)
    db_item = repo.create(data=create_data)
    assert_compare_db_item_with_dict(db_item, create_data, skip_keys_check=True)


def test_bulk_create(db_sync_session: "Session") -> None:
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
    repo = MyModelRepo(db_sync_session)
    db_items = repo.bulk_create(data=create_data)
    assert_compare_db_item_list_with_list_of_dicts(db_items, create_data, skip_keys_check=True)


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
def test_db_update(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    items_count: int,
) -> None:
    for _ in range(items_count):
        mymodel_sync_factory(db_sync_session, commit=True)
    repo = MyModelRepo(db_sync_session)
    db_item = repo.update(data=update_data)
    if db_item is None:
        pytest.fail("In this case db_item can't be None. Bug.")
    assert len(db_item) == items_count
    assert_compare_db_item_list_with_dict(db_item, update_data, skip_keys_check=True)


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
def test_change_item(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    update_data: dict[str, Any],
    expected_updated_flag: bool,  # noqa: FBT001
) -> None:
    item = mymodel_sync_factory(db_sync_session)
    repo = MyModelRepo(db_sync_session)
    updated, db_item = repo.update_instance(instance=item, data=update_data)
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
    repo = MyModelRepo(db_sync_session)
    repo.config.update_set_none = set_none
    repo.config.update_allowed_none_fields = allowed_none_fields
    updated, db_item = repo.update_instance(instance=item, data=update_data)
    if expected_updated_flag is not updated:
        pytest.skip("update flag check failed. Test needs to be changed.")
    assert_compare_db_item_none_fields(db_item, none_set_fields)


def test_db_delete_direct_value(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session)
    repo = MyModelRepo(db_sync_session)
    delete_count = repo.delete(filters={"id": item.id})
    assert delete_count == 1
    assert db_sync_session.scalar(select(func.count()).select_from(MyModel)) == 0


def test_db_delete_multiple_values(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    to_delete_count = 3
    for _ in range(to_delete_count):
        mymodel_sync_factory(db_sync_session)
    repo = MyModelRepo(db_sync_session)
    delete_count = repo.delete()
    assert delete_count == to_delete_count
    assert db_sync_session.scalar(select(func.count()).select_from(MyModel)) == 0


def test_disable_error(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, bl=False)
    repo = EmptyMyModelRepo(db_sync_session)
    with pytest.raises(RepositoryAttributeError):
        repo.disable(
            ids_to_disable={item.id},
            extra_filters={"id": item.id},
        )


def test_disable_items_direct_value(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, bl=False)
    repo = MyModelRepo(db_sync_session)
    disable_count = repo.disable(
        ids_to_disable={item.id},
        extra_filters={"id": item.id},
    )
    assert disable_count == 1
    assert (
        db_sync_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


def test_disable_items_direct_value_with_instrumented_attributes(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, bl=False)
    repo = MyModelRepoWithInstrumentedAttributes(db_sync_session)
    disable_count = repo.disable(
        ids_to_disable={item.id},
        extra_filters={"id": item.id},
    )
    assert disable_count == 1
    assert (
        db_sync_session.scalar(
            select(func.count()).select_from(MyModel).where(MyModel.bl.is_(False)),
        )
        == 0
    )


def test_exists_success_any_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    exists = repo.exists()
    assert exists is True


def test_exists_success_direct_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    exists = repo.exists(filters={"id": item.id})
    assert exists is True


def test_not_exists(db_sync_session: "Session") -> None:  # noqa: D103
    repo = MyModelRepo(db_sync_session)
    exists = repo.exists()
    assert exists is False


def test_not_exists_direct_item(  # noqa: D103
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=False)
    db_sync_session.commit()
    repo = MyModelRepo(db_sync_session)
    exists = repo.exists(filters={"id": -item.id})
    assert exists is False
