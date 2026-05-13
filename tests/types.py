from typing import TYPE_CHECKING, Any, Protocol, TypeVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session


T_co = TypeVar("T_co", covariant=True)


class SyncFactoryFunctionProtocol(Protocol[T_co]):
    """Protocol for Sync functions-factories that create db items."""

    @staticmethod
    def __call__(
        session: "Session",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> T_co: ...


class AsyncFactoryFunctionProtocol(Protocol[T_co]):
    """Protocol for Sync functions-factories that create db items."""

    @staticmethod
    async def __call__(
        session: "AsyncSession",
        *,
        commit: bool = False,
        **kwargs: Any,
    ) -> T_co: ...
