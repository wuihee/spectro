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
| Smoothing window | In points, not cm⁻¹; about 0.7–1 × narrowest FWHM ÷ point spacing (Edwards & Willson 1974 recommend 0.7) |
| Preprocessing order | Baseline → smooth → normalise |
| Peak detection threshold | Prominence ≥ 5 × noise; noise estimated from second differences *before* smoothing, then detect on the smoothed spectrum |
| Peak center | Parabola through the top three points, so not limited to the point spacing |
| Second detection method | Minima of the Savitzky–Golay second derivative (window 11, polyorder 4, prominence ≥ 12 × derivative noise), the standard IR way to find shoulders and overlapping bands. Positions only; misses broad bands and needs low noise |
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
- [x] **4. Automatic peak detection.** `estimate_noise` (robust, from second
  differences), `detect_peaks` (`scipy.signal.find_peaks` with a prominence threshold +
  `peak_widths`) → peak table (`center, fwhm, height, prominence`),
  `detect_peaks_derivative` (second-derivative minima, for shoulders and close overlaps),
  and `match_peaks` to pair a peak table with step 2's true peaks.
  Files: `src/spectro/peaks.py`, `tests/test_peaks.py`, `notebooks/04_peak_detection.ipynb`
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
- **2026-11-13** — Step 4 done. 61 tests passing. Detecting on unsmoothed noisy data gave
  false peaks and split the broad O–H band, so the recommended order is: estimate noise,
  smooth, detect with `prominence=5 * noise`. Over 30 noisy spectra (σ = 0.01) that found
  every peak with no false ones; narrow-peak centers within ~0.5 cm⁻¹, the O–H center
  within ~10 cm⁻¹. Known limits: shoulder peaks come out narrow, and equal peaks closer
  than ~¾ FWHM merge (for step 6).
- **2026-11-13** — Literature check of step 4: local maxima + noise threshold is the
  basic standard; in IR, second-derivative minima are the usual way to find overlapping
  bands (Susi & Byler 1986; Czarnecki 2015 on Savitzky–Golay settings). Added
  `detect_peaks_derivative`. On synthetic data it finds a shoulder with no dip and
  separates equal FWHM-20 peaks 10 cm⁻¹ apart (maxima need 16), but misses the 300 cm⁻¹
  O–H band, and at σ = 0.01 misses most bands. Wavelet (CWT) detection and Fourier
  self-deconvolution were considered and not added: CWT is mainly used for mass spec,
  FSD is parameter-sensitive. From now on each step starts with a literature check
  (rule in `CLAUDE.md`).
- **2026-11-13** — Literature check of steps 1–3, recorded with sources in
  `docs/LITERATURE.md`. All main choices are standard. Deviations: arPLS `lam = 1e7`
  vs. pybaselines' default 1e5 (tuned; recheck in step 9); pseudo-Voigt with one shared
  FWHM and symmetric bands (simplification; check real bands in step 9). Docstrings now
  cite Eilers & Boelens (AsLS), Edwards & Willson (smoothing window), Barnes et al.
  (SNV), Thompson–Cox–Hastings and Ida et al. (pseudo-Voigt) and IUPAC (absorbance).
- **2026-11-15** — Split the study guide into `docs/study/`: a `README.md` with the
  overview, checklist and professor summary, and one file per step named like its
  notebook.
