import numpy as np
import pytest
from scipy.constants import hbar, physical_constants

from esr_lab.core import physics

mu_B = physical_constants["Bohr magneton"][0]


def test_linewidth_conversions() -> None:
    dBpp = 1e-3
    fwhm_l = physics.fwhm_from_pp_lorentz(dBpp)
    fwhm_g = physics.fwhm_from_pp_gauss(dBpp)
    assert pytest.approx(np.sqrt(3) * dBpp, rel=1e-12) == fwhm_l
    assert pytest.approx(1.177 * dBpp, rel=1e-12) == fwhm_g


def test_hyperfine_and_gamma() -> None:
    A = physics.hyperfine_A_MHz_from_spacing(1.0, 2.0)
    assert pytest.approx(56.0499, rel=1e-4) == A
    gamma = physics.gamma_from_g(2.0)
    assert pytest.approx(2.0 * mu_B / hbar, rel=1e-12) == gamma


def test_T2_from_fwhm_lorentz() -> None:
    g = 2.0
    fwhm = 1e-3
    T2 = physics.T2_from_fwhm_lorentz(fwhm, g)
    gamma = physics.gamma_from_g(g)
    assert pytest.approx(1 / (gamma * fwhm), rel=1e-12) == T2
    with pytest.raises(ValueError):
        physics.T2_from_fwhm_lorentz(-1.0, g)
    with pytest.raises(ValueError):
        physics.T2_from_fwhm_lorentz(fwhm, -1.0)
