# spectro — plan and progress

A Python tool for analyzing IR spectra: peak detection, peak fitting,
deconvolution of overlapping peaks, and classification of samples by type.

## Decisions so far

| Topic | Decision |
| --- | --- |
| Spectrum type | IR (x = wavenumber in cm⁻¹, y = absorbance or transmittance) |
| File format | Not fixed yet; start with plain delimited text (`load_csv`) |
| Classification target | Sample type: classify whole spectra by what the sample is |
| "Convolution over all peaks" | Parked for now |
| Peak parameters | Center, FWHM, height (what you read off a plot); area is computed analytically |
| Line shapes | Gaussian, Lorentzian, pseudo-Voigt; no true Voigt for now |
| Baseline method | arPLS by default (`lam=1e7` for ~1800 points); beat AsLS on synthetic data, esp. under broad bands |
| Smoothing window | In points, not cm⁻¹; keep below narrowest FWHM ÷ point spacing |
| Preprocessing order | Baseline → smooth → normalise |
| Working style | One step at a time; each step = one module + tests + a demo notebook in `notebooks/`. Next step starts only after review. |

## Libraries

| Need | Library | Added in step |
| --- | --- | --- |
| Arrays, tables, plots | numpy, pandas, matplotlib | 1 |
| Tests | pytest | 1 |
| Demos and visuals | jupyterlab, ipykernel (dev) | 1 |
| Formatting and linting | ruff (dev) | 1 |
| Type checking | pyright (dev) | after 3 |
| Peak finding, smoothing | scipy.signal | 3 |
| Baseline correction | pybaselines | 3 |
| Peak fitting / deconvolution | lmfit | 5 |
| Classification, learning curves | scikit-learn | 7 |

Dependencies are added only when a step's code imports them.

## Build steps

- [x] **1. Project skeleton and `Spectrum` object.** `src/` layout, `Spectrum` dataclass
  (sorted x, validation, `with_y`, `to_absorbance`), `load_csv`, `plot_spectrum`.
  Files: `src/spectro/{spectrum,loaders,plotting}.py`, `tests/test_spectrum.py`,
  `notebooks/01_spectrum_basics.ipynb`
- [x] **2. Synthetic spectrum generator.** Line shapes (Gaussian, Lorentzian,
  pseudo-Voigt) parameterised by center, FWHM and height; `Peak` dataclass with analytic
  `area`; `make_spectrum(peaks, noise, baseline, seed)` returns the spectrum *and* a
  true peak table (`shape, center, fwhm, height, area`), used as ground truth for every
  later step.
  Files: `src/spectro/{lineshapes,synthetic}.py`, `tests/test_synthetic.py`,
  `notebooks/02_synthetic_data.ipynb`
- [x] **3. Preprocessing.** `estimate_baseline` / `remove_baseline` (pybaselines, arPLS
  default), `smooth` (Savitzky–Golay, window in points), `normalize` (max, area, vector,
  SNV). Each records itself in `metadata["preprocessing"]`.
  Files: `src/spectro/preprocessing.py`, `tests/test_preprocessing.py`,
  `notebooks/03_preprocessing.ipynb`
- [ ] **4. Automatic peak detection.** `find_peaks` + `peak_widths` → peak table
  (location, width, height). Tested against step 2's true peaks.
- [ ] **5. Peak fitting.** Fit each peak with an lmfit line shape (Gaussian / Lorentzian
  / Voigt / pseudo-Voigt) → center, FWHM, area, intensity with uncertainties.
- [ ] **6. Deconvolving overlapping peaks.** Fit a sum of peaks over a region, starting
  from step 4 detections; use AIC/BIC to choose the number of peaks. Use synthetic data
  with controlled overlap to find where it breaks down.
- [ ] **7. Classification by sample type.** Features from the peak table or the full
  spectrum (optionally PCA); compare logistic regression, random forest, SVM, gradient
  boosting with cross-validation.
- [ ] **8. How much data do we need?** Synthetic datasets over a grid of sample size ×
  noise × overlap; learning curves for each classifier and for peak-fitting accuracy.
- [ ] **9. Testing on real IR spectra.** Run the whole pipeline on measured spectra,
  where there is no ground truth, and check it against known band assignments instead.
  - *Data:* a small set of public reference spectra of simple compounds with textbook
    bands (e.g. NIST Chemistry WebBook, JCAMP-DX format), kept in `data/real/` with a
    note on source and licence. Swap in the lab's own spectra once their format is known.
  - *Loading:* add `load_jcamp` to `loaders.py`; real files are often in transmittance,
    so this exercises `to_absorbance`.
  - *Checks:* do the preprocessing defaults (arPLS `lam`, smoothing window) still hold at
    real point spacing? Do detected and fitted peaks land on literature positions (e.g.
    acetone C=O near 1715 cm⁻¹) within a stated tolerance? Record where real data
    behaves differently from synthetic (asymmetric bands, water vapour / CO₂ lines,
    saturated peaks).
  - *Classification:* if labelled real spectra exist, rerun the step 7 comparison on them
    and compare with the step 8 learning curves.

  Files: `src/spectro/validation.py` (match a peak table to reference band positions),
  `tests/test_real_data.py` with a small fixture file, `notebooks/09_real_spectra.ipynb`

## Open questions

- Real data file format (vendor files? which instrument?). Step 9 starts with public
  JCAMP-DX spectra so it isn't blocked on this.
- What the sample types / classes are, and roughly how many labelled spectra exist.
- Whether "convolution over all peaks" should come back (whole-spectrum fit vs.
  instrument broadening).

## Log

- **2026-11-09** — Step 1 done. 7 tests passing; demo writes
  `examples/output/01_spectrum_basics.png`.
- **2026-11-09** — Switched demos from example scripts to Jupyter notebooks
  (`notebooks/`); `examples/` removed.
- **2026-11-09** — Added `CLAUDE.md` with the workflow and documentation standard (NumPy
  docstrings). Ruff set up for formatting and linting; existing docstrings converted.
- **2026-11-09** — Step 2 done. 21 tests passing. Random variation and labelled sample
  types deferred to steps 7–8, built on `make_spectrum`.
- **2026-11-09** — Added markdown linting (`pymarkdownlnt`, configured in
  `pyproject.toml`); existing docs fixed to pass. `CLAUDE.md` now lists it as a fourth
  check.
- **2026-11-10** — Step 3 done. 42 tests passing. Switched the baseline default from AsLS
  (as first planned) to arPLS after comparing both against synthetic ground truth. Known
  limit: very broad bands (O–H, ~300 cm⁻¹ FWHM) lose a little height.
- **2026-11-13** — Added step 9: testing the pipeline on real IR spectra (public
  reference spectra first, checked against known band positions).
- **2026-11-13** — Added pyright as a fifth check and fixed the type errors it found.
  `Spectrum` now has a hand-written `__init__` typed `ArrayLike`, so its type hints
  match its docstring; `CLAUDE.md` records the typing rules.
