"""Unit conversion helpers for ESR-Lab."""

from __future__ import annotations

from typing import Union

import numpy as np

# Define type alias for float or ndarray
ArrayLike = Union[float, np.ndarray]


def mt_to_t(mt: ArrayLike) -> ArrayLike:
    """Convert millitesla to tesla.

    Parameters
    ----------
    mt : float | np.ndarray
        Value(s) in millitesla.

    Returns
    -------
    float | np.ndarray
        Value(s) in tesla.
    """

    arr = np.asarray(mt) * 1e-3
    return arr.item() if np.isscalar(mt) else arr


def g_to_t(g: ArrayLike) -> ArrayLike:
    """Convert gauss to tesla."""

    arr = np.asarray(g) * 1e-4
    return arr.item() if np.isscalar(g) else arr


def gauss_to_t(g: ArrayLike) -> ArrayLike:
    """Alias for :func:`g_to_t` for clarity."""

    return g_to_t(g)


def t_to_mt(t: ArrayLike) -> ArrayLike:
    """Convert tesla to millitesla."""

    arr = np.asarray(t) * 1e3
    return arr.item() if np.isscalar(t) else arr


def hz_to_ghz(hz: float) -> float:
    """Convert hertz to gigahertz."""

    return float(hz) / 1e9


def ghz_to_hz(ghz: float) -> float:
    """Convert gigahertz to hertz."""

    return float(ghz) * 1e9


def mw_to_w(mw: float) -> float:
    """Convert milliwatt to watt."""

    return float(mw) * 1e-3


def w_to_mw(w: float) -> float:
    """Convert watt to milliwatt."""

    return float(w) * 1e3


def to_t_from_header(value_array: ArrayLike, header_str: str) -> np.ndarray:
    """Convert ``value_array`` to tesla based on units present in ``header_str``.

    The function looks for tokens like ``mT`` or ``G`` in ``header_str``.  If no
    token is found, the values are assumed to already be in tesla.
    """

    header = header_str.lower()
    if "mt" in header:
        return np.asarray(mt_to_t(value_array))
    if "g" in header and not header.endswith("kg"):
        return np.asarray(g_to_t(value_array))
    return np.asarray(value_array, dtype=float)

