from typing import TYPE_CHECKING

import pytest
from fastapi import Depends, FastAPI, Path
from fastapi.testclient import TestClient
from verbose_http_exceptions.ext.fastapi import apply_verbose_http_exception_handler

from sqlrepo.ext.fastapi import add_session_stub_overrides
from sqlrepo.ext.fastapi.pagination import (
    LimitOffsetPagination,
    PageSizePagination,
)
from tests.text_extensions.test_fastapi.infra import Container

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def get_sync_session_depends(
    db_sync_session_factory: "sessionmaker[Session]",
):
    def get_session():
        with db_sync_session_factory() as session:
            yield session

    return get_session


@pytest.fixture
def app_with_sync_container(get_sync_session_depends: "Callable[..., Session]") -> "TestClient":
    app = FastAPI()
    add_session_stub_overrides(app, get_sync_session_depends)
    apply_verbose_http_exception_handler(app)

    @app.get('/get-one-invalid/{my_model_id}')
    def get_one_invalid(my_model_id: int = Path(), container: Container = Depends()):
        return container.invalid_service.get_by_id(my_model_id)

    @app.get('/get-one/{my_model_id}')
    def get_one(my_model_id: int = Path(), container: Container = Depends()):
        return container.my_model_service.get_by_id(my_model_id)

    @app.get('/get-one-instance/{my_model_id}')
    def get_one_instance(my_model_id: int = Path(), container: Container = Depends()):
        return container.my_model_service_with_error_instance.get_by_id(my_model_id)

    @app.get('/get-one-verbose/{my_model_id}')
    def get_one_verbose(my_model_id: int = Path(), container: Container = Depends()):
        return container.my_model_service_with_verbose_exceptions.get_by_id(my_model_id)

    @app.get('/get-one-python/{my_model_id}')
    def get_one_python(my_model_id: int = Path(), container: Container = Depends()):
        return container.my_model_with_python_error.get_by_id(my_model_id)

    @app.get('/get-all/')
    def get_all(container: Container = Depends()):
        return container.my_model_service.list()

    @app.get('/get-limit-offset-paginated/')
    def get_paginated_limit_offset(
        pagination: LimitOffsetPagination = Depends(),
        container: Container = Depends(),
    ):
        return container.my_model_service.list_paginated(pagination)

    @app.get('/get-page-size-paginated/')
    def get_paginated_page_size(
        pagination: PageSizePagination = Depends(),
        container: Container = Depends(),
    ):
        return container.my_model_service.list_paginated(pagination)

    @app.get('/get-all-invalid/')
    def get_all_invalid(container: Container = Depends()):
        return container.invalid_service.list()

    return TestClient(app)
