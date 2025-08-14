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
```
Run
```
python -m esr_lab.app
# or, once packaged:
esr-lab
```
Repository Structure
```
esr-lab/
├─ README.md
├─ LICENSE
├─ pyproject.toml               # or requirements.txt + setup.cfg
├─ data/
│  ├─ examples/                 # sample Bruker ESR5000 CSVs (anonymized)
│  └─ standards/                # DPPH etc. for calibration
├─ src/
│  └─ esr_lab/
│     ├─ app.py                 # GUI entry-point (PySide6)
│     ├─ core/
│     │  ├─ spectrum.py         # ESRSpectrum (data+metadata+units)
│     │  ├─ metadata.py         # Pydantic models for frequency, power, etc.
│     │  ├─ processing.py       # baseline/phase/smoothing/filters
│     │  ├─ fitting.py          # models: Gauss/Lorentz/Voigt (+multi-peak)
│     │  ├─ physics.py          # g-factor, A-constants, T2 (when valid)
│     │  ├─ quant.py            # double integration, calibration, spin counts
│     │  ├─ reporting.py        # tabular + JSON reports
│     │  └─ units.py            # conversions (mT/T, GHz/Hz, etc.)
│     ├─ io/
│     │  ├─ loader.py           # dispatch by filetype
│     │  ├─ bruker_csv.py       # Bruker ESR5000 CSV parser
│     │  └─ exporters.py        # csv/json; figure exports
│     ├─ gui/
│     │  ├─ main_window.py
│     │  ├─ plot_view.py        # pyqtgraph canvas + editors
│     │  ├─ panels/
│     │  │  ├─ import_panel.py
│     │  │  ├─ preprocess_panel.py
│     │  │  ├─ fit_panel.py
│     │  │  ├─ hyperfine_panel.py
│     │  │  ├─ quant_panel.py
│     │  │  └─ batch_panel.py
│     │  └─ styles/
│     ├─ plugins/               # future: simulators, alt importers, etc.
│     └─ utils/
│        ├─ logging.py
│        ├─ caching.py
│        └─ theme.py
├─ tests/
│  ├─ test_parsers.py
│  ├─ test_processing.py
│  ├─ test_fitting.py
│  ├─ test_physics.py
│  └─ data/                     # small golden datasets
└─ docs/
   ├─ user-guide.md
   └─ dev-notes.md
   
