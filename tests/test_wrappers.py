import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_dev_utils.exc import BaseSQLAlchemyDevError
from sqlalchemy_filter_converter.exc import FilterError

from sqlrepo.exc import BaseSQLRepoError, QueryError
from sqlrepo.wrappers import wrap_any_exception_manager


@pytest.mark.parametrize(
    ("wrap_error", "output_error"),
    [
        (FilterError, QueryError),
        (BaseSQLAlchemyDevError, QueryError),
        (SQLAlchemyError, QueryError),
        (AttributeError, BaseSQLRepoError),
        (TypeError, BaseSQLRepoError),
        (ValueError, BaseSQLRepoError),
    ],
)
def test_wrap_work(wrap_error: type[Exception], output_error: type[Exception]) -> None:
    error_message = "some error message."
    with pytest.raises(output_error), wrap_any_exception_manager():
        raise wrap_error(error_message)
