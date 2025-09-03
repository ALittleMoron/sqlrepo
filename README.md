# sqlrepo

![coverage](./coverage.svg)

> Repository pattern implementation for SQLAlchemy models.

## About repository pattern

Actually, I know, that my implementation is not good as repository pattern. I know, that
repository must has abstract interface, which must be implemented for different backends. I have
plans to make sqlrepo part of repository-pattern package, which will implements all possible
backends.

## Current state

Now, some features of repository pattern works incorrect or some parts of it is hard to understand
or use. I want to simplify work with repositories, so this is TODO for my project:

* [ ] Add more backends for repository pattern. Now, only SQLAlchemy adapter implemented. I want
      to implement other backends to make this repository better to use in different situations.
      NOTE: in future sqlrepo will be replaced with something like python-repository-pattern.
* [x] Add wrapper for all non sqlrepo exceptions. Now, some functionality could raise
      "raw" SQLAlchemy error. I want to avoid the situation, when developer make
      try-except with all possible exceptions, when works with my package.
      NOTE: added since 1.4.0
* [ ] Add more use-cases of `specific_column_mapping` option. Now it only works with
      `search_by` and `order_by` params. I want to add it for filters, joins and other
      parts, where it can be used.
* [x] Integrate sqlrepo with FastAPI or some other web-frameworks.
      NOTE 1: added since 1.5.0. Continued until 2.0.0. I currently not aimed to work on FastAPI.
      NOTE 2: removed since 6.0.0. Bad integration. 
* [x] Add pydantic-like configuration. Current implementation works on ClassVar. I want to separate
      configuration and main repository code.
      NOTE: added since 3.0.0
* [x] Improve messages in warnings and exceptions. Now some of them (for example, warnings in
      repository model_class checker method - __init_subclass__) have generic message, that has
      not enough context to understand it and locate incorrect usage code. 
      NOTE: added since 5.1.2

For more TODOs see [TODO file](./TODO.md)

If all these todo items are finished, it means, that all, what I want, is implemented.
If you want to give me advice or feedback, you are welcome.


## Install

With pip:

```bash
pip install sqlrepo
```

With poetry / PDM / uv:

```bash
<tool> add sqlrepo
```

or other dependency managers.

## Usage

sqlrepo provides base classes with CRUD operations, so you just need to inherit them with your
SQLAlchemy model and implement needed methods like this:

```python
from sqlrepo import BaseSyncRepository, BaseAsyncRepository

from your_package.models import YourModel

class YourModelSyncRepository(BaseSyncRepository[YourModel]):
    def get(self, your_model_id: int) -> YourModel:
          return self._get(filters={"your_model_id": your_model_id})

class YourModelAsyncRepository(BaseAsyncRepository[YourModel]):
      async def get(self, your_model_id: int) -> YourModel:
            return await self._get(filters={"your_model_id": your_model_id})
```

If you don't want to specify your methods and want to use private methods directly, you should
inherit your repository with ``SyncRepository``, ``AsyncRepository``, which implements all
repository methods.

## Configuration

sqlrepo Repository classes provide many options, which you can configure to make repositories
work like you need. To configure your repository class, You can use `RepositoryConfig` and init
it in class body like this:

```python
from sqlrepo import BaseSyncRepository, RepositoryConfig

from your_package.models import YourModel

class YourModelSyncRepository(BaseSyncRepository[YourModel]):
    config = RepositoryConfig(...)
```

Config params are the following:

### `model_class`

Model class for repository.

You can set this option manually, but it is not recommended. Repository will automatically
add model_class attribute by extracting it from Generic type.

Use case:

```python
from my_package.models import Admin

from sqlrepo import SyncRepository


class AdminRepository(SyncRepository[Admin]):
    ...

```

So, when you will use AdminRepository, model_class attribute will be set with Admin  automatically.

or you can do it twice like this:

```python
from my_package.models import Admin

from sqlrepo import SyncRepository


class AdminRepository(SyncRepository[Admin]):
    model_class = Admin
```

### `specific_column_mapping`

Warning! Current version of sqlrepo doesn't support this mapping for filters, joins and loads.

Uses as mapping for some attributes, that you need to alias or need to specify column
from other models.

Warning: if you specify column from other model, it may cause errors. For example, update
doesn't use it for filters, because joins are not presents in update.

Current implementation use these option in search_by and order_by params, if you pass them as
strings.

```python
from my_package.models import Admin

from sqlrepo import SyncRepository, RepositoryConfig


class AdminRepository(SyncRepository[Admin]):
    config = RepositoryConfig(
        specific_column_mapping={
            "custom_field": Admin.id,
            "other_field": Admin.name,
        }
    )


admins = AdminRepository(session).list(
    search='abc',
    search_by="other_field",
    order_by='custom_field',
)
```

### `use_flush`

Uses as flag of `flush` method in SQLAlchemy session.

By default, True, because repository has (mostly) multiple methods evaluate use. For example,
generally, you want to create some model instances, create some other (for example, log table)
and then receive other model instance in one use (for example, in Unit of work pattern).

