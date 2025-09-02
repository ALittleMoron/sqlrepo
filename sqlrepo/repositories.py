"""Main implementations for sqlrepo project."""

import importlib
import warnings
from dataclasses import dataclass, field
from inspect import isclass
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    ForwardRef,
    Generic,
    TypeVar,
    get_args,
)

from sqlalchemy.orm import DeclarativeBase as Base

from sqlrepo import exc as sqlrepo_exc
from sqlrepo.abc import AbstractAsyncRepository, AbstractSyncRepository
from sqlrepo.config import RepositoryConfig
from sqlrepo.constants import (
    REPOSITORY_GENERIC_TYPE_IS_NOT_CLASS_WARNING,
    REPOSITORY_GENERIC_TYPE_IS_NOT_MODEL,
    REPOSITORY_GENERIC_TYPE_NOT_PASSED_WARNING,
    REPOSITORY_GENERIC_TYPE_TYPE_VAR_PASSED_WARNING,
    REPOSITORY_GET_MODULE_INSTANCE_ERROR_TEMPLATE,
    REPOSITORY_GETTING_GENERIC_INFO_WARNING_TEMPLATE,
    REPOSITORY_MODEL_ALREADY_DEFINED_WARNING,
    REPOSITORY_NO_GENERIC_INHERITANCE_WARNING,
    REPOSITORY_RESOLVE_FORWARD_REF_WARNING_TEMPLATE,
    REPOSITORY_VALIDATE_DISABLE_ATTRIBUTES_ERROR,
)
from sqlrepo.logger import RepositoryModelClassIncorrectUseWarning, default_logger
from sqlrepo.queries import BaseAsyncQuery, BaseSyncQuery
from sqlrepo.types import BaseSQLAlchemyModel
from sqlrepo.wrappers import wrap_any_exception_manager

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm.session import Session

    # noinspection PyUnresolvedReferences
    from sqlrepo.types import (
        Count,
        DataDict,
        Filters,
        IsUpdated,
        Joins,
        Loads,
        LoggerProtocol,
        OrderByParams,
        SearchByParams,
    )


