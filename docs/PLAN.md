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
| Peak fitting | One pseudo-Voigt (or Gaussian / Lorentzian) + straight-line background per peak, in a ±2 FWHM window cut halfway to neighbours; starting values from detection |
| Data to fit | The baseline-corrected but **unsmoothed** spectrum: smoothing makes the standard errors far too small and biases heights low |
| Uncertainties | lmfit standard errors (covariance scaled by reduced χ²); they cover noise only, not a wrong model |
| Overlapping peaks | Fitted together as a sum of line shapes + one straight-line background per region; a region is a chain of peaks whose ±2 FWHM spans overlap |
| Number of peaks | Fit 1 … (detected + 1) peaks per region and keep the lowest **BIC** (AIC available); extra peaks start at the largest residual bump or by splitting a peak, best χ² wins |
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
| Web app | streamlit | 10 |

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
- [x] **5. Peak fitting.** `peak_model` / `peak_params` (lmfit models parameterised like
  `Peak`, with a derived `area`), `fit_peak` (one peak + linear background in a window)
  and `fit_peaks` (every row of a detection table) → table of center, FWHM, height,
  area and η, each with a standard error, plus the RMS residual.
  Files: `src/spectro/fitting.py`, `tests/test_fitting.py`,
  `notebooks/05_peak_fitting.ipynb`
- [x] **6. Deconvolving overlapping peaks.** `find_regions` (group overlapping peaks),
  `fit_region` (sum of peaks + linear background), `fit_table`, `compare_peak_counts`
  (AIC/BIC for 1, 2, … peaks) and `deconvolve` (all regions, lowest BIC) → the step 5
  table plus ``region``. Breakdown measured on synthetic pairs with controlled overlap.
  Files: `src/spectro/deconvolution.py`, `tests/test_deconvolution.py`,
  `notebooks/06_deconvolution.ipynb`
- [ ] **7. Classification by sample type.** Features from the peak table or the full
  spectrum (optionally PCA); compare logistic regression, random forest, SVM, gradient
  boosting with cross-validation.
  - *Preprocessing as settings:* wrap the preprocessing steps as scikit-learn pipeline
    stages, so a small menu of sensible options (baseline method, smoothing window,
    normalisation, peak-table vs. whole-spectrum features) is chosen by the search like
    any other setting. Use nested cross-validation so the reported score isn't inflated
    by the choice. Keep the menu small: each option costs data (step 8) and run time.
  - *Two criteria:* the ML chooses settings for accuracy; peak parameters reported as
    results (areas, positions) are still judged by synthetic ground truth, since a
    setting can help classification while giving physically wrong peaks.
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
- [ ] **10. Web app for the research group.** A Streamlit app, a thin layer over
  `spectro` so the library stays the single source of truth. Comes after step 9, so
  the upload page can read the group's real files.
  - *Workflow:* upload a spectrum (`load_csv`, `load_jcamp`) → preprocess, with
    sliders for arPLS `lam`, smoothing window and normalisation, plotting the
    estimated baseline over the raw data → detect (prominence in multiples of the
    noise; maxima or second-derivative method) → fit (value ± error table and
    residual plot) → download the peak table as CSV with the settings from
    ``metadata["preprocessing"]``.
  - *Hosting:* if lab spectra are unpublished, host inside the university (department
    server or lab machine) so data stays on the network. Streamlit Community Cloud or
    Hugging Face Spaces only for public or synthetic data; check Python 3.14 support.
  - *Optional:* a docs site built from the NumPy docstrings (MkDocs + mkdocstrings, or
    Sphinx + numpydoc), with the study guide and `LITERATURE.md` as pages.
  - *Tests:* keep logic in small helper functions (e.g. building the CSV export) and
    test those; the Streamlit script itself only wires widgets to them.

  Files: `app/streamlit_app.py`, a helper module (e.g. `src/spectro/report.py`),
  `tests/test_app.py`

## Follow-ups

Found while building steps 1–6; not scheduled yet. Each is a short side step: measure
on synthetic data first, check the literature, then change the default.

