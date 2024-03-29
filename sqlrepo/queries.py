import datetime
import re
from typing import TYPE_CHECKING, Any, Callable, Literal, NotRequired, TypedDict, TypeVar

from sqlalchemy import CursorResult, and_, delete
from sqlalchemy import exc as sqlalchemy_exc
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import joinedload

from sqlrepo.filters.converters import BaseFilterConverter
from sqlrepo.logging import logger
from sqlrepo.utils import apply_joins, apply_loads, get_sqlalchemy_attribute, get_utc_now


class JoinKwargs(TypedDict):
    """Kwargs for join statement."""

    isouter: NotRequired[bool]
    full: NotRequired[bool]


if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import DeclarativeBase as Base
    from sqlalchemy.orm import QueryableAttribute
    from sqlalchemy.orm.attributes import InstrumentedAttribute
    from sqlalchemy.orm.session import Session
    from sqlalchemy.orm.strategy_options import _AbstractLoad  # type: ignore
    from sqlalchemy.sql._typing import _ColumnExpressionOrStrLabelArgument  # type: ignore
    from sqlalchemy.sql.dml import Delete, ReturningUpdate, Update
    from sqlalchemy.sql.elements import ColumnElement
    from sqlalchemy.sql.selectable import Select

    BaseSQLAlchemyModel = TypeVar('BaseSQLAlchemyModel', bound=Base)
    T = TypeVar('T')
    Count = int
    Deleted = bool
    Model = type[Base]
    JoinClause = ColumnElement[bool]
    ModelWithOnclause = tuple[Model, JoinClause]
    CompleteModel = tuple[Model, JoinClause, JoinKwargs]
    Join = str | Model | ModelWithOnclause | CompleteModel
    Filter = dict[str, Any] | Sequence[dict[str, Any] | ColumnElement[bool]] | ColumnElement[bool]
    Load = str | _AbstractLoad
    SearchParam = str | QueryableAttribute[Any]
    ColumnParam = str | QueryableAttribute[Any]
    OrderByParam = _ColumnExpressionOrStrLabelArgument[Any]
    DataDict = dict[str, Any]


