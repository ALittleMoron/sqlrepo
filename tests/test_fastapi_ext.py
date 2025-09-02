import datetime
from functools import cached_property
from typing import TYPE_CHECKING

import pytest
from fastapi import Depends, FastAPI, HTTPException, Path, status
from fastapi.testclient import TestClient
from mimesis import Datetime, Locale, Text
from pydantic import BaseModel, ConfigDict, TypeAdapter
from sqlalchemy.orm.session import Session
from verbose_http_exceptions.exc import BaseVerboseHTTPException
from verbose_http_exceptions.ext.fastapi import apply_verbose_http_exception_handler

from sqlrepo.ext.fastapi import BaseSyncContainer, BaseSyncService, add_session_stub_overrides
from sqlrepo.ext.fastapi.pagination import (
    AbstractBasePagination,
    LimitOffsetPagination,
    PageSizePagination,
    PaginatedResult,
    PaginationMeta,
)
from sqlrepo.ext.fastapi.services import NotSet, ServiceClassIncorrectUseWarning
from sqlrepo.repositories import BaseSyncRepository
from tests.utils import MyModel, assert_compare_db_item_with_dict

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session, sessionmaker

    from tests.types import SyncFactoryFunctionProtocol


text_faker = Text(locale=Locale.EN)
dt_faker = Datetime(locale=Locale.EN)


class MyModelNotFoundVerboseException(BaseVerboseHTTPException):  # noqa: D101
    status_code = status.HTTP_404_NOT_FOUND
    code = "client_error"
    type_ = "not_found"
    message = "MyModel entity instance not found."


class MyModelRepository(BaseSyncRepository[MyModel]):  # noqa: D101
    ...


class MyModelDetail(BaseModel):  # noqa: D101
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    other_name: str | None = None
    dt: datetime.datetime | None = None
    bl: bool | None = None


class MyModelList(BaseModel):  # noqa: D101
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None


class MyModelService(BaseSyncService[MyModel, MyModelDetail, MyModelList]):  # noqa: D101
    not_found_message = "MyModel entity not found."
    not_found_exception = HTTPException

    def init_repositories(self, session: "Session") -> None:  # noqa: D102
        self.my_model_repo = MyModelRepository(session)

    def get_by_id(self, my_model_id: int) -> MyModelDetail:  # noqa: D102
        entity = self.my_model_repo._get(filters={"id": my_model_id})
        return self.resolve_entity(entity)

    def list(self) -> list[MyModelList]:  # noqa: D102
        entities = self.my_model_repo._list()
        return self.resolve_entity_list(entities)

    def list_paginated(  # noqa: D102
        self,
        pagination: AbstractBasePagination,
    ) -> PaginatedResult[MyModelList]:
        entities = self.my_model_repo._list(limit=pagination.limit, offset=pagination.offset)
        total_count = self.my_model_repo._count()
        meta = PaginationMeta.create(
            all_records_count=total_count,
            pagination=pagination,
        )
        return self.paginate_result(entities, meta)


class InvalidService(MyModelService):  # noqa: D101
    ...


InvalidService.detail_schema = NotSet
InvalidService.list_schema = NotSet
InvalidService.not_found_message = NotSet
InvalidService.not_found_exception = NotSet


class MyModelServiceWithErrorInstance(MyModelService):  # noqa: D101
    not_found_exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="error 1")


class MyModelServiceWithVerboseExceptions(MyModelService):  # noqa: D101
    not_found_exception = MyModelNotFoundVerboseException


class MyModelServiceWithPythonError(MyModelService):  # noqa: D101
    not_found_exception = ValueError


class Container(BaseSyncContainer):  # noqa: D101
    @cached_property
    def invalid_service(self) -> InvalidService:  # noqa: D102
        return InvalidService(self.request, self.session)

    @cached_property
    def my_model_service(self) -> MyModelService:  # noqa: D102
        return MyModelService(self.request, self.session)

    @cached_property
    def my_model_service_with_error_instance(self) -> MyModelServiceWithErrorInstance:  # noqa: D102
        return MyModelServiceWithErrorInstance(self.request, self.session)

    @cached_property
    def my_model_service_with_verbose_exceptions(  # noqa: D102
        self,
    ) -> MyModelServiceWithVerboseExceptions:  # noqa: D102
        return MyModelServiceWithVerboseExceptions(self.request, self.session)

    @cached_property
    def my_model_with_python_error(self) -> MyModelServiceWithPythonError:  # noqa: D102
        return MyModelServiceWithPythonError(self.request, self.session)


