from typing import TYPE_CHECKING, Any, Literal

import pytest
from sqlalchemy_filter_converter import (
    AdvancedFilterConverter,
    DjangoLikeFilterConverter,
    SimpleFilterConverter,
)

from sqlrepo.config import RepositoryConfig
from sqlrepo.exc import RepositoryAttributeError
from sqlrepo.repositories import BaseRepository
from tests.utils import MyModel

if TYPE_CHECKING:
    from tests.utils import OtherModel  # noqa: F401


def test_inherit_skip() -> None:
    assert BaseRepository.__inheritance_check_model_class__ is True

    class MyRepo(BaseRepository):
        __inheritance_check_model_class__ = False

    assert MyRepo.__inheritance_check_model_class__ is True


def test_validate_disable_attributes() -> None:
    class CorrectRepo(BaseRepository[MyModel]):
        config = RepositoryConfig(
            disable_id_field="id",
            disable_field="bl",
            disable_field_type=bool,
        )

    CorrectRepo._validate_disable_attributes()


def test_validate_disable_attributes_raise_error() -> None:
    class CorrectRepo(BaseRepository[MyModel]): ...

    with pytest.raises(RepositoryAttributeError):
        CorrectRepo._validate_disable_attributes()


@pytest.mark.parametrize(
    ("strategy", "expected_class"),
    [
        ("simple", SimpleFilterConverter),
        ("advanced", AdvancedFilterConverter),
        ("django", DjangoLikeFilterConverter),
    ],
)
def test_get_filter_convert_class(
    strategy: Literal["simple", "advanced", "django"],
    expected_class: Any,
) -> None:  # noqa: ANN401
    class CorrectRepo(BaseRepository[MyModel]):
        config = RepositoryConfig(filter_convert_strategy=strategy)

    assert isinstance(CorrectRepo.config.get_filter_convert(), expected_class)