class BaseQuery:
    """"""

    def __init__(
        self,
        filter_converter_class: type[BaseFilterConverter],
        specific_column_mapping: dict[str, "ColumnElement[Any]"] | None = None,
        load_strategy: Callable[..., '_AbstractLoad'] = joinedload,
    ) -> None:
        self.specific_column_mapping = specific_column_mapping
        self.filter_converter_class = filter_converter_class
        self.load_strategy = load_strategy

    def _resolve_specific_columns(
        self,
        *,
        elements: 'Sequence[T]',
    ) -> 'Sequence[T]':
        if not self.specific_column_mapping:
            return elements
        new_elements: 'list[T]' = []
        for ele in elements:
            if not isinstance(ele, str) or ele not in self.specific_column_mapping:
                new_elements.append(ele)
            else:
                new_elements.append(self.specific_column_mapping[ele])  # type: ignore
        return new_elements

    def _resolve_and_apply_joins(
        self,
        *,
        stmt: 'Select[tuple[T]]',
        joins: 'Sequence[Join]',
    ) -> 'Select[tuple[T]]':
        """"""
        for join in joins:
            if isinstance(join, tuple | list):
                target, clause, *kw_list = join
                join_kwargs = kw_list[0] if len(kw_list) == 1 else JoinKwargs()
                stmt = stmt.join(target, clause, **join_kwargs)
            elif isinstance(join, str):
                stmt = apply_joins(stmt, join)
            else:
                stmt = stmt.join(join)
        return stmt

    def _resolve_and_apply_loads(
        self,
        *,
        stmt: 'Select[tuple[T]]',
        loads: 'Sequence[Load]',
    ) -> 'Select[tuple[T]]':
        """"""
        for load in loads:
            stmt = (
                apply_loads(stmt, load, load_strategy=self.load_strategy)
                if isinstance(load, str)
                else stmt.options(load)
            )
        return stmt

    def _make_disable_filters(  # noqa: C901
        self,
        *,
        model: 'type[BaseSQLAlchemyModel]',
        id_field: 'QueryableAttribute[Any]',
        ids_to_disable: set[Any],
        disable_field: 'QueryableAttribute[Any]',
        field_type: type[datetime.datetime] | type[bool] = datetime.datetime,
        allow_filter_by_value: bool = True,
        extra_filters: 'Filter | None' = None,
    ) -> list['ColumnElement[bool]']:
        """

        Parameters
        ----------

        Returns
        -------
        """
        filters: list['ColumnElement[bool]'] = list()
        filters.append(id_field.in_(ids_to_disable))
        if allow_filter_by_value and field_type == bool:
            filters.append(disable_field.is_not(True))
        elif allow_filter_by_value and field_type == datetime.datetime:
            filters.append(disable_field.is_(None))
        if extra_filters is not None:
            sqlalchemy_filters = self.filter_converter_class.convert(model, extra_filters)
            filters.extend(sqlalchemy_filters)
        return filters

    def _make_search_filter(
        self,
        search: str,
        model: type['BaseSQLAlchemyModel'],
        *search_by_args: 'SearchParam',
        use_and_clause: bool = False,
        # TODO: добавить флаг case_insensitive: bool = True
    ) -> 'ColumnElement[bool]':
        """"""
        filters: list['ColumnElement[bool]'] = []
        search_by_args = self._resolve_specific_columns(elements=search_by_args)  # type: ignore
        for search_by in search_by_args:
            if isinstance(search_by, str):
                column = get_sqlalchemy_attribute(model, search_by)
                clause = column.ilike(f'%{search}%')
                filters.append(clause)
            else:
                filters.append(search_by.ilike(f'%{search}%'))
        if use_and_clause:
            return and_(*filters)
        return or_(*filters)

    def _get_item_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
    ) -> 'Select[tuple[BaseSQLAlchemyModel]]':
        """"""
        stmt = select(model)
        if joins is not None:
            stmt = self._resolve_and_apply_joins(stmt=stmt, joins=joins)
        if loads is not None:
            stmt = self._resolve_and_apply_loads(
                stmt=stmt,
                loads=loads,
            )
        if filters is not None:
            sqlalchemy_filters = self.filter_converter_class.convert(model, filters)
            stmt = stmt.where(*sqlalchemy_filters)
        return stmt

    def _get_items_count_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        filters: 'Filter | None' = None,
    ) -> 'Select[tuple[int]]':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = select(func.count()).select_from(model)
        if joins is not None:
            stmt = self._resolve_and_apply_joins(stmt=stmt, joins=joins)
        if filters is not None:
            sqlalchemy_filters = self.filter_converter_class.convert(model, filters)
            stmt = stmt.where(*sqlalchemy_filters)
        return stmt

    def _get_item_list_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
        filters: 'Filter | None' = None,
        search: str | None = None,
        search_by: 'Sequence[SearchParam] | None' = None,
        order_by: 'Sequence[OrderByParam] | None' = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> 'Select[tuple[BaseSQLAlchemyModel]]':
        stmt = self._get_item_stmt(model=model, filters=filters, joins=joins, loads=loads)
        if search is not None and search_by is not None:
            search = re.escape(search)
            search = search.translate(str.maketrans({'%': r'\%', '_': r'\_', '/': r'\/'}))
            stmt = stmt.where(self._make_search_filter(search, model, *search_by))
        if order_by is not None:
            stmt = stmt.order_by(*self._resolve_specific_columns(elements=order_by))
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        return stmt

    def _db_update_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        data: 'DataDict',
        filters: 'Filter | None' = None,
    ) -> 'ReturningUpdate[tuple[BaseSQLAlchemyModel]]':
        stmt = update(model)
        if filters is not None:
            sqlalchemy_filters = self.filter_converter_class.convert(model, filters)
            stmt = stmt.where(*sqlalchemy_filters)
        stmt = stmt.values(**data).returning(model)
        return stmt

    def _db_delete_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
    ) -> 'Delete':
        stmt = delete(model)
        if filters is not None:
            sqlalchemy_filters = self.filter_converter_class.convert(model, filters)
            stmt = stmt.where(*sqlalchemy_filters)
        return stmt

    def _disable_items_stmt(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        ids_to_disable: set[Any],
        id_field: 'InstrumentedAttribute[Any]',
        disable_field: 'InstrumentedAttribute[Any]',
        field_type: type[datetime.datetime] | type[bool] = datetime.datetime,
        allow_filter_by_value: bool = True,
        extra_filters: 'Filter | None' = None,
    ) -> 'Update | Count':
        if issubclass(field_type, bool):
            field_value = True
        elif issubclass(field_type, datetime.datetime):  # type: ignore
            field_value = get_utc_now()
        else:
            # msg = (
            #     f'Параметр "field_type" должен быть одним из следующих: bool, datetime. '
            #     f'Был передан {field_type}.'
            # )
            msg = ''  # FIXME
            raise TypeError(msg)
        if not ids_to_disable:
            return 0
        try:
            filters = self._make_disable_filters(
                model=model,
                ids_to_disable=ids_to_disable,
                id_field=id_field,
                disable_field=disable_field,
                field_type=field_type,
                allow_filter_by_value=allow_filter_by_value,
                extra_filters=extra_filters,
            )
        except AttributeError:
            params = dict(
                model=model,
                ids_to_disable=ids_to_disable,
                id_field=id_field,
                disable_field=disable_field,
                field_type=field_type,
                allow_filter_by_value=allow_filter_by_value,
                extra_filters=extra_filters,
            )
            logger.exception(
                '',  # FIXME
                params,
            )
            return 0
        stmt = update(model).where(*filters).values({disable_field: field_value})
        return stmt