@pytest.fixture()
def get_sync_session_depends(  # noqa: ANN201
    db_sync_session_factory: "sessionmaker[Session]",
):
    def get_session():  # noqa: ANN202
        with db_sync_session_factory() as session:
            yield session

    return get_session


@pytest.fixture()
def app_with_sync_container(get_sync_session_depends: "Callable[..., Session]") -> "TestClient":
    app = FastAPI()
    add_session_stub_overrides(app, get_sync_session_depends)
    apply_verbose_http_exception_handler(app)

    @app.get('/get-one-invalid/{my_model_id}')
    def get_one_invalid(
        my_model_id: int = Path(), container: Container = Depends()
    ):  # noqa: ANN202
        return container.invalid_service.get_by_id(my_model_id)

    @app.get('/get-one/{my_model_id}')
    def get_one(my_model_id: int = Path(), container: Container = Depends()):  # noqa: ANN202
        return container.my_model_service.get_by_id(my_model_id)

    @app.get('/get-one-instance/{my_model_id}')
    def get_one_instance(
        my_model_id: int = Path(), container: Container = Depends()
    ):  # noqa: ANN202
        return container.my_model_service_with_error_instance.get_by_id(my_model_id)

    @app.get('/get-one-verbose/{my_model_id}')
    def get_one_verbose(
        my_model_id: int = Path(), container: Container = Depends()
    ):  # noqa: ANN202
        return container.my_model_service_with_verbose_exceptions.get_by_id(my_model_id)

    @app.get('/get-one-python/{my_model_id}')
    def get_one_python(my_model_id: int = Path(), container: Container = Depends()):  # noqa: ANN202
        return container.my_model_with_python_error.get_by_id(my_model_id)

    @app.get('/get-all/')
    def get_all(container: Container = Depends()):  # noqa: ANN202
        return container.my_model_service.list()

    @app.get('/get-limit-offset-paginated/')
    def get_paginated_limit_offset(  # noqa: ANN202
        pagination: LimitOffsetPagination = Depends(),
        container: Container = Depends(),
    ):
        return container.my_model_service.list_paginated(pagination)

    @app.get('/get-page-size-paginated/')
    def get_paginated_page_size(  # noqa: ANN202
        pagination: PageSizePagination = Depends(),
        container: Container = Depends(),
    ):
        return container.my_model_service.list_paginated(pagination)

    @app.get('/get-all-invalid/')
    def get_all_invalid(container: Container = Depends()):  # noqa: ANN202
        return container.invalid_service.list()

    return TestClient(app)


def test_get_one(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    app_with_sync_container: "TestClient",
) -> None:
    item = mymodel_sync_factory(db_sync_session, commit=True)
    assert item is not None, f"MyModel with id {item.id} not found in db."
    response = app_with_sync_container.get(f'/get-one/{item.id}')
    assert response.status_code == status.HTTP_200_OK
    response = response.json()
    schema = MyModelDetail.model_validate(response)
    assert item.id == schema.id


def test_get_one_not_found(
    db_sync_session: "Session",
    app_with_sync_container: "TestClient",
) -> None:
    response = app_with_sync_container.get('/get-one/1251251')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = response.json()
    assert "detail" in response
    assert response['detail'] == "MyModel entity not found."


def test_get_one_instance_not_found(
    db_sync_session: "Session",
    app_with_sync_container: "TestClient",
) -> None:
    response = app_with_sync_container.get('/get-one-instance/1251251')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = response.json()
    assert "detail" in response
    assert response['detail'] == "error 1"


def test_get_one_verbose_not_found(
    db_sync_session: "Session",
    app_with_sync_container: "TestClient",
) -> None:
    response = app_with_sync_container.get('/get-one-verbose/1251251')
    assert response.status_code == status.HTTP_404_NOT_FOUND
    response = response.json()
    for key in {"message", 'location', "attr", "code", "type"}:
        assert key in response
    assert response['message'] == "MyModel entity instance not found."


def test_get_one_python_not_found(
    db_sync_session: "Session",
    app_with_sync_container: "TestClient",
) -> None:
    with pytest.raises(ValueError, match="MyModel entity not found."):
        app_with_sync_container.get('/get-one-python/1251251')


