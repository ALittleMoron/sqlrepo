import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from freezegun import freeze_time
from sqlalchemy import ColumnElement, and_, delete, func, insert, or_, select, update, exists
from sqlalchemy.orm import joinedload
from sqlalchemy_dev_utils.exc import NoModelAttributeError
from sqlalchemy_filter_converter import SimpleFilterConverter

from sqlrepo.exc import QueryError
from sqlrepo.queries import BaseQuery
from tests.utils import MyModel, OtherModel, NotModelClass

now = datetime.datetime.now(tz=ZoneInfo("UTC"))


@pytest.mark.parametrize(
    ("model", "specific_column_mapping", "elements", "expected_result"),
    [
        (
            MyModel,
            None,
            [MyModel.name],
            [MyModel.name],
        ),
        (
            OtherModel,
            {"other_model_id": OtherModel.id, "some_other_model_field": OtherModel.name},
            ["other_model_id", "some_other_model_field"],
            [OtherModel.id, OtherModel.name],
        ),
    ],
)
def test_resolve_specific_columns(  # noqa
    model: Any,  # noqa: ANN401
    specific_column_mapping: Any,  # noqa: ANN401
    elements: list[str | ColumnElement[Any]],
    expected_result: list[str | ColumnElement[Any]],  # noqa
) -> None:
    query = BaseQuery(
        filter_converter=SimpleFilterConverter(specific_column_mapping=specific_column_mapping),
        specific_column_mapping=specific_column_mapping,
    )
    converted_columns = query._resolve_specific_columns(model=model, elements=elements)
    assert converted_columns == expected_result


@pytest.mark.parametrize(
    ("model", "elements", "exception", "match"),
    [
        (
            MyModel,
            ["other_model_id_field"],
            NoModelAttributeError,
            None,
        ),
        (
            OtherModel,
            ["other_model_id_field", "some_other_model_field"],
            NoModelAttributeError,
            None,
        ),
        (
            MyModel,
            [25],
            ValueError,
            "Type of 0 element of given elements is incorrect. Type: <class 'int'>",
        ),
    ],
)
def test_resolve_specific_columns_error(  # noqa
    model: Any,  # noqa: ANN401
    elements: list[str | ColumnElement[Any]],
    exception: type[Exception],
    match: str | None,
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter(), specific_column_mapping=None)
    with pytest.raises(exception, match=match):
        query._resolve_specific_columns(model=model, elements=elements)


@pytest.mark.parametrize(
    ("stmt", "joins", "expected_result"),
    [
        (
            select(MyModel),
            [OtherModel],
            select(MyModel).join(OtherModel),
        ),
        (
            select(MyModel),
            OtherModel,
            select(MyModel).join(OtherModel),
        ),
        (
            select(MyModel),
            ["other_models"],
            select(MyModel).join(OtherModel),
        ),
        (
            select(MyModel),
            [(OtherModel, MyModel.id == OtherModel.my_model_id)],
            select(MyModel).join(OtherModel),
        ),
        (
            select(MyModel),
            [(OtherModel, MyModel.id == OtherModel.my_model_id, {"isouter": True})],
            select(MyModel).join(OtherModel, isouter=True),
        ),
        (
            select(MyModel),
            [(OtherModel, MyModel.id == OtherModel.my_model_id, {"full": True})],
            select(MyModel).join(OtherModel, full=True),
        ),
        (
            select(MyModel),
            "other_models",
            select(MyModel).join(OtherModel),
        ),
    ],
)
def test_resolve_and_apply_joins(  # noqa
    stmt: Any,  # noqa
    joins: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    new_stmt = query._resolve_and_apply_joins(stmt=stmt, joins=joins)
    assert str(new_stmt) == str(expected_result)


def test_resolve_and_apply_joins_query_error() -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())

    msg = (
        f'Parameter "joins" should not contains non-declarative model classes. '
        f'{NotModelClass} was passed'
    )
    with pytest.raises(
        QueryError,
        match=msg,
    ):
        query._resolve_and_apply_joins(stmt=select(MyModel), joins=NotModelClass)  # type: ignore


