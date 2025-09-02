import datetime
from functools import cached_property
from typing import TYPE_CHECKING

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from starlette import status
from verbose_http_exceptions.exc import BaseVerboseHTTPException

from sqlrepo import BaseSyncRepository
from sqlrepo.ext.fastapi import BaseSyncContainer, BaseSyncService
from sqlrepo.ext.fastapi.helpers import NotSet
from sqlrepo.ext.fastapi.pagination import AbstractBasePagination, PaginatedResult, PaginationMeta
from tests.utils import MyModel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class MyModelDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    other_name: str | None = None
    dt: datetime.datetime | None = None
    bl: bool | None = None


class MyModelList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None


class MyModelService(BaseSyncService[MyModel, MyModelDetail, MyModelList]):
    not_found_message = "MyModel entity not found."
    not_found_exception = HTTPException

    def init_repositories(self, session: "Session") -> None:
        self.my_model_repo = MyModelRepository(session)

    def get_by_id(self, my_model_id: int) -> MyModelDetail:
        entity = self.my_model_repo._get(filters={"id": my_model_id})
        return self.resolve_entity(entity)

    def list(self) -> list[MyModelList]:
        entities = self.my_model_repo._list()
        return self.resolve_entity_list(entities)

    def list_paginated(
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


class InvalidService(MyModelService): ...


InvalidService.detail_schema = NotSet
InvalidService.list_schema = NotSet
InvalidService.not_found_message = NotSet
InvalidService.not_found_exception = NotSet


class MyModelNotFoundVerboseException(BaseVerboseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "client_error"
    type_ = "not_found"
    message = "MyModel entity instance not found."


class MyModelServiceWithErrorInstance(MyModelService):
    not_found_exception = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="error 1")


class MyModelServiceWithVerboseExceptions(MyModelService):
    not_found_exception = MyModelNotFoundVerboseException


class MyModelServiceWithPythonError(MyModelService):
    not_found_exception = ValueError


class Container(BaseSyncContainer):
    @cached_property
    def invalid_service(self) -> InvalidService:
        return InvalidService(self.request, self.session)

    @cached_property
    def my_model_service(self) -> MyModelService:
        return MyModelService(self.request, self.session)

    @cached_property
    def my_model_service_with_error_instance(self) -> MyModelServiceWithErrorInstance:
        return MyModelServiceWithErrorInstance(self.request, self.session)

    @cached_property
    def my_model_service_with_verbose_exceptions(
        self,
    ) -> MyModelServiceWithVerboseExceptions:
        return MyModelServiceWithVerboseExceptions(self.request, self.session)

    @cached_property
    def my_model_with_python_error(self) -> MyModelServiceWithPythonError:
        return MyModelServiceWithPythonError(self.request, self.session)


class MyModelRepository(BaseSyncRepository[MyModel]): ...