def test_limit_offset_pagination(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    app_with_sync_container: "TestClient",
) -> None:

    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    items_map = {item.id: item for item in items}
    db_sync_session.commit()
    response = app_with_sync_container.get('/get-limit-offset-paginated/?limit=1')
    assert response.status_code == status.HTTP_200_OK
    response = response.json()
    schema = TypeAdapter(PaginatedResult[MyModelList]).validate_python(response)
    assert schema.meta.all_pages_count == len(items)
    assert schema.meta.filtered_pages_count == len(items)
    assert schema.meta.all_records_count == len(items)
    assert schema.meta.filtered_records_count == len(items)
    assert schema.meta.per_page == 1
    assert schema.meta.current_page == 1
    assert schema.meta.prev_page is None
    assert schema.meta.next_page == 2  # noqa: PLR2004
    for item in schema.data:
        assert item.id in items_map
        assert_compare_db_item_with_dict(items_map[item.id], item.model_dump())


def test_page_size_pagination(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    app_with_sync_container: "TestClient",
) -> None:

    items = [mymodel_sync_factory(db_sync_session, commit=False) for _ in range(3)]
    items_map = {item.id: item for item in items}
    db_sync_session.commit()
    response = app_with_sync_container.get('/get-page-size-paginated/?per_page=1')
    assert response.status_code == status.HTTP_200_OK
    response = response.json()
    schema = TypeAdapter(PaginatedResult[MyModelList]).validate_python(response)
    assert schema.meta.all_pages_count == len(items)
    assert schema.meta.filtered_pages_count == len(items)
    assert schema.meta.all_records_count == len(items)
    assert schema.meta.filtered_records_count == len(items)
    assert schema.meta.per_page == 1
    assert schema.meta.current_page == 1
    assert schema.meta.prev_page is None
    assert schema.meta.next_page == 2  # noqa: PLR2004
    for item in schema.data:
        assert item.id in items_map
        assert_compare_db_item_with_dict(items_map[item.id], item.model_dump())


def test_get_all(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    app_with_sync_container: "TestClient",
) -> None:
    ids = {mymodel_sync_factory(db_sync_session).id, mymodel_sync_factory(db_sync_session).id}
    db_sync_session.commit()
    response = app_with_sync_container.get('/get-all/')
    assert response.status_code == status.HTTP_200_OK
    response = response.json()
    schema = TypeAdapter(list[MyModelList]).validate_python(response)
    assert len(schema) == len(ids)
    for item in schema:
        assert item.id in ids


def test_invalid_methods(
    db_sync_session: "Session",
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
    app_with_sync_container: "TestClient",
) -> None:
    with pytest.raises(AttributeError):
        app_with_sync_container.get('/get-one-invalid/1251251/')
    item = mymodel_sync_factory(db_sync_session, commit=True)
    assert item is not None, f"MyModel with id {item.id} not found in db."
    with pytest.raises(AttributeError):
        app_with_sync_container.get(f'/get-one-invalid/{item.id}')
    with pytest.raises(AttributeError):
        app_with_sync_container.get('/get-all-invalid/')


def test_inherit_skip() -> None:
    assert BaseSyncService.__inheritance_check_model_class__ is True

    class MyService(BaseSyncService):
        __inheritance_check_model_class__ = False

    assert MyService.__inheritance_check_model_class__ is True


def test_already_set_schemas() -> None:
    class MyService(BaseSyncService[MyModel, MyModelDetail, MyModelList]):
        detail_schema = MyModelDetail
        list_schema = MyModelList


def test_cant_eval_forward_ref() -> None:
    with pytest.warns(ServiceClassIncorrectUseWarning):

        class MyTestService(BaseSyncService["OtherModel", "OtherDetail", "OtherList"]): ...  # type: ignore


def test_can_eval_forward_ref() -> None:
    class MyTestService(BaseSyncService["MyModel", "MyModelDetail", "MyModelList"]): ...

    assert MyTestService.detail_schema is not NotSet
    assert MyTestService.list_schema is not NotSet


def test_generic_incorrect_type() -> None:
    with pytest.warns(
        ServiceClassIncorrectUseWarning,
        match="Passed GenericType is not pydantic BaseModel subclass.",
    ):

        class MyService(BaseSyncService[int, int, int]): ...  # type: ignore


def test_no_generic() -> None:
    with pytest.warns(
        ServiceClassIncorrectUseWarning,
        match="GenericType was not passed for pydantic BaseModel subclass.",
    ):

        class MyService(BaseSyncService): ...
