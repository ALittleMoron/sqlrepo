from typing import TYPE_CHECKING

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from mimesis import Datetime, Text
from pydantic import TypeAdapter
from sqlalchemy.orm.session import Session

from sqlrepo.ext.fastapi import BaseSyncService
from sqlrepo.ext.fastapi.pagination import (
    PaginatedResult,
)
from sqlrepo.ext.fastapi.services import NotSet, ServiceClassIncorrectUseWarning
from tests.text_extensions.test_fastapi.infra import MyModelDetail, MyModelList
from tests.utils import MyModel, assert_compare_db_item_with_dict

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

    from tests.types import SyncFactoryFunctionProtocol


class TestFastAPIExtension:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        text_faker: Text,
        dt_faker: Datetime,
        db_sync_session: "Session",
        mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
        app_with_sync_container: "TestClient",
    ) -> None:
        self.text_faker = text_faker
        self.dt_faker = dt_faker
        self.db_sync_session = db_sync_session
        self.mymodel_sync_factory = mymodel_sync_factory
        self.app_with_sync_container = app_with_sync_container

    def test_get_one(self) -> None:
        item = self.mymodel_sync_factory(self.db_sync_session, commit=True)
        assert item is not None, f"MyModel with id {item.id} not found in db."
        response = self.app_with_sync_container.get(f'/get-one/{item.id}')
        assert response.status_code == status.HTTP_200_OK
        response = response.json()
        schema = MyModelDetail.model_validate(response)
        assert item.id == schema.id

    def test_get_one_not_found(self) -> None:
        response = self.app_with_sync_container.get('/get-one/1251251')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = response.json()
        assert "detail" in response
        assert response['detail'] == "MyModel entity not found."

    def test_get_one_instance_not_found(self) -> None:
        response = self.app_with_sync_container.get('/get-one-instance/1251251')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = response.json()
        assert "detail" in response
        assert response['detail'] == "error 1"

    def test_get_one_verbose_not_found(self) -> None:
        response = self.app_with_sync_container.get('/get-one-verbose/1251251')
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response = response.json()
        for key in ("message", 'location', "attr", "code", "type"):
            assert key in response
        assert response['message'] == "MyModel entity instance not found."

    def test_get_one_python_not_found(self) -> None:
        with pytest.raises(ValueError, match="MyModel entity not found."):
            self.app_with_sync_container.get('/get-one-python/1251251')

    def test_limit_offset_pagination(self) -> None:
        items = [self.mymodel_sync_factory(self.db_sync_session, commit=False) for _ in range(3)]
        items_map = {item.id: item for item in items}
        self.db_sync_session.commit()
        response = self.app_with_sync_container.get('/get-limit-offset-paginated/?limit=1')
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

    def test_page_size_pagination(self) -> None:
        items = [self.mymodel_sync_factory(self.db_sync_session, commit=False) for _ in range(3)]
        items_map = {item.id: item for item in items}
        self.db_sync_session.commit()
        response = self.app_with_sync_container.get('/get-page-size-paginated/?per_page=1')
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

    def test_get_all(self) -> None:
        ids = {
            self.mymodel_sync_factory(self.db_sync_session).id,
            self.mymodel_sync_factory(self.db_sync_session).id,
        }
        self.db_sync_session.commit()
        response = self.app_with_sync_container.get('/get-all/')
        assert response.status_code == status.HTTP_200_OK
        response = response.json()
        schema = TypeAdapter(list[MyModelList]).validate_python(response)
        assert len(schema) == len(ids)
        for item in schema:
            assert item.id in ids

    def test_invalid_methods(self) -> None:
        with pytest.raises(AttributeError):
            self.app_with_sync_container.get('/get-one-invalid/1251251/')
        item = self.mymodel_sync_factory(self.db_sync_session, commit=True)
        assert item is not None, f"MyModel with id {item.id} not found in db."
        with pytest.raises(AttributeError):
            self.app_with_sync_container.get(f'/get-one-invalid/{item.id}')
        with pytest.raises(AttributeError):
            self.app_with_sync_container.get('/get-all-invalid/')

    def test_inherit_skip(self) -> None:
        assert BaseSyncService.__inheritance_check_model_class__ is True

        class MyService(BaseSyncService):
            __inheritance_check_model_class__ = False

        assert MyService.__inheritance_check_model_class__ is True

    def test_already_set_schemas(self) -> None:
        class MyService(BaseSyncService[MyModel, MyModelDetail, MyModelList]):
            detail_schema = MyModelDetail
            list_schema = MyModelList

    def test_cant_eval_forward_ref(self) -> None:
        with pytest.warns(ServiceClassIncorrectUseWarning):

            class MyTestService(BaseSyncService["OtherModel", "OtherDetail", "OtherList"]): ...  # type: ignore[reportUndefinedVariable]

    def test_can_eval_forward_ref(self) -> None:
        class MyTestService(BaseSyncService["MyModel", "MyModelDetail", "MyModelList"]): ...

        assert MyTestService.detail_schema is not NotSet
        assert MyTestService.list_schema is not NotSet

    def test_generic_incorrect_type(self) -> None:
        with pytest.warns(
            ServiceClassIncorrectUseWarning,
            match="Passed GenericType is not pydantic BaseModel subclass.",
        ):

            class MyService(BaseSyncService[int, int, int]): ...  # type: ignore[reportInvalidTypeArguments]

    def test_no_generic(self) -> None:
        with pytest.warns(
            ServiceClassIncorrectUseWarning,
            match="GenericType was not passed for pydantic BaseModel subclass.",
        ):

            class MyService(BaseSyncService): ...
