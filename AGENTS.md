# AGENTS.md

> This document is for both human contributors and AI coding assistants ("agents"). It explains the roles, data contracts, and conventions that ESR‑Lab follows so agents can propose changes that fit the architecture without breaking analysis correctness.

## Project Purpose
A Python toolkit for **Electron Spin Resonance (ESR) data ingestion, processing, analysis, and reporting**. Primary goals:
- Ingest vendor exports (initially **Bruker CSV**), preserve metadata/units.
- Provide reproducible **preprocessing** (baseline/derivative/normalization).
- Perform **feature extraction** (resonance field, g‑factor, linewidth ΔB, area/double integral, peak asymmetry).
- Offer **fitting** (Lorentzian/Voigt/derivative models) with uncertainty estimates.
- Enable **batch pipelines** and a small **GUI/CLI app** for interactive review.
- Generate publishable **figures** and **report artifacts** (tables, JSON summaries).

---
## High‑Level Architecture (Agents)

### 1) IO Agent — `esr_lab.io`
**Responsibility:** File discovery, parsing, and serialization.
- **Bruker CSV reader:**
  - Detects numeric columns (`BField`, unit columns like `[mT]`).
  - Resolves axes: `x = magnetic field (mT or T)`, `y = signal`.
  - Infers **unit hints** and normalizes **field to mT** internally.
  - Captures sweep direction, microwave frequency (GHz), temperature (K) when present.
- **Writers:** CSV/JSON for processed spectra and metrics; minimal sidecar metadata.
- **Contract:** Returns a `Spectrum` dataclass (see Data Contracts) **without mutating raw arrays**.

### 2) Preprocessing Agent — `esr_lab.prep`
**Responsibility:** Deterministic transforms **without changing physics**.
- Baseline removal (polynomial, asymmetric least squares).
- Smoothing (Savitzky–Golay); parameterized and logged.
- Normalization options: `max`, `area`, `zscore` (document which stage uses which).
- First/second derivatives as separate steps; never implicit.

### 3) Feature Agent — `esr_lab.features`
**Responsibility:** Peak detection and descriptive metrics.
- Resonance field `B_res` (from peak/zero‑crossing for derivative spectra).
- Linewidth `ΔBpp` (peak‑to‑peak) and/or `ΔB1/2` (half‑width at half‑max) depending on spectrum type.
- **g‑factor**: `g = h*ν / (μ_B * B_res)`, use microwave frequency `ν` from metadata; default **X‑band 9.4–9.8 GHz** must be explicit if inferred.
- Double integral for spin concentration (if baseline‑removed absorption available).
- Output includes **uncertainty** when possible (propagate from fit covariance).

### 4) Fitting Agent — `esr_lab.fit`
**Responsibility:** Physical model fits.
- Line shapes: Lorentzian, Gaussian, Voigt and their **field derivatives**.
- Multi‑component fits (e.g., overlapping lines) with sensible bounds.
- Returns fit params **with covariance**, fit quality (χ²_red, AIC/BIC), residuals.

### 5) Pipeline Agent — `esr_lab.pipeline`
**Responsibility:** Orchestrate IO → Preprocessing → Features → Fit for **single** or **batch** runs.
- Single entry point `run_pipeline(config, inputs)`.
- Emits an `AnalysisResult` bundle and optionally writes artifacts to `runs/<timestamp>/`.

### 6) App/UX Agent — `esr_lab.app`
**Responsibility:** Launch GUI/CLI, route user actions to pipelines.
- CLI commands: `load`, `preprocess`, `analyze`, `fit`, `report` (idempotent; composable).
- GUI (if enabled): plot raw/processed spectra; allow parameter tweaks with live recompute.
- Never hides transforms—always show a **provenance panel** (what steps, with which params).

### 7) Plotting Agent — `esr_lab.viz`
**Responsibility:** Publication‑quality figures (matplotlib).
- Separate styling from data; **no unit conversion inside plotting**.
- Support derivative/absorption markers: annotate `B_res`, `ΔB`, zero‑crossings.

### 8) Persistence Agent — `esr_lab.store`
**Responsibility:** Result caching and run registries.
- Small SQLite/JSON index of runs; mapping raw file → analysis artifacts and config hash.

---
## Data Contracts

### `Spectrum`
```python
@dataclass
class Spectrum:
    field_mT: np.ndarray   # 1D, strictly increasing; units mT
    signal: np.ndarray     # 1D, same length as field_mT
    dtype: Literal["absorption","derivative"]
    meta: Dict[str, Any]   # {vendor:"Bruker", freq_GHz:float|None, temp_K:float|None, sample:str|None, notes:str|None}
```
**Rules:**
- **Never mutate** `field_mT` in place after creation. Derived arrays → new objects.
- If parser receives Tesla, convert to mT at parse time and set `meta["unit_hint"] = "T->mT"`.

### `AnalysisResult`
```python
@dataclass
class AnalysisResult:
    spectrum: Spectrum
    steps: List[Transform]           # ordered preprocessing records
    features: Dict[str, float]       # {B_res_mT, g, dBpp_mT, area, ...}
    fit: Optional[FitResult]
    artifacts: Dict[str, Path]       # e.g., {"plot_png": ..., "metrics_csv": ...}
```