@pytest.mark.parametrize(
    (
        "id_field",
        "ids_to_disable",
        "disable_field",
        "field_type",
        "allow_filter_by_value",
        "extra_filters",
        "expected_result",
    ),
    [
        (
            MyModel.id,
            {1, 2, 3, 4, 5},
            MyModel.dt,
            datetime.datetime,
            False,
            None,
            [MyModel.id.in_({1, 2, 3, 4, 5})],
        ),
        (
            MyModel.id,
            {1, 2, 3, 4, 5},
            MyModel.dt,
            datetime.datetime,
            False,
            {"name": "aboba"},
            [MyModel.id.in_({1, 2, 3, 4, 5}), MyModel.name == "aboba"],
        ),
        (
            MyModel.id,
            {1, 2, 3, 4, 5},
            MyModel.dt,
            datetime.datetime,
            True,
            None,
            [MyModel.id.in_({1, 2, 3, 4, 5}), MyModel.dt.is_(None)],
        ),
        (
            MyModel.id,
            {1, 2, 3, 4, 5},
            MyModel.bl,
            bool,
            True,
            None,
            [MyModel.id.in_({1, 2, 3, 4, 5}), MyModel.bl.is_not(True)],
        ),
    ],
)
def test_make_disable_filters(  # noqa
    id_field: Any,  # noqa
    ids_to_disable: set[Any],
    disable_field: Any,  # noqa
    field_type: type[datetime.datetime] | type[bool],
    allow_filter_by_value: bool,  # noqa
    extra_filters: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    disable_filters = query._make_disable_filters(
        model=MyModel,
        id_field=id_field,
        ids_to_disable=ids_to_disable,
        disable_field=disable_field,
        field_type=field_type,
        allow_filter_by_value=allow_filter_by_value,
        extra_filters=extra_filters,
    )
    assert list(map(str, disable_filters)) == list(map(str, expected_result))


@pytest.mark.parametrize(
    ("search", "search_by_args", "use_and_clause", "expected_result"),
    [
        (
            "value",
            (MyModel.name, MyModel.other_name),
            False,
            or_(MyModel.name.ilike(r"%value%"), MyModel.other_name.ilike(r"%value%")),
        ),
        (
            "value",
            (MyModel.name, MyModel.other_name),
            True,
            and_(MyModel.name.ilike(r"%value%"), MyModel.other_name.ilike(r"%value%")),
        ),
        (
            "value",
            ("name", "other_name"),
            False,
            or_(MyModel.name.ilike(r"%value%"), MyModel.other_name.ilike(r"%value%")),
        ),
    ],
)
def test_make_search_filter(  # noqa
    search: str,
    search_by_args: tuple[Any, ...],
    use_and_clause: bool,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    search_filter = query._make_search_filter(
        search,
        MyModel,
        *search_by_args,
        use_and_clause=use_and_clause,
    )
    assert str(search_filter) == str(expected_result)


@pytest.mark.parametrize(
    ("filters", "joins", "loads", "expected_result"),
    [
        (
            None,
            None,
            None,
            select(MyModel),
        ),
        (
            {"name": "aboba"},
            None,
            None,
            select(MyModel).where(MyModel.name == "aboba"),
        ),
        (
            None,
            ["other_models"],
            None,
            select(MyModel).join(OtherModel),
        ),
        (
            None,
            None,
            [joinedload(MyModel.other_models)],
            select(MyModel).options(joinedload(MyModel.other_models)),
        ),
    ],
)
def test_get_item_stmt(  # noqa
    filters: Any,  # noqa
    joins: Any,  # noqa
    loads: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    get_item_stmt = query._get_item_stmt(
        model=MyModel,
        filters=filters,
        joins=joins,
        loads=loads,
    )
    assert str(get_item_stmt) == str(expected_result)


@pytest.mark.parametrize(
    ("filters", "joins", "expected_result"),
    [
        (
            None,
            None,
            select(func.count()).select_from(MyModel),
        ),
        (
            {"name": "aboba"},
            None,
            select(func.count()).select_from(MyModel).where(MyModel.name == "aboba"),
        ),
        (
            None,
            ["other_models"],
            select(func.count()).select_from(MyModel).join(OtherModel),
        ),
        (
            [OtherModel.name == "aboba"],
            ["other_models"],
            select(func.count())
            .select_from(MyModel)
            .join(OtherModel)
            .where(OtherModel.name == "aboba"),
        ),
    ],
)
def test_get_items_count_stmt(  # noqa
    filters: Any,  # noqa
    joins: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    get_items_count_stmt = query._get_items_count_stmt(
        model=MyModel,
        joins=joins,
        filters=filters,
    )
    assert str(get_items_count_stmt) == str(expected_result)


@pytest.mark.parametrize(
    (
        "joins",
        "loads",
        "filters",
        "search",
        "search_by",
        "order_by",
        "limit",
        "offset",
        "expected_result",
    ),
    [
        (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            select(MyModel),
        ),
        (
            None,
            None,
            None,
            "some_value",
            None,
            None,
            None,
            None,
            select(MyModel),
        ),
        (
            None,
            None,
            None,
            None,
            (MyModel.name,),
            None,
            None,
            None,
            select(MyModel),
        ),
        (
            None,
            None,
            None,
            "somevalue",
            (MyModel.name,),
            None,
            None,
            None,
            select(MyModel).where(MyModel.name.ilike(r"%somevalue%")),
        ),
        (
            None,
            None,
            None,
            "somevalue",
            MyModel.name,
            None,
            None,
            None,
            select(MyModel).where(MyModel.name.ilike(r"%somevalue%")),
        ),
        (
            None,
            None,
            None,
            "somevalue",
            "name",
            None,
            None,
            None,
            select(MyModel).where(MyModel.name.ilike(r"%somevalue%")),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            ("name",),
            None,
            None,
            select(MyModel).order_by(MyModel.name),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            "name",
            None,
            None,
            select(MyModel).order_by(MyModel.name),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            ("-name",),
            None,
            None,
            select(MyModel).order_by(MyModel.name.desc()),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            "-name",
            None,
            None,
            select(MyModel).order_by(MyModel.name.desc()),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            None,
            1,
            None,
            select(MyModel).limit(1),
        ),
        (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            1,
            select(MyModel).offset(1),
        ),
    ],
)
def test_get_item_list_stmt(  # noqa
    joins: Any,  # noqa
    loads: Any,  # noqa
    filters: Any,  # noqa
    search: Any,  # noqa
    search_by: Any,  # noqa
    order_by: Any,  # noqa
    limit: Any,  # noqa
    offset: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    get_item_list_stmt = query._get_item_list_stmt(
        model=MyModel,
        joins=joins,
        loads=loads,
        filters=filters,
        search=search,
        search_by=search_by,
        order_by=order_by,
        limit=limit,
        offset=offset,
    )
    assert str(get_item_list_stmt) == str(expected_result)


@pytest.mark.parametrize(
    ("data", "expected_result"),
    [
        (None, insert(MyModel).values().returning(MyModel)),
        ({"id": 1}, insert(MyModel).values({"id": 1}).returning(MyModel)),
        ([{"id": 1}], insert(MyModel).values([{"id": 1}]).returning(MyModel)),
    ],
)
def test_db_insert_stmt(data: Any, expected_result: Any) -> None:  # noqa: ANN401
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    db_insert_stmt = query._db_insert_stmt(model=MyModel, data=data)
    assert str(db_insert_stmt) == str(expected_result)


@pytest.mark.parametrize(
    ("data", "expected_result"),
    [
        (None, [MyModel()]),
        ({"id": 1}, [MyModel(id=1)]),
        ([{"id": 1}, None], [MyModel(id=1), MyModel()]),
        ([{"id": 1}, {"id": 2}], [MyModel(id=1), MyModel(id=2)]),
    ],
)
def test_prepare_create_items(data: Any, expected_result: Any) -> None:  # noqa: ANN401
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    prepared_values = query._prepare_create_items(model=MyModel, data=data)
    assert len(prepared_values) == len(expected_result)
    for prepared, expected in zip(prepared_values, prepared_values, strict=True):
        assert prepared.__dict__ == expected.__dict__


@pytest.mark.parametrize(
    (
        "data",
        "filters",
        "expected_result",
    ),
    [
        (
            {"name": 25},
            None,
            update(MyModel).values({"name": 25}).returning(MyModel),
        ),
        (
            {"name": "aboba"},
            {"name": "aboba"},
            update(MyModel).where(MyModel.name == "aboba").values({"name": 25}).returning(MyModel),
        ),
    ],
)
def test_db_update_stmt(  # noqa
    data: Any,  # noqa
    filters: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    db_update_stmt = query._db_update_stmt(
        model=MyModel,
        data=data,
        filters=filters,
    )
    assert str(db_update_stmt) == str(expected_result)


@pytest.mark.parametrize(
    ("filters", "expected_result"),
    [
        (None, delete(MyModel)),
        ({"name": "aboba"}, delete(MyModel).where(MyModel.name == "aboba")),
    ],
)
def test_db_delete_stmt(filters: Any, expected_result: Any):  # noqa
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    db_delete_stmt = query._db_delete_stmt(
        model=MyModel,
        filters=filters,
    )
    assert str(db_delete_stmt) == str(expected_result)


@freeze_time(now)
@pytest.mark.parametrize(
    (
        "ids_to_disable",
        "id_field",
        "disable_field",
        "field_type",
        "allow_filter_by_value",
        "extra_filters",
        "expected_result",
    ),
    [
        (
            {1, 2, 3},
            MyModel.id,
            MyModel.dt,
            datetime.datetime,
            False,
            None,
            update(MyModel).where(MyModel.id.in_([1, 2, 3])).values({MyModel.dt: now}),
        ),
        (
            {1, 2, 3},
            MyModel.id,
            MyModel.bl,
            bool,
            False,
            None,
            update(MyModel).where(MyModel.id.in_([1, 2, 3])).values({MyModel.bl: True}),
        ),
        (
            {1, 2, 3},
            MyModel.id,
            MyModel.bl,
            bool,
            True,
            None,
            update(MyModel)
            .where(MyModel.id.in_([1, 2, 3]), MyModel.bl.is_not(True))
            .values({MyModel.bl: True}),
        ),
    ],
)
def test_disable_items_stmt(  # noqa
    ids_to_disable: Any,  # noqa
    id_field: Any,  # noqa
    disable_field: Any,  # noqa
    field_type: Any,  # noqa
    allow_filter_by_value: Any,  # noqa
    extra_filters: Any,  # noqa
    expected_result: Any,  # noqa
) -> None:  # noqa
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    disable_items_stmt = query._disable_items_stmt(
        model=MyModel,
        ids_to_disable=ids_to_disable,
        id_field=id_field,
        disable_field=disable_field,
        field_type=field_type,
        allow_filter_by_value=allow_filter_by_value,
        extra_filters=extra_filters,
    )
    assert str(disable_items_stmt) == str(expected_result)


def test_disable_items_stmt_type_error():  # noqa
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    with pytest.raises(QueryError):
        query._disable_items_stmt(
            model=MyModel,
            ids_to_disable={1, 2, 3},
            id_field=MyModel.id,
            disable_field=MyModel.bl,
            field_type=str,  # type: ignore
            allow_filter_by_value=True,
            extra_filters=None,
        )


def test_disable_items_stmt_value_error():  # noqa
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    with pytest.raises(
        QueryError,
        match='Parameter "ids_to_disable" should contains at least one element.',
    ):
        query._disable_items_stmt(
            model=MyModel,
            ids_to_disable=set(),
            id_field=MyModel.id,
            disable_field=MyModel.bl,
            field_type=bool,
            allow_filter_by_value=True,
            extra_filters=None,
        )


@pytest.mark.parametrize(
    ('filters', "expected_result"),
    [
        (None, select(exists().select_from(MyModel))),
        ({"id": 25}, select(exists().where(MyModel.id == 25))),
    ],
)
def test_exists_items_stmt(
    filters: Any,  # noqa
    expected_result: bool,  # noqa
) -> None:
    query = BaseQuery(filter_converter=SimpleFilterConverter())
    disable_items_stmt = query._exists_items_stmt(model=MyModel, filters=filters)
    assert str(disable_items_stmt) == str(expected_result)
