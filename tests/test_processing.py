import numpy as np
import pytest

from backend.core import processing, units


def test_poly_baseline_removes_trend() -> None:
    x = np.linspace(-1, 1, 1000)
    baseline_true = 0.2 * x**2 + 0.1 * x + 0.5
    rng = np.random.default_rng(0)
    y = baseline_true + 0.05 * np.sin(5 * x) + 0.01 * rng.normal(size=x.size)
    baseline, y_corr = processing.poly_baseline(x, y, order=2)
    rms_before = np.sqrt(np.mean(y**2))
    rms_after = np.sqrt(np.mean(y_corr**2))
    assert rms_after < rms_before
    assert np.max(np.abs(baseline)) > 0.1


def test_phase_auto_returns_small_angle_on_pure_derivative() -> None:
    x = np.linspace(-5, 5, 1000)
    w = 1.0
    y_deriv = -2 * x / w**2 / (1 + (x / w) ** 2) ** 2
    phi = processing.phase_auto(y_deriv)
    assert abs(np.rad2deg(phi)) < 3.0


def test_integrate_absorption_area_consistency() -> None:
    x = np.linspace(-5, 5, 2000)
    w = 1.0
    y_deriv = -2 * x / w**2 / (1 + (x / w) ** 2) ** 2
    abs1 = processing.integrate_absorption(x, y_deriv)
    area1 = processing.integrate_area(x, abs1)
    abs2 = processing.integrate_absorption(x, 2 * y_deriv)
    area2 = processing.integrate_area(x, abs2)
    assert area1 > 0
    assert pytest.approx(area1 * 2, rel=1e-3) == area2


def test_units_conversions_roundtrip() -> None:
    g = 1234.5
    t = units.g_to_t(g)
    g_back = units.t_to_mt(t) * 10
    assert pytest.approx(g, rel=1e-12) == g_back

    mt = 12.3
    t = units.mt_to_t(mt)
    mt_back = units.t_to_mt(t)
    assert pytest.approx(mt, rel=1e-12) == mt_back

    hz = units.ghz_to_hz(9.5)
    ghz = units.hz_to_ghz(hz)
    assert pytest.approx(9.5, rel=1e-12) == ghz

    mw = 15.0
    w = units.mw_to_w(mw)
    mw_back = units.w_to_mw(w)
    assert pytest.approx(mw, rel=1e-12) == mw_back
