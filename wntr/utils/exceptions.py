# coding: utf-8
"""
Exception classes for WNTR warnings and errors.
"""


class WNTRException(Exception):  # pragma: no cover
    """
    Base class for filtering WNTR specific exceptions.
    """

    pass


class NetworkModelError(WNTRException):  # pragma: no cover
    """
    The requested water network model action is impossible.
    """

    pass


class SimulatorError(WNTRException):  # pragma: no cover
    """
    An error occurred during simulation or the action on the simulator is not possible.
    """

    pass


class ToolkitError(WNTRException):  # pragma: no cover
    """
    An error occurred in the EPANET toolkit.
    """

    pass


class WNTRWarning(Warning):  # pragma: no cover
    """
    Base class for filtering WNTR specific warnings.
    """

    pass


class NetworkModelWarning(WNTRWarning):  # pragma: no cover
    """
    The requested action on the water network model is not possible, but its failure can simply go ignored.
    """

    pass


class SimulatorWarning(WNTRWarning):  # pragma: no cover
    """
    The requested action on the simulator is not possible, but it can be ignored, or there is something wrong in the simulation, but it can continue.
    """

    pass


class ToolkitWarning(WNTRWarning):  # pragma: no cover
    """
    The EPANET toolkit issued a warning.
    """

    pass
