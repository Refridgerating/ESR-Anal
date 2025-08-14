# ESR-Anal (CW-ESR/EPR Analysis GUI)

A fast, lab-friendly, **object-oriented** desktop app for analyzing continuous-wave ESR/EPR data (e.g., Bruker ESR5000 `.csv`). It extracts **g-factors, center field (B₀), linewidths (ΔBₚₚ, FWHM)**, phase, frequency, modulation amplitude, microwave power, **hyperfine constants**, and **spin counts** — with robust pre-processing and **batch** workflows. Includes live, editable plots and publication-quality exports.

## Highlights

- **Import**: Bruker ESR5000 `.csv` (pluggable importers for other formats later)
- **Pre-processing**: baseline (poly/spline), detrend, smoothing, **phase correction** (0–90°), zero-shift, unit conversions
- **Line fitting** (derivative domain): Gaussian, Lorentzian, Voigt (multi-peak capable)
- **Core outputs**: B₀, ΔBₚₚ, FWHM (auto convert), amplitude, **g-factor** (g = hf / μB B₀)
- **Hyperfine**: line spacing → A (mT, MHz); tensor later via simulation plugin
- **Spin quantitation**: **double integration** with **calibration** (e.g., DPPH)
- **Metadata**: read & store frequency, modulation amplitude, microwave power, temperature, phase, instrument info, operator notes
- **Batch processing**: run on folders; per-file reports; **overlay** multiple spectra
- **Graph editing**: draggable baselines, range selectors, markers, peak picking, theme presets; export PNG/SVG/PDF
- **Reproducibility**: project/session files (JSON), per-analysis config, audit trail
- **Extensible**: plugin architecture for importers, fit models, exporters, and simulators
- **Cross-platform**: Windows/macOS/Linux (PySide6 + PyQtGraph)

---

## Quick Start

### Dependencies

- Python ≥ 3.10
- **PySide6** (GUI), **pyqtgraph** (fast plotting), **numpy**, **scipy**, **pandas**
- **lmfit** (robust model fitting), **matplotlib** (exports), **pydantic** (typed configs)
- Optional: **numba** (speedups), **poetry** or **uv** (env management), **pytest** (tests)

```bash
# Option A: pip
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Option B: poetry
poetry install
poetry run esr-lab
