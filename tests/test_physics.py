"""Tests for :mod:`backend.core.physics`."""

import logging
from pathlib import Path

import numpy as np
import pytest
from scipy.constants import hbar, physical_constants

from backend.core import physics
from backend.utils.logging import get_logger

mu_B = physical_constants["Bohr magneton"][0]


@pytest.fixture
def physics_logger(tmp_path: Path) -> logging.Logger:
    """Logger writing to a temporary file for each test."""

    log_path = tmp_path / "physics.log"
    logger = get_logger("test_physics")
    logger.handlers.clear()
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter("%(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    yield logger
    for h in list(logger.handlers):
        h.flush()
        h.close()
    logger.handlers.clear()


def test_fwhm_from_pp_lorentz(physics_logger: logging.Logger) -> None:
    dBpp = 1e-3
    expected = np.sqrt(3) * dBpp
    result = physics.fwhm_from_pp_lorentz(dBpp)
    physics_logger.info("Lorentz FWHM expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-12) == result


def test_fwhm_from_pp_gauss(physics_logger: logging.Logger) -> None:
    dBpp = 1e-3
    expected = 1.177 * dBpp
    result = physics.fwhm_from_pp_gauss(dBpp)
    physics_logger.info("Gaussian FWHM expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-12) == result


def test_hyperfine_A_MHz_from_spacing(physics_logger: logging.Logger) -> None:
    expected = 2.0 * 28.02495 * 1.0
    result = physics.hyperfine_A_MHz_from_spacing(1.0, 2.0)
    physics_logger.info("Hyperfine A expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-4) == result


def test_gamma_from_g(physics_logger: logging.Logger) -> None:
    expected = 2.0 * mu_B / hbar
    result = physics.gamma_from_g(2.0)
    physics_logger.info("Gamma expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-12) == result


def test_g_factor(physics_logger: logging.Logger) -> None:
    expected = 2.0
    result = physics.g_factor(9.5e9, 0.339)
    physics_logger.info("g-factor expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-2) == result


def test_T2_from_fwhm_lorentz(physics_logger: logging.Logger) -> None:
    g = 2.0
    fwhm = 1e-3
    result = physics.T2_from_fwhm_lorentz(fwhm, g)
    gamma = physics.gamma_from_g(g)
    expected = 1 / (gamma * fwhm)
    physics_logger.info("T2 expected %s computed %s", expected, result)
    assert pytest.approx(expected, rel=1e-12) == result
    with pytest.raises(ValueError):
        physics.T2_from_fwhm_lorentz(-1.0, g)
    with pytest.raises(ValueError):
        physics.T2_from_fwhm_lorentz(fwhm, -1.0)