If you will work with repositories as single methods uses, switch to use_flush=False. It will
make queries commit any changes.

### `update_set_none`

Uses as flag of set None option in `update_instance` method.

If True, allow to force `update_instance` instance columns with None value. Works together
with `update_allowed_none_fields`.

By default False, because it's not safe to set column to None - current version if sqlrepo
not able to check optional type. Will be added in next versions, and then `update_set_none`
will be not necessary.

### `update_allowed_none_fields`

Set of strings, which represents columns of model.

Uses as include or exclude for given data in `update_instance` method.

By default allow any fields. Not dangerous, because `update_set_none` by default set to False,
and there will be no affect on `update_instance` method

### `allow_disable_filter_by_value`

Uses as flag of filtering in disable method.

If True, make additional filter, which will exclude items, which already disabled.
Logic of disable depends on type of disable column. See `disable_field` docstring for more
information.

By default True, because it will make more efficient query to not override disable column. In
some cases (like datetime disable field) it may be better to turn off this flag to save disable
with new context (repeat disable, if your domain supports repeat disable and it make sense).

### `disable_field_type`

Uses as choice of type of disable field.

By default, None. Needs to be set manually, because this option depends on user custom
implementation of disable_field. If None and `disable` method was evaluated, there will be
RepositoryAttributeError exception raised by Repository class.

### `disable_field`

Uses as choice of used defined disable field.

By default, None. Needs to be set manually, because this option depends on user custom
implementation of disable_field. If None and `disable` method was evaluated, there will be
RepositoryAttributeError exception raised by Repository class.

Now only works with string fields, because otherwise sqlalchemy think that Repository class is
sqlalchemy model without mapping, and raise error.

### `disable_id_field`

Uses as choice of used defined id field in model, which supports disable.

By default, None. Needs to be set manually, because this option depends on user custom
implementation of disable_field. If None and `disable` method was evaluated, there will be
RepositoryAttributeError exception raised by Repository class.

Now only works with string fields, because otherwise sqlalchemy think that Repository class is
sqlalchemy model without mapping, and raise error.

### `unique_list_items`

__Warning!__ Ambiguous option!

Current version of `sqlrepo` works with load strategies with user configured option
`load_strategy`. In order to make `list` method works stable, this option is used.
If you don't work with relationships in your model or you don't need unique (for example,
if you use selectinload), set this option to False. Otherwise keep it in True state.

### `filter_convert_strategy`

Uses as choice of filter convert.

By default "simple", so you able to pass filters with ``key-value`` structure. You still can
pass raw filters (just list of SQLAlchemy filters), but if you pass dict, it will be converted
to SQLAlchemy filters with passed strategy.

Currently, supported converters:

* `simple` - `key-value` dict.

* `advanced` - dict with `field`, `value` and `operator` keys.
List of operators: `=, >, <, >=, <=, is, is_not, between, contains`.

* `django-like` - `key-value` dict with django-like lookups system. See django docs for
more info.

## Extensions

v1.5.0 now provided extensions for other technologies like web-frameworks. Now only FastAPI is
supported.

### FastAPI

FastAPI extensions implements base classes for services and container, so you can work with your
code easier.

Attention! Container is good solution, if you want to simplify your work with services and
repositories, but it cause situation, when you can access any services in any routes. It's not
safe, so be careful.

First of all You need to prepare all to work with plugin:

```python
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine("<your-db-url-here>")
Session = sessionmaker(engine)


class Base(DeclarativeBase): ...


class YourModel(Base):
    # Your model definition
    ...


def get_session():
    with Session() as session:
        yield session


app = FastAPI()
```

then you should use plugin like this:

```python
# your prepared code below

from sqlrepo.ext.fastapi import add_session_stub_overrides
add_session_stub_overrides(app, get_session)
```

then you can implements containers and services like this:

```python
# your prepared code below

from functools import cached_property
from pydantic import BaseModel, ConfigDict

from sqlrepo import BaseSyncRepository
from sqlrepo.ext.fastapi import BaseSyncContainer, BaseSyncService


class YourModelDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    ...


class YourModelList(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    ...


class YourModelRepository(BaseSyncRepository[YourModel]):
    def your_custom_repo_method(self) -> YourModel: ...


class YourModelService(BaseSyncService[YourModel, YourModelDetail, YourModelList]):
    detail_schema = YourModelDetail
    list_schema = YourModelList
    not_found_message = "YourModel entity not found in database"
    not_found_exception = HTTPException

    def init_repositories(self, session: "Session") -> None:
        self.your_model_repo = YourModelRepository(session)

    def your_custom_service_method(self) -> YourModelDetail:
        return self.resolve(self.your_model_repo.your_custom_repo_method())


class Container(BaseSyncContainer):

    @cached_property
    def your_model_service(self):
        return YourModelService(self.request, self.session)
```

and finally you can use Container in your routes like this:

```python
# your prepared code below

@app.get("/", response_model=YourModelDetail)
def get_your_model(container: Container = Depends()):
    return container.your_model_service.your_custom_service_method()
```
