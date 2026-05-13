from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_dev_utils.exc import BaseSQLAlchemyDevError
from sqlalchemy_filter_converter.exc import FilterError

from sqlrepo.exc import BaseSQLRepoError, QueryError

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def wrap_any_exception_manager() -> "Generator[None, None, Any]":
    """Context manager wrapper to prevent sqlalchemy or any other exceptions to be thrown."""
    try:
        yield
    except BaseSQLAlchemyDevError as exc:
        msg = "error on sqlalchemy-dev-utils package level."
        raise QueryError(msg) from exc
    except SQLAlchemyError as exc:
        msg = "error on SQLAlchemy level."
        raise QueryError(msg) from exc
    except FilterError as exc:
        msg = "error on sqlalchemy-filter-converter package level."
        raise QueryError(msg) from exc
    except (AttributeError, TypeError, ValueError) as exc:
        msg = "error on python level."
        raise BaseSQLRepoError(msg) from exc
