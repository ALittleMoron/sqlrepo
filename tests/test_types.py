from typing import TYPE_CHECKING, TypeVar

import pytest

from sqlrepo import constants as c
from sqlrepo.repositories import BaseRepository, RepositoryModelClassIncorrectUseWarning
from tests.utils import MyModel

if TYPE_CHECKING:
    from tests.utils import OtherModel  # noqa: F401

T = TypeVar("T")


def test_extract_model_from_generic_already_set_model_class_warn() -> None:
    with pytest.warns(RepositoryModelClassIncorrectUseWarning):

        class MyRepo(BaseRepository[MyModel]):
            model_class = MyModel


def test_extract_model_from_generic_cant_eval_forward_ref() -> None:
    with pytest.warns(RepositoryModelClassIncorrectUseWarning):

        class MyRepo(BaseRepository["OtherModel"]): ...


def test_extract_model_from_generic_eval_forward_ref() -> None:
    class MyRepo(BaseRepository["MyModel"]): ...

    assert MyRepo.model_class == MyModel


def test_extract_model_from_generic_generic_incorrect_type() -> None:
    with pytest.warns(
        RepositoryModelClassIncorrectUseWarning,
        match=c.REPOSITORY_GENERIC_TYPE_IS_NOT_MODEL,
    ):

        class MyRepo(BaseRepository[int]): ...  # type: ignore[reportInvalidTypeArguments]


def test_extract_model_from_generic_no_generic() -> None:
    with pytest.warns(
        RepositoryModelClassIncorrectUseWarning,
        match=c.REPOSITORY_GENERIC_TYPE_NOT_PASSED_WARNING,
    ):

        class MyRepo(BaseRepository): ...


def test_extract_model_from_generic_type_var() -> None:
    with pytest.warns(
        RepositoryModelClassIncorrectUseWarning,
        match=c.REPOSITORY_GENERIC_TYPE_TYPE_VAR_PASSED_WARNING,
    ):

        class MyRepo(BaseRepository[T]): ...  # type: ignore[reportInvalidTypeArguments]


def test_extract_model_from_generic_generic_not_class() -> None:
    with pytest.warns(
        RepositoryModelClassIncorrectUseWarning,
        match=c.REPOSITORY_GENERIC_TYPE_IS_NOT_CLASS_WARNING,
    ):

        class MyRepo(BaseRepository['25']): ...  # type: ignore[reportInvalidTypeArguments]


def test_extract_model_from_generic_correct_use() -> None:
    class CorrectRepo(BaseRepository[MyModel]): ...

    assert CorrectRepo.model_class == MyModel


def test_extract_model_from_generic_right_multiple_inheritance_correct_use() -> None:
    class CorrectRepo(int, BaseRepository[MyModel]): ...

    assert CorrectRepo.model_class == MyModel


def test_extract_model_from_generic_left_multiple_inheritance_correct_use() -> None:
    class CorrectRepo(BaseRepository[MyModel], int): ...

    assert CorrectRepo.model_class == MyModel


def test_extract_model_from_generic_unsafe_generic() -> None:
    with pytest.raises(SyntaxError):

        class MyRepo(BaseRepository['import sys; sys.exit(255)']): ...  # type: ignore  # noqa: PGH003
