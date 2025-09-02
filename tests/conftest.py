import asyncio
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from mimesis import Datetime, Locale, Text
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy_utils import database_exists, create_database

from tests.utils import (
    Base,
    MyModel,
    OtherModel,
    coin_flip,
    create_db_item_async,
    create_db_item_sync,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from sqlalchemy import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
    from sqlalchemy.orm import Session

    from tests.types import AsyncFactoryFunctionProtocol, SyncFactoryFunctionProtocol


@pytest.fixture(scope="session")
def db_domain() -> str:
    return "postgres:postgres@localhost:5432/test_sqlrepo_db"


@pytest.fixture(scope="session")
def db_sync_url(db_domain: str) -> str:
    return f"postgresql://{db_domain}"


@pytest.fixture(scope="session")
def db_async_url(db_domain: str) -> str:
    return f"postgresql+asyncpg://{db_domain}"


@pytest.fixture(scope="session")
def postgresql_url_with_template_db(db_domain_with_template_db: str) -> str:
    return f"postgresql://{db_domain_with_template_db}"


@pytest.fixture
def db_sync_engine(db_sync_url: str) -> "Generator[Engine, None, None]":
    if not database_exists(db_sync_url):
        create_database(db_sync_url)
    engine = create_engine(db_sync_url, echo=False, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest_asyncio.fixture()
async def db_async_engine(
    db_async_url: str,
    db_sync_engine: "Engine",  # noqa: ARG001
) -> "AsyncGenerator[AsyncEngine, None]":
    engine = create_async_engine(db_async_url, echo=True, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def db_sync_session_factory(db_sync_engine: "Engine") -> "scoped_session[Session]":
    return scoped_session(
        sessionmaker(bind=db_sync_engine, autoflush=False, expire_on_commit=False),
    )


@pytest.fixture
def db_async_session_factory(
    db_async_engine: "AsyncEngine",
) -> "async_scoped_session[AsyncSession]":
    return async_scoped_session(
        async_sessionmaker(bind=db_async_engine, autoflush=False, expire_on_commit=False),
        asyncio.current_task,
    )


@pytest.fixture
def db_sync_session(
    db_sync_engine: "Engine",
    db_sync_session_factory: "scoped_session[Session]",
) -> "Generator[Session, None, None]":
    Base.metadata.create_all(db_sync_engine)
    with db_sync_session_factory() as session:
        yield session
    Base.metadata.drop_all(db_sync_engine)


@pytest_asyncio.fixture()
async def db_async_session(
    db_async_engine: "AsyncEngine",
    db_async_session_factory: "async_scoped_session[AsyncSession]",
) -> "AsyncGenerator[AsyncSession, None]":
    async with db_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with db_async_session_factory() as session:
        yield session


@pytest.fixture
def mymodel_sync_factory(
    dt_faker: Datetime,
    text_faker: Text,
) -> "SyncFactoryFunctionProtocol[MyModel]":

    def _create(
        session: "Session",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> MyModel:
        params: dict[str, Any] = {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "dt": dt_faker.datetime(),
            "bl": coin_flip(),
        }
        params.update(kwargs)
        return create_db_item_sync(session, MyModel, params, commit=commit)

    return _create


@pytest.fixture
def othermodel_sync_factory(
    text_faker: Text,
    mymodel_sync_factory: "SyncFactoryFunctionProtocol[MyModel]",
) -> "SyncFactoryFunctionProtocol[OtherModel]":

    def _create(
        session: "Session",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> OtherModel:
        if "model_id" not in kwargs:
            model_id = mymodel_sync_factory(session, commit=commit).id
        else:
            model_id = kwargs.pop("model_id")
        params: dict[str, Any] = {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "model_id": model_id,
        }
        params.update(kwargs)
        return create_db_item_sync(session, OtherModel, params, commit=commit)

    return _create


@pytest.fixture
def mymodel_async_factory(
    text_faker: Text,
    dt_faker: Datetime,
) -> "AsyncFactoryFunctionProtocol[MyModel]":

    async def _create(
        session: "AsyncSession",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> MyModel:
        params: dict[str, Any] = {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "dt": dt_faker.datetime(),
            "bl": coin_flip(),
        }
        params.update(kwargs)
        return await create_db_item_async(session, MyModel, params, commit=commit)

    return _create


@pytest.fixture
def othermodel_async_factory(
    text_faker: Text,
    mymodel_async_factory: "AsyncFactoryFunctionProtocol[MyModel]",
) -> "AsyncFactoryFunctionProtocol[OtherModel]":

    async def _create(
        session: "AsyncSession",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> OtherModel:
        if "model_id" not in kwargs:
            model = await mymodel_async_factory(session, commit=commit)
            model_id = model.id
        else:
            model_id = kwargs.pop("model_id")
        params: dict[str, Any] = {
            "name": text_faker.sentence(),
            "other_name": text_faker.sentence(),
            "model_id": model_id,
        }
        params.update(kwargs)
        return await create_db_item_async(session, OtherModel, params, commit=commit)

    return _create


@pytest.fixture
def text_faker() -> Text:
    return Text(locale=Locale.EN)


@pytest.fixture
def dt_faker() -> Datetime:
    return Datetime(locale=Locale.EN)