### `Transform`
Contains `name`, `params`, `version`, and hash for reproducibility.

---
## Conventions
- **Python:** 3.11+
- **Style:** Black + Ruff; type hints required; `from __future__ import annotations`.
- **Errors:** raise domain errors (`ESRDataError`, `UnitError`, `FitConvergenceError`).
- **Logging:** use `logging` with module logger names; default INFO, debug togglable.
- **Determinism:** set RNG seeds for stochastic steps; record library versions in run metadata.
- **Units:** internal field unit is **mT**; frequencies **GHz**; linewidth **mT**; temperature **K**.

---
## Parameter Defaults (Agents SHOULD use, unless user overrides)
- **Preprocessing**
  - Baseline: polynomial order **2** (bounded 1–5), window ≥ 5% span.
  - S-G smoothing: window length odd, ~1–3% of points; polyorder ≤ 3.
  - Normalization: `max` for visualization; `area` when comparing concentrations.
- **Peak/Feature**
  - Min prominence: 3× median absolute deviation of noise.
  - For derivative spectra, `B_res` at **zero‑crossing** closest to max|signal| with sign change.
- **Fitting**
  - Initial guesses from features; bounds enforce physical positivity for widths.

---
## File/Folder Layout
```
esr_lab/
  app/            # CLI/GUI entry points
  io/             # parsers & writers
  prep/           # baseline, smoothing, normalization
  features/       # peak finding & metrics
  fit/            # models & solvers
  viz/            # plotting utilities
  pipeline/       # orchestration
  store/          # run registry / cache
  tests/          # pytest suites
  _version.py

runs/             # analysis outputs (plots, json, logs)
configs/          # pipeline configs (YAML/JSON)
```

---
## CLI Commands (expected behavior)
- `esr analyze <inputs...> [--config configs/x.yml] [--out runs/ts]` → full pipeline.
- `esr preprocess <file> --baseline poly2 --sg 21,3` → emits processed spectrum.
- `esr fit <file> --model voigt --components 2` → fit + params JSON.
- `esr report <run_id>` → assemble figures/CSV summary suitable for papers.

Agents MUST keep commands **idempotent** and **composable** (stdin/stdout friendly where useful).

---
## Testing & Quality Gates
- **pytest** with coverage for IO, prep, features, fit; include regression tests for known datasets.
- Golden‑file tests for plotting (hash on PNG bytes or mpl testing utilities).
- Fast unit tests (<2s each); slower fit tests are marked and optional by default.

---
## Figure Standards
- Axis: field in **mT**; label `B (mT)`; signal in arbitrary units with clear note.
- Derivative spectra must indicate zero‑crossing and ΔBpp visually.
- Save `PNG` (300 DPI) and optional `SVG`; metadata JSON next to images.

---
## Guidelines for AI Agents (Codex, etc.)
1. **Respect data contracts**: never rewrite `Spectrum` arrays in place; produce new instances.
2. **Be explicit with units**: any conversion must be logged and tested.
3. **Surface parameters**: any new knob must be thread through CLI/GUI and config schema.
4. **Do not silently infer microwave frequency**: if missing, annotate that `g` uses default and warn.
5. **Prefer small, pure functions** in `prep/` and `features/`; push state to `pipeline/`.
6. **Document equations** in code comments where physics appears (g‑factor, ΔB, integrals).
7. **Add tests** for each new transform and fit; include one synthetic and one real dataset.
8. **Log provenance**: list transform names + parameters in `AnalysisResult.steps`.
9. **No hidden smoothing** inside fitting; fitting consumes what preprocessing produced.
10. **Performance**: vectorize with NumPy; avoid Python loops in hot paths; profile before adding Numba.

---
## Example: Computing g‑factor (for derivative spectrum)
1. Find zero‑crossing near global extremum.
2. Interpolate to sub‑point precision for `B_res_mT`.
3. `g = (h * ν_GHz * 1e9) / (μ_B * (B_res_mT * 1e-3))`.
4. Report `g ± σ_g` using error propagation from `σ_B` and `σ_ν` if available.

Constants: Planck `h`, Bohr magneton `μ_B` from `scipy.constants`.

---
## Security & Robustness
- Treat input CSVs as untrusted: guard against NaNs, infs, non‑monotonic fields.
- Validate shapes and monotonicity; resample only on explicit request.
- Avoid code execution from metadata; never eval user strings.

---
## Roadmap Hooks (placeholders agents may implement)
- Additional vendor parsers (JEOL, Adani, etc.).
- Temperature‑dependent analysis (Arrhenius‑style plots from series).
- Batch report generator (multi‑sample comparison).
- GUI: draggable markers to pick **Ms/Hc** analogs for VSM mode (if reused), and ΔB gates for ESR.

---
## References
- Poole, *Electron Spin Resonance* (textbook standards for line shapes and g‑factor)
- Weil & Bolton, *Electron Paramagnetic Resonance*

---
## Contact / Ownership
- Maintainer: <your‑name>
- Issues: use GitHub Issues with labels: `io`, `prep`, `features`, `fit`, `viz`, `pipeline`, `app`.

