from typing import TYPE_CHECKING, Any, NotRequired, Protocol, TypeAlias, TypedDict, TypeVar

from sqlalchemy.orm.decl_api import DeclarativeBase as Base

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.orm.attributes import InstrumentedAttribute, QueryableAttribute
    from sqlalchemy.orm.strategy_options import _AbstractLoad  # type: ignore[reportPrivateUsage]
    from sqlalchemy.sql._typing import (
        _ColumnExpressionOrStrLabelArgument,  # type: ignore[reportPrivateUsage]
    )


class LoggerProtocol(Protocol):
    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def warn(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def critical(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...
    def fatal(self, msg: Any, *args: Any, **kwargs: Any) -> None: ...


class JoinKwargs(TypedDict):
    """Kwargs for SQLAlchemy join."""

    isouter: NotRequired[bool]
    full: NotRequired[bool]


BaseSQLAlchemyModel = TypeVar("BaseSQLAlchemyModel", bound=Base)

Count: TypeAlias = int
Deleted: TypeAlias = bool
IsUpdated: TypeAlias = bool
StrField: TypeAlias = str

DictStrAny: TypeAlias = "dict[str, Any]"
DataDict: TypeAlias = "DictStrAny"
SpecificColumnMapping: TypeAlias = "dict[str, QueryableAttribute[Any]]"

Filter: TypeAlias = "dict[str, Any] | ColumnElement[bool]"
Filters: TypeAlias = "Filter | tuple[Filter, ...] | list[Filter]"

Model: TypeAlias = "type[Base]"
JoinClause: TypeAlias = "ColumnElement[bool]"
JoinClauseWithModel: TypeAlias = "tuple[Model, JoinClause]"
CompleteJoinClause: TypeAlias = "tuple[Model, JoinClause, JoinKwargs]"
SimpleJoin: TypeAlias = "str | Model"
ComplexJoin: TypeAlias = "JoinClauseWithModel | CompleteJoinClause"
Joins: TypeAlias = "SimpleJoin | tuple[ComplexJoin, ...] | list[ComplexJoin]"

DisableField: TypeAlias = "InstrumentedAttribute[Any] | StrField"
DisableIdField: TypeAlias = "DisableField"

Load: TypeAlias = "_AbstractLoad"
Loads: TypeAlias = "Load | tuple[Load, ...] | list[Load]"

OrderByParam: TypeAlias = "_ColumnExpressionOrStrLabelArgument[Any]"
OrderByParams: TypeAlias = "OrderByParam | tuple[OrderByParam, ...] | list[OrderByParam]"

SearchByParam: TypeAlias = "str | QueryableAttribute[Any]"
SearchByParams: TypeAlias = "SearchByParam | tuple[SearchByParam, ...] | list[SearchByParam]"
