"""Physics related utilities for ESR-Lab."""

from __future__ import annotations

import numpy as np
from scipy.constants import h, hbar, physical_constants

mu_B = physical_constants["Bohr magneton"][0]


def g_factor(frequency_Hz: float, B0_T: float) -> float:
    """Compute g-factor from resonance frequency and magnetic field."""

    return float(h * frequency_Hz / (mu_B * B0_T))


def fwhm_from_pp_lorentz(dBpp_T: float) -> float:
    """Convert peak-to-peak Lorentzian width to full width at half maximum."""

    return float(np.sqrt(3) * dBpp_T)


def fwhm_from_pp_gauss(dBpp_T: float) -> float:
    """Convert peak-to-peak Gaussian width to full width at half maximum."""

    return float(1.177 * dBpp_T)


def hyperfine_A_MHz_from_spacing(dB_mT: float, g: float) -> float:
    """Hyperfine constant ``A`` in MHz from line spacing in mT and ``g``."""

    return float(g * 28.02495 * dB_mT)


def gamma_from_g(g: float) -> float:
    """Gyromagnetic ratio ``gamma`` in rad/s/T from g-factor."""

    return float(g * mu_B / hbar)


def T2_from_fwhm_lorentz(FWHM_T: float, g: float) -> float:
    """Spin-spin relaxation time ``T2`` from Lorentzian FWHM.

    Parameters
    ----------
    FWHM_T : float
        Full width at half maximum in tesla.
    g : float
        g-factor.

    Returns
    -------
    float
        ``T2`` in seconds.
    """

    if FWHM_T <= 0 or g <= 0:
        raise ValueError("FWHM and g must be positive")
    gamma = gamma_from_g(g)
    return float(1.0 / (gamma * FWHM_T))

