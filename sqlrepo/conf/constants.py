generic_usage_postfix = (
    "If you use repository class without generic or need to use it with different class, which is "
    "not a SQLAlchemy declarative model class, you should use "
    "``__inheritance_check_model_class__ = False`` in your repository class to disable this "
    "warning."
)
only_declarative_postfix = "Repository class can only work with SQLAlchemy declarative models."
generic_usage_with_only_declarative_postfix = f'{only_declarative_postfix} {generic_usage_postfix}'

REPOSITORY_VALIDATE_DISABLE_ATTRIBUTES_ERROR = (
    'Attribute "disable_id_field" or "disable_field" or "disable_field_type" not '
    "set in your repository class. Can't disable entities."
)
REPOSITORY_MODEL_ALREADY_DEFINED_WARNING = (
    "Don't change model_class attribute to class. Use generic syntax instead. "
    "See PEP 646 (https://peps.python.org/pep-0646/). Repository will automatically "
    "add model_class attribute by extracting it from Generic type. "
) + generic_usage_postfix
REPOSITORY_NO_GENERIC_INHERITANCE_WARNING = (
    "Incorrect inheritance from Repository classes. Parent class has no generics."
) + generic_usage_postfix
REPOSITORY_GETTING_GENERIC_INFO_WARNING_TEMPLATE = (
    "Error during getting information about Generic types for {cls.__name__}. "
    "Original exception: {exc!s}. "
) + generic_usage_postfix
REPOSITORY_GET_MODULE_INSTANCE_ERROR_TEMPLATE = (
    "No attribute __module__ in {cls}. Can't import global context for ForwardRef resolving. "
) + generic_usage_postfix
REPOSITORY_RESOLVE_FORWARD_REF_WARNING_TEMPLATE = (
    "Can't evaluate ForwardRef of generic type. Don't use type in generic with quotes. "
    "Original exception: {exc!s}. "
) + generic_usage_postfix
REPOSITORY_GENERIC_TYPE_NOT_PASSED_WARNING = (
    "GenericType was not passed for SQLAlchemy model declarative class. "
) + generic_usage_postfix
REPOSITORY_GENERIC_TYPE_TYPE_VAR_PASSED_WARNING = (
    "GenericType is TypeVar. "
) + generic_usage_postfix
REPOSITORY_GENERIC_TYPE_IS_NOT_CLASS_WARNING = (
    "Passed GenericType is not a class. "
) + generic_usage_with_only_declarative_postfix
REPOSITORY_GENERIC_TYPE_IS_NOT_MODEL = (
    "Passed GenericType is not SQLAlchemy model declarative class.  "
) + generic_usage_with_only_declarative_postfix
