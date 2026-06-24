import numpy as np


def _check_float(value, property_name: str, allow_none: bool = False) -> float | None:
    """Transform a value to a float.

    Raises ValueError if the value is not a float or convertible to float.
    If allow_none is True, None is returned unchanged instead of raising.
    """
    if value is None and allow_none:
        return None

    try:
        return float(value)
    except (ValueError, TypeError) as e:
        value_type = type(value).__name__
        if allow_none:
            raise ValueError(
                f"{property_name} must be a float, convertible to float, or None. Received {value} of type {value_type}"
            ) from e
        raise ValueError(
            f"{property_name} must be a float or convertible to float. Received {value} of type {value_type}"
        ) from e


def _check_positive_or_zero_float(value, property_name: str) -> float:
    """Transform a value to a float and check it is positive or zero.

    Raises ValueError if the value is not a float or convertible to float,
    or if the value is negative.
    """
    value = _check_float(value, property_name)

    if value < 0:
        raise ValueError(f"{property_name} must not be negative")

    return value


def _check_positive_non_zero_float(value, property_name: str) -> float:
    """Transform a value to a float and check it is positive.

    Raises ValueError if the value is not a float or convertible to float,
    or if the value is not positive.
    """
    value = _check_float(value, property_name)

    if not value > 0:
        raise ValueError(f"{property_name} must be greater than zero")

    return value


def _check_int(value, property_name: str, allow_none: bool = False) -> int | None:
    """Transform a value to an int.

    Raises ValueError if the value is not an int or convertible to int
    without loss (e.g. 3.5 is rejected, while 3.0 and np.int64(3) are accepted).
    If allow_none is True, None is returned unchanged instead of raising.
    """
    if value is None and allow_none:
        return None

    try:
        int_value = int(value)
    except (ValueError, TypeError) as e:
        value_type = type(value).__name__
        if allow_none:
            raise ValueError(
                f"{property_name} must be an int, convertible to int, or None. Received {value} of type {value_type}"
            ) from e
        raise ValueError(
            f"{property_name} must be an int or convertible to int. Received {value} of type {value_type}"
        ) from e

    if isinstance(value, float) and value != int_value:
        raise ValueError(f"{property_name} must be an integer value. Received {value}")

    return int_value


def _check_bool(value, property_name: str) -> bool:
    """Transform a value to a bool.

    Raises ValueError if the value is not a bool (including numpy bool types).
    Numeric and string values (e.g. 0/1, "True"/"False") are intentionally
    rejected rather than coerced, since Python's bool() would silently treat
    any non-empty string (including "False") as True.
    """
    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    value_type = type(value).__name__
    raise ValueError(f"{property_name} must be a bool. Received {value} of type {value_type}")


def _check_str(value, property_name: str) -> str:
    """Transform a value to a str.

    Raises ValueError if the value is not a str (including numpy str types,
    which are a subclass of str).
    """
    if isinstance(value, str):
        return str(value)

    value_type = type(value).__name__
    raise ValueError(f"{property_name} must be a string. Received {value} of type {value_type}")


def _check_numeric_or_str(value, property_name: str):
    """Return the value unchanged if it is a string, otherwise transform it to a float.

    Raises ValueError if the value is not a string and not a float or convertible to float.
    """
    if isinstance(value, str):
        return value

    try:
        return float(value)
    except (ValueError, TypeError) as e:
        value_type = type(value).__name__
        raise ValueError(
            f"{property_name} must be a float, convertible to float, or a string. Received {value} of type {value_type}"
        ) from e