- **Baseline on noisy spectra (step 3).** At σ = 0.01 arPLS leaves a curved dip of up
  to ~0.045 under the broad O–H band and sits ~0.012 high on average; in step 6 this
  becomes a spurious wide component that takes 9–22 % of the C–H areas.
  1. Diagnose: baseline error against the true baseline over noise level × `lam` ×
     band width, to find whether stiffness or noise causes it.
  2. Compare fixes, scored by baseline error and by the step 6 result: retune `lam`;
     smooth before the baseline (LITERATURE.md deviation 4); other pybaselines
     methods (literature check first); a curved background per region in step 6.
  3. Update the default, tests and `LITERATURE.md`; rerun notebooks 03–06.
  4. Confirm on real spectra in step 9 before settling, as our synthetic baseline is
     a simple polynomial.
- **Choosing the number of peaks (step 6).** Literature-backed tweaks to cut false
  peaks: require a BIC margin before adding a peak (e.g. ΔBIC > 6, "strong" on Kass
  and Raftery's scale) instead of the plain minimum; reject added peaks whose
  uncertainties are very large; try starting values from `detect_peaks_derivative`,
  the usual IR source of candidate bands.

## Open questions

- Real data file format (vendor files? which instrument?). Step 9 starts with public
  JCAMP-DX spectra so it isn't blocked on this.
- What the sample types / classes are, and roughly how many labelled spectra exist.
- Whether "convolution over all peaks" should come back (whole-spectrum fit vs.
  instrument broadening).
- Web app (step 10): who will use it, and do they want only peak tables or also to
  tune settings? Can lab data leave the university network? What does the
  department offer for hosting?

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
- **2026-11-15** — Step 5 done. 73 tests passing. Added lmfit. Literature check first:
  nonlinear least squares with standard profiles is the standard (Maddams 1980). On
  the noisy synthetic spectrum the isolated bands come back within ~3 % in area and η
  identifies their shape (0 Gaussian, 1 Lorentzian). Fitting the smoothed spectrum was
  tested and rejected: standard errors covered the truth 1 % of the time instead of
  ~68 %, and heights came out ~2 % low. Known limit: the overlapping C–H pair loses
  7–30 % of its area when fitted one peak at a time (for step 6). True Voigt not added.
- **2026-11-16** — Added step 10: a Streamlit web app for the research group, after
  step 9 so it can load real files. Hosting depends on whether lab data may leave the
  university network.
- **2026-11-18** — Step 6 done. 84 tests passing. Literature check first: fitting the
  whole envelope is standard (Maddams 1980; Vandeginste & De Galan 1975), and AIC/BIC
  are the standard way to choose the number of components (BIC used for peak counts by
  Shinotsuka et al. 2020). Joint fitting brings the C–H pair's areas from ~20 % low to
  within 3 %, and its errors cover the truth 70–75 % of the time. Starting extra peaks
  only from the residual got stuck on merged pairs (area errors ~90 %); also trying a
  split of each peak fixed it. Two equal FWHM-20 bands are resolved every time from
  0.6 FWHM apart at SNR 50 and 0.4 FWHM at SNR 250 (detection alone: ~¾–1 FWHM); at
  1.5 FWHM one draw in ten got a spurious third peak. BIC chosen over AIC: AIC added a
  non-existent peak on a noisy spectrum. Known limit: at σ = 0.01 arPLS leaves a curved
  dip of up to ~0.045 under the O–H band; the region's straight-line background can't
  follow it, so BIC adds a wide spurious component that takes 9–22 % of the C–H areas.
  Follow-up for step 3 / step 9 (baseline on noisy data, or a curved region background).
- **2026-11-18** — Added a Follow-ups section: fix baseline removal on noisy spectra
  (step 3) and tighten the choice of peak count (step 6), both unscheduled. Step 7 now
  plans to treat preprocessing options as pipeline settings chosen by nested
  cross-validation, while peak parameters stay judged by ground truth.
