"""Exceptions for sqlrepo project."""

# |--------------| BASE |--------------|


class BaseSQLRepoError(Exception):
    """Base sqlrepo error."""


# |--------------| REPOSITORIES |--------------|


class RepositoryError(BaseSQLRepoError):
    """Base repository error."""


class RepositoryAttributeError(RepositoryError):
    """Repository error about incorrect attribute."""


# |--------------| QUERIES |--------------|


class QueryError(BaseSQLRepoError):
    """Base query error."""