class BaseSyncQuery(BaseQuery):
    """"""

    def __init__(
        self,
        session: 'Session',
        filter_converter_class: type[BaseFilterConverter],
        specific_column_mapping: dict[str, "ColumnElement[Any]"] | None = None,
        load_strategy: Callable[[Any], '_AbstractLoad'] = joinedload,
    ) -> None:
        self.session = session
        super().__init__(filter_converter_class, specific_column_mapping, load_strategy)

    def get_item(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
    ) -> 'BaseSQLAlchemyModel | None':
        """

        Parameters
        ----------

        Returns
        -------

        Raises
        ------
        """
        stmt = self._get_item_stmt(
            model=model,
            filters=filters,
            joins=joins,
            loads=loads,
        )
        result = self.session.scalars(stmt)
        return result.first()

    def get_items_count(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        filters: 'Filter | None' = None,
    ) -> int:
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._get_items_count_stmt(
            model=model,
            joins=joins,
            filters=filters,
        )
        count = self.session.scalar(stmt)
        if count is None:
            count = 0
        return count

    def get_item_list(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
        filters: 'Filter | None' = None,
        search: str | None = None,
        search_by: 'Sequence[SearchParam] | None' = None,
        order_by: 'Sequence[OrderByParam] | None' = None,
        limit: int | None = None,
        offset: int | None = None,
        unique_items: bool = False,
    ) -> 'Sequence[BaseSQLAlchemyModel]':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._get_item_list_stmt(
            model=model,
            joins=joins,
            loads=loads,
            filters=filters,
            search=search,
            search_by=search_by,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        result = self.session.scalars(stmt)
        if unique_items:
            return result.unique().all()
        return result.all()

    def create_item(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        data: 'DataDict | None' = None,
        use_flush: bool = False,
    ) -> 'BaseSQLAlchemyModel':
        """

        Parameters
        ----------

        Returns
        -------
        """
        item = model() if data is None else model(**data)
        self.session.add(item)
        if use_flush:
            self.session.flush()
        else:
            self.session.commit()

        # FIXME
        # logger.debug(
        #     'Создание в БД: успешное создание. Экземпляр: %s. %s.',
        #     item,
        #     'Создание без фиксирования.' if use_flush else 'Создание и фиксирование.',
        # )
        return item

    def db_update(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        data: 'DataDict',
        filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Sequence[BaseSQLAlchemyModel] | None':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._db_update_stmt(
            model=model,
            data=data,
            filters=filters,
        )
        result = self.session.scalars(stmt)
        if use_flush:
            self.session.flush()
        else:
            self.session.commit()
        return result.unique().all()

    def change_item(
        self,
        *,
        data: 'DataDict',
        item: 'BaseSQLAlchemyModel',
        set_none: bool = False,
        allowed_none_fields: 'Literal["*"] | Sequence[str]' = '*',
        use_flush: bool = False,
    ) -> 'tuple[bool, BaseSQLAlchemyModel]':
        """

        Parameters
        ----------

        Returns
        -------
        """
        is_updated = False
        if not set_none:
            data = {key: value for key, value in data.items() if value is not None}
        for field, value in data.items():
            if (
                set_none
                and value is None
                and (allowed_none_fields != '*' and field not in allowed_none_fields)
            ):
                continue
            if not is_updated and getattr(item, field, None) != value:
                is_updated = True
            setattr(item, field, value)
        if use_flush:
            self.session.flush()
        else:
            self.session.commit()
        # FIXME
        # logger.debug(
        #     (
        #         'Обновление строки БД: успешное обновление. Экземпляр: %r. Параметры: %s, '
        #         'set_none: %s, use_flush: %s.'
        #     ),
        #     item,
        #     data,
        #     set_none,
        #     use_flush,
        # )
        return is_updated, item

    def db_delete(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Count':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._db_delete_stmt(
            model=model,
            filters=filters,
        )
        result = self.session.execute(stmt)
        if use_flush:
            self.session.flush()
        else:
            self.session.commit()
        if isinstance(result, CursorResult):  # type: ignore
            return result.rowcount
        # FIXME
        # не получится узнать реальное количество измененных сущностей. Поэтому 0.
        return 0

    def delete_item(
        self,
        *,
        item: 'Base',
        use_flush: bool = False,
    ) -> 'Deleted':
        """

        Parameters
        ----------

        Returns
        -------
        """
        item_repr = repr(item)
        try:
            self.session.delete(item)
            if use_flush:
                self.session.flush()
            else:
                self.session.commit()
        except sqlalchemy_exc.SQLAlchemyError as exc:
            self.session.rollback()
            # FIXME
            # logger.warning('Удаление из БД: ошибка удаления: %s', exc)
            return False
        # FIXME
        # logger.debug('Удаление из БД: успешное удаление. Экземпляр: %s', item_repr)
        return True

    def disable_items(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        ids_to_disable: set[Any],
        id_field: 'InstrumentedAttribute[Any]',
        disable_field: 'InstrumentedAttribute[Any]',
        field_type: type[datetime.datetime] | type[bool] = datetime.datetime,
        allow_filter_by_value: bool = True,
        extra_filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Count':
        """

        Parameters
        ----------

        Returns
        -------

        Raises
        ------
        TypeError
        AttributeError
        """
        stmt = self._disable_items_stmt(
            model=model,
            ids_to_disable=ids_to_disable,
            id_field=id_field,
            disable_field=disable_field,
            field_type=field_type,
            allow_filter_by_value=allow_filter_by_value,
            extra_filters=extra_filters,
        )
        if isinstance(stmt, int):
            return stmt
        result = self.session.execute(stmt)
        if use_flush:
            self.session.flush()
        else:
            self.session.commit()
        # FIXME
        # только в CursorResult есть атрибут rowcount
        if isinstance(result, CursorResult):  # type: ignore
            return result.rowcount
        # FIXME
        # не получится узнать реальное количество измененных сущностей. Поэтому 0.
        return 0


class BaseAsyncQuery(BaseQuery):
    """Base async query class."""

    def __init__(
        self,
        session: 'AsyncSession',
        filter_converter_class: type[BaseFilterConverter],
        specific_column_mapping: dict[str, "ColumnElement[Any]"] | None = None,
        load_strategy: Callable[..., '_AbstractLoad'] = joinedload,
    ) -> None:
        self.session = session
        super().__init__(filter_converter_class, specific_column_mapping, load_strategy)

    async def get_item(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
    ) -> 'BaseSQLAlchemyModel | None':
        """

        Parameters
        ----------

        Returns
        -------

        Raises
        ------
        """
        stmt = self._get_item_stmt(
            model=model,
            filters=filters,
            joins=joins,
            loads=loads,
        )
        result = await self.session.scalars(stmt)
        return result.first()

    async def get_items_count(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        filters: 'Filter | None' = None,
    ) -> int:
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._get_items_count_stmt(
            model=model,
            joins=joins,
            filters=filters,
        )
        count = await self.session.scalar(stmt)
        if count is None:
            count = 0
        return count

    async def get_item_list(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        joins: 'Sequence[Join] | None' = None,
        loads: 'Sequence[Load] | None' = None,
        filters: 'Filter | None' = None,
        search: str | None = None,
        search_by: 'Sequence[SearchParam] | None' = None,
        order_by: 'Sequence[OrderByParam] | None' = None,
        limit: int | None = None,
        offset: int | None = None,
        unique_items: bool = False,
    ) -> 'Sequence[BaseSQLAlchemyModel]':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._get_item_list_stmt(
            model=model,
            joins=joins,
            loads=loads,
            filters=filters,
            search=search,
            search_by=search_by,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )
        result = await self.session.scalars(stmt)
        if unique_items:
            return result.unique().all()
        return result.all()

    async def create_item(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        data: 'DataDict | None' = None,
        use_flush: bool = False,
    ) -> 'BaseSQLAlchemyModel':
        """

        Parameters
        ----------

        Returns
        -------
        """
        item = model() if data is None else model(**data)
        self.session.add(item)
        if use_flush:
            await self.session.flush()
        else:
            await self.session.commit()

        # FIXME
        # logger.debug(
        #     'Создание в БД: успешное создание. Экземпляр: %s. %s.',
        #     item,
        #     'Создание без фиксирования.' if use_flush else 'Создание и фиксирование.',
        # )
        return item

    async def db_update(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        data: 'DataDict',
        filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Sequence[BaseSQLAlchemyModel] | None':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._db_update_stmt(
            model=model,
            data=data,
            filters=filters,
        )
        result = await self.session.scalars(stmt)
        if use_flush:
            await self.session.flush()
        else:
            await self.session.commit()
        return result.unique().all()

    async def change_item(
        self,
        *,
        data: 'DataDict',
        item: 'BaseSQLAlchemyModel',
        set_none: bool = False,
        allowed_none_fields: 'Literal["*"] | Sequence[str]' = '*',
        use_flush: bool = False,
    ) -> 'tuple[bool, BaseSQLAlchemyModel]':
        """

        Parameters
        ----------

        Returns
        -------
        """
        is_updated = False
        if not set_none:
            data = {key: value for key, value in data.items() if value is not None}
        for field, value in data.items():
            if (
                set_none
                and value is None
                and (allowed_none_fields != '*' and field not in allowed_none_fields)
            ):
                continue
            if not is_updated and getattr(item, field, None) != value:
                is_updated = True
            setattr(item, field, value)
        if use_flush:
            await self.session.flush()
        else:
            await self.session.commit()
        # FIXME
        # logger.debug(
        #     (
        #         'Обновление строки БД: успешное обновление. Экземпляр: %r. Параметры: %s, '
        #         'set_none: %s, use_flush: %s.'
        #     ),
        #     item,
        #     data,
        #     set_none,
        #     use_flush,
        # )
        return is_updated, item

    async def db_delete(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Count':
        """

        Parameters
        ----------

        Returns
        -------
        """
        stmt = self._db_delete_stmt(
            model=model,
            filters=filters,
        )
        result = await self.session.execute(stmt)
        if use_flush:
            await self.session.flush()
        else:
            await self.session.commit()
        if isinstance(result, CursorResult):  # type: ignore
            return result.rowcount
        # FIXME
        # не получится узнать реальное количество измененных сущностей. Поэтому 0.
        return 0

    async def delete_item(
        self,
        *,
        item: 'Base',
        use_flush: bool = False,
    ) -> 'Deleted':
        """

        Parameters
        ----------

        Returns
        -------
        """
        item_repr = repr(item)
        try:
            await self.session.delete(item)
            if use_flush:
                await self.session.flush()
            else:
                await self.session.commit()
        except sqlalchemy_exc.SQLAlchemyError as exc:
            await self.session.rollback()
            # FIXME
            # logger.warning('Удаление из БД: ошибка удаления: %s', exc)
            return False
        # FIXME
        # logger.debug('Удаление из БД: успешное удаление. Экземпляр: %s', item_repr)
        return True

    async def disable_items(
        self,
        *,
        model: type['BaseSQLAlchemyModel'],
        ids_to_disable: set[Any],
        id_field: 'InstrumentedAttribute[Any]',
        disable_field: 'InstrumentedAttribute[Any]',
        field_type: type[datetime.datetime] | type[bool] = datetime.datetime,
        allow_filter_by_value: bool = True,
        extra_filters: 'Filter | None' = None,
        use_flush: bool = False,
    ) -> 'Count':
        """

        Parameters
        ----------

        Returns
        -------
        int


        Raises
        ------
        TypeError
        AttributeError
        """
        stmt = self._disable_items_stmt(
            model=model,
            ids_to_disable=ids_to_disable,
            id_field=id_field,
            disable_field=disable_field,
            field_type=field_type,
            allow_filter_by_value=allow_filter_by_value,
            extra_filters=extra_filters,
        )
        if isinstance(stmt, int):
            return stmt
        result = await self.session.execute(stmt)
        if use_flush:
            await self.session.flush()
        else:
            await self.session.commit()
        # FIXME
        # только в CursorResult есть атрибут rowcount
        if isinstance(result, CursorResult):  # type: ignore
            return result.rowcount
        # FIXME
        # не получится узнать реальное количество измененных сущностей. Поэтому 0.
        return 0
