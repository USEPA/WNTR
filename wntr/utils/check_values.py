def _check_float(value, property_name: str) -> float:
    """Transform a value to a float.

    Raises ValueError if the value is not a float or convertible to float.
    """
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        value_type = type(value).__name__
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


def _check_float_or_none(value, property_name: str) -> float | None:
    """Transform a value to a float, unless it is None in which case return None.

    Raises ValueError if the value is not a float or convertible to float,
    and is not None.
    """
    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError) as e:
        value_type = type(value).__name__
        raise ValueError(
            f"{property_name} must be a float, convertible to float, or None. Received {value} of type {value_type}"
        ) from e