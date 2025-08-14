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
   
```
## Data Model

### `ESRSpectrum`

- **Fields**: `field_B` (1D ndarray, T), `signal_dAbs` (derivative), optional `absorption` (computed), `mask`
- **Metadata** (`ESRMeta`): `frequency_Hz`, `mod_amp_T`, `mw_power_W`, `temperature_K`, `phase_rad`, `instrument`, `operator`, `notes`, `timestamp`
- **Methods**:
  - `from_bruker_csv(path) -> ESRSpectrum`
  - `baseline(method="poly"|"spline", order=2, knots=None)`
  - `smooth(method="savgol", window, polyorder)`
  - `phase_correct(delta_rad)` (or optimize)
  - `to_absorption()` (integrate derivative once)
  - `to_area()` (double integrate with background control)
  - `subset(Bmin, Bmax)` (ROI for fitting)
  - `export_results()` (dict/json)

---

## Bruker ESR5000 CSV Parsing

- **Header detection**: scan top lines for key tokens:
  - `Frequency` (GHz)
  - `Modulation` (G or mT)
  - `Microwave Power` (mW)
  - `Temperature` (K)
  - `Phase` (deg)
- **Data**: columns like `Field(G)` or `Field(mT)`, `Signal (dAbs)`
- **Unit normalization**: convert to **Tesla** for fields, **Hz** for frequency, **W** for power; store raw header for audit

---

## Analysis Pipeline

1. **Load** → parse metadata; normalize units  
2. **Pre-process**
   - Baseline: polynomial (order 0–3) or spline (draggable anchors)
   - Phase: slider + “auto” (minimize dispersive residual)
   - Smoothing: Savitzky–Golay, optional downsample
   - Range select (exclude artefacts)
3. **Fit (derivative domain)**
   - Model: Gaussian | Lorentzian | Voigt | Multi-peak
   - Params: B₀, ΔBₚₚ, amplitude, phase fraction
   - Conversions:
     - Lorentzian: ΔB₁/₂ = √3 × ΔBₚₚ
     - Gaussian: ΔB₁/₂ = 1.177 × ΔBₚₚ
4. **Physics**
   - g-factor: g = hf / μB B₀
   - Hyperfine: peak-to-peak spacing → A (mT, MHz)
   - T₂ (only if Lorentzian/homogeneous): ΔB₁/₂ = 1/(γT₂)
5. **Quantitation**
   - Double integration → relative spins
   - Calibrate vs standard (DPPH)
6. **Report**
   - Per-spectrum JSON/CSV
   - Figure exports (PNG/SVG/PDF)

---

## GUI Overview

- **Plot Canvas** (pyqtgraph): fast pan/zoom; overlay many spectra
- **Graph Editing**:
  - Draggable baselines
  - Range selector for ROI fitting
  - Peak markers, label editor
- **Panels**:
  - Import
  - Pre-process
  - Fit
  - Physics
  - Quant
  - Batch
- **Sessions**: save/load `.esrproj.json`

---

## Programmatic API

```python
from esr_lab.core.spectrum import ESRSpectrum
from esr_lab.core.fitting import FitModel
from esr_lab.core.physics import g_factor

sp = ESRSpectrum.from_bruker_csv("data/examples/sample.csv")
sp.baseline(method="poly", order=2).phase_correct(0.05).smooth("savgol", window=11, polyorder=3)

model = FitModel.voigt(initial={"B0_T": 0.339, "dBpp_T": 0.0015, "amp": 1.0})
fit = model.fit(sp, roi=(0.33, 0.35))

B0 = fit.params["B0_T"].value
g  = g_factor(frequency_Hz=sp.meta.frequency_Hz, B0_T=B0)

results = {
    "B0_T": B0,
    "FWHM_T": fit.to_fwhm(),
    "g": g,
    **fit.stats()
}
```
## Batch Processing

- Select a folder or multiple files
- Choose a saved pipeline preset (JSON)
- Outputs:
  - `batch_results.csv`
  - Per-file JSON with full fit parameters and stats
  - Combined overlay figure for visual comparison

---

## Accuracy & QA

- **Field calibration**: verify against DPPH line (g = 2.0036) to ensure correct field scaling
- **Power/modulation checks**: automatic warnings if the spectrum shows signs of saturation or over-modulation
- **Unit tests** (in `tests/`):
  - CSV parser correctly interprets and converts field units
  - ΔBₚₚ ↔ FWHM conversions for Gaussian/Lorentzian models
  - g-factor calculations match known standards
  - Double integration remains stable under baseline variations
  - Session save/load reproduces identical results

---

## Extensibility & Plugins

- **Importers**: add `io/*.py` modules implementing `can_load()` and `load()` hooks for new file formats
- **Models**: register new fit model classes in `core/fitting.py`
- **Exporters**: add custom formats (e.g., MATLAB `.mat`, Origin `.opj`) in `io/exporters.py`
- **Simulations**: placeholder `plugins/` for adding g-tensor/hyperfine simulation capabilities

---

## CLI (Optional)

```bash
# Fit one file
esr-lab fit sample.csv --model voigt --roi 0.33 0.35 --phase-auto --baseline poly2

# Batch process a folder
esr-lab batch ./runs/2025-08-14 --preset configs/xband_voigt.json --export ./out
```
## Configuration

- **Global defaults**: Stored in `configs/defaults.json` — contains plot styles, unit preferences, and export settings.
- **Presets**: Pre-defined analysis pipelines (e.g., "X-band organic radical", "powder oxide sample") that bundle preprocessing, fitting, and reporting settings.
- **Per-session**: `.esrproj.json` bundles file paths, all analysis parameters, and results to ensure experiments are 100% reproducible.

---

## Contributing

Pull requests are welcome! Please follow these steps:

1. **File an Issue** describing the bug or feature request.
2. **Add or extend unit tests** in `tests/` for your changes.
3. Maintain **module boundaries** — keep GUI logic separate from core computation and data handling.
4. Run:

```bash
pytest -q
```

## Appendix: Key Equations

- g-factor:  
  g = (h * f) / (μB * B0)

- Lorentzian linewidth conversion:  
  ΔB_1/2 = sqrt(3) * ΔB_pp

- Gaussian linewidth conversion:  
  ΔB_1/2 = 1.177 * ΔB_pp

- Hyperfine spacing:  
  A [MHz] ≈ g * (28.02495) * ΔB [mT]

- Relation to T2 (homogeneous limit):  
  ΔB_1/2 = 1 / (γ * T2)  
  γ = (g * μB) / ħ


License
MIT license
