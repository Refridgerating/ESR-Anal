"""Signal processing utilities for ESR-Lab."""

from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy import integrate, interpolate, optimize, signal

Array = np.ndarray


def _as_array(x: Array) -> Array:
    """Return ``x`` as a ``float`` ``ndarray``."""
    return np.asarray(x, dtype=float)


def poly_baseline(
    field_B: Array, y: Array, order: int = 2, mask: Array | None = None
) -> Tuple[Array, Array]:
    """Polynomial baseline correction using robust least squares.

    Parameters
    ----------
    field_B : np.ndarray
        Field axis in tesla.
    y : np.ndarray
        Signal array.
    order : int, optional
        Polynomial order, by default 2.
    mask : np.ndarray | None, optional
        Optional boolean mask selecting baseline region.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Baseline and baseline corrected signal.
    """

    x = _as_array(field_B)
    y = _as_array(y)
    if mask is not None:
        x_fit = x[mask]
        y_fit = y[mask]
    else:
        x_fit = x
        y_fit = y

    # Vandermonde matrix for polynomial fit
    X = np.vander(x_fit, order + 1, increasing=True)

    def resid(c: Array) -> Array:
        return X @ c - y_fit

    res = optimize.least_squares(resid, x0=np.zeros(order + 1), loss="soft_l1")
    coef = res.x
    baseline = np.vander(x, order + 1, increasing=True) @ coef
    y_corr = y - baseline
    return baseline, y_corr


def spline_baseline(
    field_B: Array, y: Array, knots: Array | None = None, s: float | None = None
) -> Tuple[Array, Array]:
    """Spline baseline subtraction.

    Parameters
    ----------
    field_B : np.ndarray
        Field axis.
    y : np.ndarray
        Signal array.
    knots : np.ndarray | None
        Optional internal knots for :class:`LSQUnivariateSpline`.
    s : float | None
        Smoothing factor for :class:`UnivariateSpline`. When ``None`` the
        factor is estimated from the median absolute deviation of the data.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        Baseline and baseline corrected signal.
    """

    x = _as_array(field_B)
    y = _as_array(y)

    if s is None:
        mad = np.median(np.abs(y - np.median(y)))
        s = len(x) * (1.4826 * mad) ** 2

    if knots is not None and len(knots) > 0:
        spline = interpolate.LSQUnivariateSpline(x, y, knots, k=3)
    else:
        spline = interpolate.UnivariateSpline(x, y, s=s)

    baseline = spline(x)
    y_corr = y - baseline
    return baseline, y_corr


def savgol_smooth(y: Array, window: int, polyorder: int) -> Array:
    """Apply Savitzky-Golay smoothing to ``y``.

    Parameters
    ----------
    y : np.ndarray
        Input signal.
    window : int
        Smoothing window (must be odd).
    polyorder : int
        Polynomial order (< ``window``).
    """

    if window % 2 == 0 or window <= 0:
        raise ValueError("window must be a positive odd integer")
    if window <= polyorder:
        raise ValueError("window must be greater than polyorder")
    return signal.savgol_filter(_as_array(y), window, polyorder)


def phase_correct(y_deriv: Array, phase_rad: float) -> Array:
    """Rotate derivative signal by ``phase_rad`` using Hilbert transform."""

    y_deriv = _as_array(y_deriv)
    analytic = signal.hilbert(y_deriv)
    rotated = np.real(analytic * np.exp(-1j * phase_rad))
    return rotated


def phase_auto(
    y_deriv: Array,
    search_deg: Tuple[int, int] = (-20, 20),
    step_deg: float = 0.25,
) -> float:
    """Automatically find optimal phase angle.

    Parameters
    ----------
    y_deriv : np.ndarray
        First derivative signal.
    search_deg : tuple[int, int], optional
        Search range in degrees, by default (-20, 20).
    step_deg : float, optional
        Step size in degrees, by default 0.25.

    Returns
    -------
    float
        Optimal phase in radians.
    """

    y_deriv = _as_array(y_deriv)
    analytic = signal.hilbert(y_deriv)
    angles = np.deg2rad(np.arange(search_deg[0], search_deg[1] + step_deg, step_deg))
    best_angle = 0.0
    best_norm = np.inf
    for ang in angles:
        dispersion = np.imag(analytic * np.exp(-1j * ang))
        nrm = np.linalg.norm(dispersion)
        if nrm < best_norm:
            best_norm = nrm
            best_angle = ang
    return float(best_angle)


def integrate_absorption(field_B: Array, y_deriv: Array) -> Array:
    """Integrate derivative to obtain absorption spectrum."""

    x = _as_array(field_B)
    y = _as_array(y_deriv)
    y_abs = integrate.cumulative_trapezoid(y, x, initial=0.0)
    slope = (y_abs[-1] - y_abs[0]) / (x[-1] - x[0])
    baseline = slope * (x - x[0]) + y_abs[0]
    return y_abs - baseline


def integrate_area(
    field_B: Array, y_abs: Array, roi: Tuple[float, float] | None = None
) -> float:
    """Compute area under absorption spectrum within ROI."""

    x = _as_array(field_B)
    y = _as_array(y_abs)
    if roi is not None:
        Bmin, Bmax = roi
        mask = (x >= Bmin) & (x <= Bmax)
        x = x[mask]
        y = y[mask]
    n_edge = max(1, len(x) // 20)
    idx = np.r_[:n_edge, len(x) - n_edge : len(x)]
    coef = np.polyfit(x[idx], y[idx], 1)
    baseline = np.polyval(coef, x)
    y_corr = y - baseline
    area = np.trapz(y_corr, x)
    return float(area)


def subset(field_B: Array, y: Array, Bmin: float, Bmax: float) -> Tuple[Array, Array]:
    """Return subset of data between ``Bmin`` and ``Bmax`` (inclusive)."""

    if Bmin >= Bmax:
        raise ValueError("Bmin must be less than Bmax")
    mask = (field_B >= Bmin) & (field_B <= Bmax)
    if np.sum(mask) < 10:
        raise ValueError("Subset must contain at least 10 points")
    return field_B[mask], y[mask]

