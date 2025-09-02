import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Literal

from sqlalchemy_filter_converter import (
    AdvancedFilterConverter,
    BaseFilterConverter,
    DjangoLikeFilterConverter,
    SimpleFilterConverter,
)
from sqlalchemy_filter_converter.types import FilterConverterStrategiesLiteral

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences
    from sqlrepo.types import DisableField, DisableIdField, SpecificColumnMapping, StrField


filter_convert_classes: Final[dict[FilterConverterStrategiesLiteral, type[BaseFilterConverter]]] = {
    "simple": SimpleFilterConverter,
    "advanced": AdvancedFilterConverter,
    "django": DjangoLikeFilterConverter,
}
"""Convert class filters mapping."""


@dataclass(slots=True)
class RepositoryConfig:
    """Repository config as dataclass."""

    # TODO: add specific_column_mapping to filters, joins and loads.
    specific_column_mapping: "SpecificColumnMapping" = field(default_factory=dict)
    """
    Warning! Current version of sqlrepo doesn't support this mapping for filters, joins and loads.

    Uses as mapping for some attributes, that you need to alias or need to specify column
    from other models.

    Warning: if you specify column from other model, it may cause errors. For example, update
    doesn't use it for filters, because joins are not presents in update.
    """
    use_flush: bool = field(default=True)
    """
    Uses as flag of flush method in SQLAlchemy session.

    By default, True, because repository has (mostly) multiple methods evaluate use. For example,
    generally, you want to create some model instances, create some other (for example, log table)
    and then receive other model instance in one use (for example, in Unit of work pattern).

    If you will work with repositories as single methods uses, switch to use_flush=False. It will
    make queries commit any changes.
    """
    update_set_none: bool = field(default=False)
    """
    Uses as flag of set None option in ``update_instance`` method.

    If True, allow to force ``update_instance`` instance columns with None value. Works together
    with ``update_allowed_none_fields``.

    By default False, because it's not safe to set column to None - current version if sqlrepo
    not able to check optional type. Will be added in next versions, and ``then update_set_none``
    will be not necessary.
    """
    update_allowed_none_fields: 'Literal["*"] | set[StrField]' = field(default="*")
    """
    Set of strings, which represents columns of model.

    Uses as include or exclude for given data in ``update_instance`` method.

    By default allow any fields. Not dangerous, because ``update_set_none`` by default set to False,
    and there will be no affect on ``update_instance`` method
    """
    allow_disable_filter_by_value: bool = field(default=True)
    """
    Uses as flag of filtering in disable method.

    If True, make additional filter, which will exclude items, which already disabled.
    Logic of disable depends on type of disable column. See ``disable_field`` docstring for more
    information.

    By default True, because it will make more efficient query to not override disable column. In
    some cases (like datetime disable field) it may be better to turn off this flag to save disable
    with new context (repeat disable, if your domain supports repeat disable and it make sense).
    """
    disable_field_type: type[datetime.datetime] | type[bool] | None = field(default=None)
    """
    Uses as choice of type of disable field.

    By default, None. Needs to be set manually, because this option depends on user custom
    implementation of disable_field. If None and ``disable`` method was evaluated, there will be
    RepositoryAttributeError exception raised by Repository class.
    """
    disable_field: "DisableField | None" = field(default=None)
    """
    Uses as choice of used defined disable field.

    By default, None. Needs to be set manually, because this option depends on user custom
    implementation of disable_field. If None and ``disable`` method was evaluated, there will be
    RepositoryAttributeError exception raised by Repository class.
    """
    disable_id_field: "DisableIdField | None" = field(default=None)
    """
    Uses as choice of used defined id field in model, which supports disable.

    By default, None. Needs to be set manually, because this option depends on user custom
    implementation of disable_field. If None and ``disable`` method was evaluated, there will be
    RepositoryAttributeError exception raised by Repository class.
    """
    unique_list_items: bool = field(default=True)
    """
    Warning! Ambiguous option!
    ==========================

    Current version of ``sqlrepo`` works with load strategies with user configured option
    ``load_strategy``. In order to make ``list`` method works stable, this option is used.
    If you don't work with relationships in your model or you don't need unique (for example,
    if you use selectinload), set this option to False. Otherwise keep it in True state.
    """
    filter_convert_strategy: "FilterConverterStrategiesLiteral" = field(default="simple")
    """
    Uses as choice of filter convert.

    By default "simple", so you able to pass filters with ``key-value`` structure. You still can
    pass raw filters (just list of SQLAlchemy filters), but if you pass dict, it will be converted
    to SQLAlchemy filters with passed strategy.

    Currently, supported converters:

        ``simple`` - ``key-value`` dict.

        ``advanced`` - dict with ``field``, ``value`` and ``operator`` keys.
        List of operators:

            ``=, >, <, >=, <=, is, is_not, between, contains``

        ``django-like`` - ``key-value`` dict with django-like lookups system. See django docs for
        more info.
    """

    def get_filter_convert(self) -> BaseFilterConverter:
        """Get filter convert class from passed strategy."""
        converter_class = filter_convert_classes[self.filter_convert_strategy]
        return converter_class(specific_column_mapping=self.specific_column_mapping)
