# TODOs

## Major 

- [ ] Add more backends for repository pattern. Now, only SQLAlchemy adapter implemented. I want
  to implement other backends to make this repository better to use in different situations.
  NOTE: in future sqlrepo will be replaced with something like python-repository-pattern.
- [x] Add wrapper for all non sqlrepo exceptions. Now, some functionality could raise
  "raw" SQLAlchemy error. I want to avoid the situation, when developer make
  try-except with all possible exceptions, when works with my package.
  NOTE: added since 1.4.0
- [ ] Add more use-cases of `specific_column_mapping` option. Now it only works with
  `search_by` and `order_by` params. I want to add it for filters, joins and other
  parts, where it can be used.
- [x] Integrate sqlrepo with FastAPI or some other web-frameworks.
  NOTE 1: added since 1.5.0. Continued until 2.0.0. I currently not aimed to work on FastAPI.
  NOTE 2: removed since 6.0.0. Bad integration.
- [x] Add pydantic-like configuration. Current implementation works on ClassVar. I want to separate
  configuration and main repository code.
  NOTE: added since 3.0.0
- [ ] Config rework:
    - [ ] Rework config `unique_list_items` - currently it has unexpected behaviors,
      so to prevent it, Query-classes should inspect queries for it to add
      unique only if error may be raised.
    - [ ] Change `use_flush` default to False or remove default
    - [ ] Raname `update_set_none` and `update_allowed_none_fields` - not understandable field names
    - [ ] Add more verbose information of config fields
    - [ ] Replace `filter_convert_strategy` with `filter_class` to allow users to make their own
          filter classes

## Minor

- [ ] Add documentation for package (GH wiki / MkDocs / other documentation resource).
- [ ] Add more tests for repositories and queries.
- [ ] Replace PyRight with Mypy.
- [ ] Add Python3.13 support.
- [ ] Check for compatibility with structlog. Add structlog support if needed.
- [ ] Add more variance of exceptions. 
- [ ] Actualize CI/CD process: check best practices from other repositories.
- [x] Improve messages in warnings and exceptions. Now some of them (for example, warnings in
  repository model_class checker method - `__init_subclass__`) have generic message, that has
  not enough context to understand it and locate incorrect usage code.
  NOTE: added since 5.1.2

## Refactoring

- [ ] Move asserts from `tests.utils` file to helper class.
- [ ] Rewrite all tests to class-based with setup.
- [ ] remove factories from tests, rewrite to classes FactoryHelper and StorageHelper.
- [ ] Simplify `conftest.py`: Remove sessionmaker fixture and simplify engine create.
- [ ] Simplify auto-detection of repository model.
- [ ] Separate Makefile lint and fix commands to sub-commands.
