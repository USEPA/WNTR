"""
Test the wntr.utils module
"""

import numpy as np
import pytest

from wntr.utils.check_values import (
    _check_bool,
    _check_float,
    _check_int,
    _check_numeric_or_str,
    _check_positive_non_zero_float,
    _check_positive_or_zero_float,
    _check_str,
)


@pytest.mark.parametrize("value", [1.0, 1, "400", 2.71828])
def test_positive_non_zero_float(value):
    assert _check_positive_non_zero_float(value, "test") == float(value)


@pytest.mark.parametrize("value", [0, "0", 0.0, "not_a_number", -1, -2.71828, [-1, 2]])
def test_positive_non_zero_float_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_positive_non_zero_float(value, "test")


@pytest.mark.parametrize("value", [0.0, 0, "0", 1.0, 1, "500", 0, 2.71828])
def test_positive_or_zero_float(value):
    assert _check_positive_or_zero_float(value, "test") == float(value)


@pytest.mark.parametrize("value", ["not_a_number", -1, -2.71828, [-1, 2]])
def test_positive_or_zero_float_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_positive_or_zero_float(value, "test")


@pytest.mark.parametrize("value", [1.0, 1, "400", 2.71828, 0.0, 0, -1, -2.71828])
def test_check_float(value):
    assert _check_float(value, "test") == float(value)


@pytest.mark.parametrize("value", ["not_a_number", [-1, 2]])
def test_check_float_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_float(value, "test")


@pytest.mark.parametrize("value", [1.0, 1, "400", 2.71828, 0.0, 0, -1, -2.71828])
def test_check_float_allow_none_with_float(value):
    assert _check_float(value, "test", allow_none=True) == float(value)


def test_check_float_allow_none_with_none():
    assert _check_float(None, "test", allow_none=True) is None


def test_check_float_no_allow_none_with_none():
    with pytest.raises(ValueError, match="test"):
        _check_float(None, "test")


@pytest.mark.parametrize("value", ["not_a_number", [-1, 2]])
def test_check_float_allow_none_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_float(value, "test", allow_none=True)


@pytest.mark.parametrize(
    "value",
    [1, 1.0, 3.0, "400", np.int32(7), np.int64(7), np.float32(7.0), np.float64(7.0)],
)
def test_check_int(value):
    assert _check_int(value, "test") == int(value)


@pytest.mark.parametrize("value", [3.5, "not_a_number", None, [-1, 2]])
def test_check_int_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_int(value, "test")


@pytest.mark.parametrize(
    "value",
    [1, 1.0, 3.0, "400", np.int32(7), np.int64(7), np.float32(7.0), np.float64(7.0)],
)
def test_check_int_allow_none_with_int(value):
    assert _check_int(value, "test", allow_none=True) == int(value)


def test_check_int_allow_none_with_none():
    assert _check_int(None, "test", allow_none=True) is None


def test_check_int_no_allow_none_with_none():
    with pytest.raises(ValueError, match="test"):
        _check_int(None, "test")


@pytest.mark.parametrize("value", [3.5, "not_a_number", [-1, 2]])
def test_check_int_allow_none_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_int(value, "test", allow_none=True)


@pytest.mark.parametrize(
    "value", [1.0, 1, 2.71828, np.float32(2.0), np.float64(2.0), np.int64(2)]
)
def test_check_numeric_or_str_with_number(value):
    assert _check_numeric_or_str(value, "test") == float(value)


def test_check_numeric_or_str_with_str():
    assert _check_numeric_or_str("HEAD", "test") == "HEAD"


@pytest.mark.parametrize("value", [None, [-1, 2]])
def test_check_numeric_or_str_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_numeric_or_str(value, "test")


@pytest.mark.parametrize("value", [True, False, np.bool_(True), np.bool_(False)])
def test_check_bool(value):
    assert _check_bool(value, "test") == bool(value)


@pytest.mark.parametrize("value", [0, 1, "True", "False", "0", None, [True]])
def test_check_bool_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_bool(value, "test")


@pytest.mark.parametrize("value", ["HEAD", "", np.str_("HEAD")])
def test_check_str(value):
    assert _check_str(value, "test") == str(value)


@pytest.mark.parametrize("value", [1, 1.0, None, True, [1, 2]])
def test_check_str_bad_value(value):
    with pytest.raises(ValueError, match="test"):
        _check_str(value, "test")