def extract_model_from_generic(cls: type[Any]) -> "type[Base] | None":  # noqa: PLR0911 PLR0912 C901
    """Iterate through cls generics and returns SQLAlchemy declarative model.

    If there are errors in inheritance or problem with extracting model, it causes None return.
    """
    if hasattr(cls, "model_class"):
        warnings.warn(
            REPOSITORY_MODEL_ALREADY_DEFINED_WARNING,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    # NOTE: impossible situation. May be reproduced if user manually delete generic from inherited
    #       class.
    if not hasattr(cls, '__orig_bases__'):  # pragma: no coverage
        warnings.warn(
            REPOSITORY_NO_GENERIC_INHERITANCE_WARNING,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    model = None
    # PEP-560: https://peps.python.org/pep-0560/
    exceptions = []
    for base in cls.__orig_bases__:
        try:
            if issubclass(base.__origin__, BaseRepository):
                model = get_args(base)[0]
                break
        except (TypeError, IndexError, AttributeError) as exc:
            exceptions.append(exc)
    if model is None or len(cls.__orig_bases__) == 0:
        warnings.warn(
            REPOSITORY_GENERIC_TYPE_NOT_PASSED_WARNING,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    if len(exceptions) == len(cls.__orig_bases__):
        warnings.warn(
            REPOSITORY_GETTING_GENERIC_INFO_WARNING_TEMPLATE.format(cls=cls, exc=exceptions),
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    if isinstance(model, ForwardRef):
        try:
            repo_module = vars(cls).get("__module__")
            if not repo_module:  # pragma: no coverage
                msg = REPOSITORY_GET_MODULE_INSTANCE_ERROR_TEMPLATE.format(cls=cls)
                raise TypeError(msg)  # noqa: TRY301
            model_globals = vars(importlib.import_module(repo_module))
            model = eval(model.__forward_arg__, model_globals)  # noqa: S307
        except (ImportError, TypeError, AttributeError, NameError) as exc:
            warnings.warn(
                REPOSITORY_RESOLVE_FORWARD_REF_WARNING_TEMPLATE.format(exc=exc),
                RepositoryModelClassIncorrectUseWarning,
                stacklevel=2,
            )
            return None
    if isinstance(model, TypeVar):
        warnings.warn(
            REPOSITORY_GENERIC_TYPE_TYPE_VAR_PASSED_WARNING,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    if not isclass(model):
        warnings.warn(
            REPOSITORY_GENERIC_TYPE_IS_NOT_CLASS_WARNING,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    if not issubclass(model, Base):
        warnings.warn(
            REPOSITORY_GENERIC_TYPE_IS_NOT_MODEL,
            RepositoryModelClassIncorrectUseWarning,
            stacklevel=2,
        )
        return None
    return model


@dataclass()
class BaseRepository(Generic[BaseSQLAlchemyModel]):
    """Base repository class.

    Don't Use it directly. Use BaseAsyncRepository and BaseSyncRepository, or pass query_class
    directly (not recommended.)
    """

    __inheritance_check_model_class__: ClassVar[bool] = True
    """
    Private custom magic property.

    Use it, if you want to inherit Repository without checking model_class attribute.
    """

    model_class: ClassVar[type["BaseSQLAlchemyModel"]]  # type: ignore[reportGeneralTypeIssues]
    """
    Model class for repository.

    You can set this option manually, but it is not recommended. Repository will automatically
    add model_class attribute by extracting it from Generic type.

    Use case:

    ```
    from my_package.models import Admin

    class AdminRepository(BaseSyncRepository[Admin]):
        pass

    # So, when you will use AdminRepository, model_class attribute will be set with Admin
    # automatically.
    ```
    """

    config: ClassVar[RepositoryConfig] = RepositoryConfig()
    """Repository config, that contains all settings.

    To add your own settings, inherit RepositoryConfig and add your own fields, then init it in
    your Repository class as class variable.
    """

    @classmethod
    def _validate_disable_attributes(cls) -> None:
        if (
            cls.config.disable_id_field is None
            or cls.config.disable_field is None
            or cls.config.disable_field_type is None
        ):
            raise sqlrepo_exc.RepositoryAttributeError(REPOSITORY_VALIDATE_DISABLE_ATTRIBUTES_ERROR)

    def __init_subclass__(cls) -> None:  # noqa: D105
        super().__init_subclass__()
        if cls.__inheritance_check_model_class__ is False:
            cls.__inheritance_check_model_class__ = True
            return
        model_class = extract_model_from_generic(cls)
        if model_class is None:
            return
        cls.model_class = model_class  # type: ignore[reportAttributeAccessIssue]


@dataclass()
class BaseAsyncRepository(BaseRepository[BaseSQLAlchemyModel]):
    """Base repository class with async interface.

    Has main CRUD methods for working with model. Use async session of SQLAlchemy to work with this
    class.
    """

    __inheritance_check_model_class__ = False

    session: "AsyncSession" = field()
    logger: "LoggerProtocol" = field(default=default_logger)
    query_class: type["BaseAsyncQuery"] = field(default=BaseAsyncQuery)
    queries: BaseAsyncQuery = field(init=False)

    def __post_init__(self) -> None:  # noqa: D105
        self.queries = self.query_class(
            session=self.session,
            filter_converter=self.config.get_filter_convert(),
            specific_column_mapping=self.config.specific_column_mapping,
            logger=self.logger,
        )

    async def _get(
        self,
        *,
        filters: "Filters",
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
    ) -> "BaseSQLAlchemyModel | None":
        """Get one instance of model_class by given filters."""
        with wrap_any_exception_manager():
            return await self.queries.get_item(
                model=self.model_class,
                joins=joins,
                loads=loads,
                filters=filters,
            )

    async def _count(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
    ) -> int:
        """Get count of instances of model_class by given filters."""
        with wrap_any_exception_manager():
            return await self.queries.get_items_count(
                model=self.model_class,
                joins=joins,
                filters=filters,
            )

    async def _exists(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> bool:
        """Check rows in table for existing."""
        with wrap_any_exception_manager():
            return await self.queries.items_exists(
                model=self.model_class,
                filters=filters,
            )

    async def _list(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
        search: str | None = None,
        search_by: "SearchByParams | None" = None,
        order_by: "OrderByParams | None" = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> "list[BaseSQLAlchemyModel]":
        """Get list of instances of model_class."""
        with wrap_any_exception_manager():
            return await self.queries.get_item_list(
                model=self.model_class,
                joins=joins,
                loads=loads,
                filters=filters,
                search=search,
                search_by=search_by,
                order_by=order_by,
                limit=limit,
                offset=offset,
                unique_items=self.config.unique_list_items,
            )

    async def _bulk_create(
        self,
        *,
        data: "Sequence[DataDict]",
    ) -> "list[BaseSQLAlchemyModel]":
        """Create sequence model_class of instances from given data."""
        with wrap_any_exception_manager():
            return await self.queries.db_create(
                model=self.model_class,
                data=data,
            )

    async def _create(
        self,
        *,
        data: "DataDict | None",
    ) -> "BaseSQLAlchemyModel":
        """Create model_class instance from given data."""
        with wrap_any_exception_manager():
            return await self.queries.db_create(
                model=self.model_class,
                data=data,
            )

    async def _update(
        self,
        *,
        data: "DataDict",
        filters: "Filters | None" = None,
    ) -> "list[BaseSQLAlchemyModel] | None":
        """Update model_class from given data."""
        with wrap_any_exception_manager():
            return await self.queries.db_update(
                model=self.model_class,
                data=data,
                filters=filters,
                use_flush=self.config.use_flush,
            )

    async def _update_instance(
        self,
        *,
        instance: "BaseSQLAlchemyModel",
        data: "DataDict",
    ) -> "tuple[IsUpdated, BaseSQLAlchemyModel]":
        """Update model_class instance from given data.

        Returns tuple with boolean (was instance updated or not) and updated instance.
        """
        with wrap_any_exception_manager():
            return await self.queries.change_item(
                data=data,
                item=instance,
                set_none=self.config.update_set_none,
                allowed_none_fields=self.config.update_allowed_none_fields,
                use_flush=self.config.use_flush,
            )

    async def _delete(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> "Count":
        """Delete model_class in db by given filters."""
        with wrap_any_exception_manager():
            return await self.queries.db_delete(
                model=self.model_class,
                filters=filters,
                use_flush=self.config.use_flush,
            )

    async def _disable(
        self,
        *,
        ids_to_disable: set[Any],
        extra_filters: "Filters | None" = None,
    ) -> "Count":
        """Disable model_class instances with given ids and extra_filters."""
        with wrap_any_exception_manager():
            self._validate_disable_attributes()
            return await self.queries.disable_items(
                model=self.model_class,
                ids_to_disable=ids_to_disable,
                id_field=self.config.disable_id_field,  # type: ignore[reportArgumentType]
                disable_field=self.config.disable_field,  # type: ignore[reportArgumentType]
                field_type=self.config.disable_field_type,  # type: ignore[reportArgumentType]
                allow_filter_by_value=self.config.allow_disable_filter_by_value,
                extra_filters=extra_filters,
                use_flush=self.config.use_flush,
            )


@dataclass()
class BaseSyncRepository(BaseRepository[BaseSQLAlchemyModel]):
    """Base repository class with sync interface.

    Has main CRUD methods for working with model. Use sync session of SQLAlchemy to work with this
    class.
    """

    __inheritance_check_model_class__ = False

    session: "Session" = field()
    logger: "LoggerProtocol" = field(default=default_logger)
    query_class: type["BaseSyncQuery"] = field(default=BaseSyncQuery)
    queries: BaseSyncQuery = field(init=False)

    def __post_init__(self) -> None:  # noqa: D105
        self.queries = self.query_class(
            session=self.session,
            filter_converter=self.config.get_filter_convert(),
            specific_column_mapping=self.config.specific_column_mapping,
            logger=self.logger,
        )

    def _get(
        self,
        *,
        filters: "Filters",
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
    ) -> "BaseSQLAlchemyModel | None":
        """Get one instance of model_class by given filters."""
        with wrap_any_exception_manager():
            return self.queries.get_item(
                model=self.model_class,
                joins=joins,
                loads=loads,
                filters=filters,
            )

    def _count(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
    ) -> int:
        """Get count of instances of model_class by given filters."""
        with wrap_any_exception_manager():
            return self.queries.get_items_count(
                model=self.model_class,
                joins=joins,
                filters=filters,
            )

    def _exists(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> bool:
        """Check rows in table for existing."""
        with wrap_any_exception_manager():
            return self.queries.items_exists(
                model=self.model_class,
                filters=filters,
            )

    def _list(
        self,
        *,
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
        filters: "Filters | None" = None,
        search: str | None = None,
        search_by: "SearchByParams | None" = None,
        order_by: "OrderByParams | None" = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> "list[BaseSQLAlchemyModel]":
        """Get list of instances of model_class."""
        with wrap_any_exception_manager():
            return self.queries.get_item_list(
                model=self.model_class,
                joins=joins,
                loads=loads,
                filters=filters,
                search=search,
                search_by=search_by,
                order_by=order_by,
                limit=limit,
                offset=offset,
                unique_items=self.config.unique_list_items,
            )

    def _bulk_create(
        self,
        *,
        data: "Sequence[DataDict]",
    ) -> "list[BaseSQLAlchemyModel]":
        """Create sequence model_class of instances from given data."""
        with wrap_any_exception_manager():
            return self.queries.db_create(
                model=self.model_class,
                data=data,
            )

    def _create(
        self,
        *,
        data: "DataDict | None",
    ) -> "BaseSQLAlchemyModel":
        """Create model_class instance from given data."""
        with wrap_any_exception_manager():
            return self.queries.db_create(
                model=self.model_class,
                data=data,
            )

    def _update(
        self,
        *,
        data: "DataDict",
        filters: "Filters | None" = None,
    ) -> "list[BaseSQLAlchemyModel] | None":
        """Update model_class from given data."""
        with wrap_any_exception_manager():
            return self.queries.db_update(
                model=self.model_class,
                data=data,
                filters=filters,
                use_flush=self.config.use_flush,
            )

    def _update_instance(
        self,
        *,
        instance: "BaseSQLAlchemyModel",
        data: "DataDict",
    ) -> "tuple[IsUpdated, BaseSQLAlchemyModel]":
        """Update model_class instance from given data.

        Returns tuple with boolean (was instance updated or not) and updated instance.
        """
        with wrap_any_exception_manager():
            return self.queries.change_item(
                data=data,
                item=instance,
                set_none=self.config.update_set_none,
                allowed_none_fields=self.config.update_allowed_none_fields,
                use_flush=self.config.use_flush,
            )

    def _delete(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> "Count":
        """Delete model_class in db by given filters."""
        with wrap_any_exception_manager():
            return self.queries.db_delete(
                model=self.model_class,
                filters=filters,
                use_flush=self.config.use_flush,
            )

    def _disable(
        self,
        *,
        ids_to_disable: set[Any],
        extra_filters: "Filters | None" = None,
    ) -> "Count":
        """Disable model_class instances with given ids and extra_filters."""
        with wrap_any_exception_manager():
            self._validate_disable_attributes()
            return self.queries.disable_items(
                model=self.model_class,
                ids_to_disable=ids_to_disable,
                id_field=self.config.disable_id_field,  # type: ignore[reportArgumentType]
                disable_field=self.config.disable_field,  # type: ignore[reportArgumentType]
                field_type=self.config.disable_field_type,  # type: ignore[reportArgumentType]
                allow_filter_by_value=self.config.allow_disable_filter_by_value,
                extra_filters=extra_filters,
                use_flush=self.config.use_flush,
            )


class AsyncRepository(BaseAsyncRepository[BaseSQLAlchemyModel], AbstractAsyncRepository):
    """Async repository class with implemented base methods."""

    __inheritance_check_model_class__ = False

    async def get(
        self,
        *,
        filters: "Filters",
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
    ) -> "BaseSQLAlchemyModel | None":
        """Get one instance of model_class by given filters."""
        return await self._get(filters=filters, joins=joins, loads=loads)

    async def count(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
    ) -> int:
        """Get count of instances of model_class by given filters."""
        return await self._count(filters=filters, joins=joins)

    async def exists(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> bool:
        """Check rows in table for existing."""
        return await self._exists(filters=filters)

    async def list(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
        search: str | None = None,
        search_by: "SearchByParams | None" = None,
        order_by: "OrderByParams | None" = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> "list[BaseSQLAlchemyModel]":
        """Get list of instances of model_class."""
        return await self._list(
            filters=filters,
            joins=joins,
            loads=loads,
            search=search,
            search_by=search_by,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

    async def create(
        self,
        *,
        data: "DataDict | None",
    ) -> "BaseSQLAlchemyModel":
        """Create model_class instance from given data."""
        return await self._create(data=data)

    async def bulk_create(
        self,
        *,
        data: "Sequence[DataDict]",
    ) -> "list[BaseSQLAlchemyModel]":
        """Create sequence model_class of instances from given data."""
        return await self._bulk_create(data=data)

    async def update(
        self,
        *,
        data: "DataDict",
        filters: "Filters | None" = None,
    ) -> "list[BaseSQLAlchemyModel] | None":
        """Update model_class from given data."""
        return await self._update(data=data, filters=filters)

    async def update_instance(
        self,
        *,
        instance: "BaseSQLAlchemyModel",
        data: "DataDict",
    ) -> "tuple[bool, BaseSQLAlchemyModel]":
        """Update model_class instance from given data.

        Returns tuple with boolean (was instance updated or not) and updated instance.
        """
        return await self._update_instance(instance=instance, data=data)

    async def delete(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> int:
        """Delete model_class in db by given filters."""
        return await self._delete(filters=filters)

    async def disable(
        self,
        *,
        ids_to_disable: set[Any],
        extra_filters: "Filters | None" = None,
    ) -> int:
        """Disable model_class instances with given ids and extra_filters."""
        return await self._disable(ids_to_disable=ids_to_disable, extra_filters=extra_filters)


class SyncRepository(BaseSyncRepository[BaseSQLAlchemyModel], AbstractSyncRepository):
    """Sync repository class with implemented base methods."""

    __inheritance_check_model_class__ = False

    def get(
        self,
        *,
        filters: "Filters",
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
    ) -> "BaseSQLAlchemyModel | None":
        """Get one instance of model_class by given filters."""
        return self._get(filters=filters, joins=joins, loads=loads)

    def count(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
    ) -> int:
        """Get count of instances of model_class by given filters."""
        return self._count(filters=filters, joins=joins)

    def exists(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> bool:
        """Check rows in table for existing."""
        return self._exists(filters=filters)

    def list(
        self,
        *,
        filters: "Filters | None" = None,
        joins: "Joins | None" = None,
        loads: "Loads | None" = None,
        search: str | None = None,
        search_by: "SearchByParams | None" = None,
        order_by: "OrderByParams | None" = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> "list[BaseSQLAlchemyModel]":
        """Get list of instances of model_class."""
        return self._list(
            filters=filters,
            joins=joins,
            loads=loads,
            search=search,
            search_by=search_by,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

    def create(
        self,
        *,
        data: "DataDict | None",
    ) -> "BaseSQLAlchemyModel":
        """Create model_class instance from given data."""
        return self._create(data=data)

    def bulk_create(
        self,
        *,
        data: "Sequence[DataDict]",
    ) -> "list[BaseSQLAlchemyModel]":
        """Create sequence model_class of instances from given data."""
        return self._bulk_create(data=data)

    def update(
        self,
        *,
        data: "DataDict",
        filters: "Filters | None" = None,
    ) -> "list[BaseSQLAlchemyModel] | None":
        """Update model_class from given data."""
        return self._update(data=data, filters=filters)

    def update_instance(
        self,
        *,
        instance: "BaseSQLAlchemyModel",
        data: "DataDict",
    ) -> "tuple[bool, BaseSQLAlchemyModel]":
        """Update model_class instance from given data.

        Returns tuple with boolean (was instance updated or not) and updated instance.
        """
        return self._update_instance(instance=instance, data=data)

    def delete(
        self,
        *,
        filters: "Filters | None" = None,
    ) -> int:
        """Delete model_class in db by given filters."""
        return self._delete(filters=filters)

    def disable(
        self,
        *,
        ids_to_disable: set[Any],
        extra_filters: "Filters | None" = None,
    ) -> int:
        """Disable model_class instances with given ids and extra_filters."""
        return self._disable(ids_to_disable=ids_to_disable, extra_filters=extra_filters)
