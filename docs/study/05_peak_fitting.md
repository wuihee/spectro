# Step 5 · Peak fitting

## The idea

Detection reads a peak's center, FWHM and height off a few data points.
Fitting instead picks a line shape (Gaussian, Lorentzian or pseudo-Voigt)
and adjusts its parameters until the curve matches *every* point across the
peak as closely as possible: the **least-squares** fit, which minimises the
sum of squared differences between data and curve. That gives better
values, the area and line shape too, and an **uncertainty** for each.

```text
 corrected ──► smooth ──► detect_peaks ──► starting values
     │                                          │
     └─────────── (unsmoothed!) ──► fit_peaks ◄─┘ ──► table: value ± error for each parameter
```

Two rules shape everything else. Detection gives the starting values,
because the fit only improves on a guess. And the fit runs on the
**unsmoothed** spectrum, because the uncertainties assume each point's noise
is independent of its neighbours', which smoothing breaks.

## Read

1. `src/spectro/fitting.py`: start with `fit_peak` and its `Notes` (what is
   minimised, where the errors come from, why not smoothed data). Then
   `fit_peaks` and its `Notes` (the overlap limit). `peak_model` and
   `peak_params` build the lmfit model and its bounds; step 6 will reuse
   them to add several peaks together.
2. `tests/test_fitting.py`: note `test_errors_match_scatter_over_noise_realisations`,
   which checks the uncertainties themselves, not just the values.
3. `notebooks/05_peak_fitting.ipynb`: run it.

## Key terms

- **Least squares:** choose the parameters that make Σ (data − curve)² as
  small as possible. For peak shapes there's no formula for the answer, so
  the Levenberg–Marquardt algorithm improves a starting guess step by step.
- **Residual:** data minus fitted curve. A good fit leaves residuals that
  look like plain noise; a pattern means the shape or window is wrong.
- **Standard error:** how much a parameter would vary if the measurement
  were repeated with fresh noise. A correct standard error contains the true
  value about 68 % of the time.
- **η (eta):** the Lorentzian fraction of a pseudo-Voigt: 0 is pure
  Gaussian, 1 pure Lorentzian. Fitting it tells you the band's shape.

## Try

- Fit the C=O band with `shape="gaussian"`, `"lorentzian"` and
  `"pseudo_voigt"`. Plot the three residuals. Which shape leaves a pattern?
- Change the starting center by 5, 10 and 20 cm⁻¹. When does the fit stop
  finding the right peak?
- Fit with `window=1`, `2` and `4`. How do the area and its error change,
  and why?
- In notebook part 4, replace `smooth(spectrum)` with
  `smooth(spectrum, window=21)`. What happens to the bias and the coverage?
- Move the two C–H bands apart (2870 → 2800, 2750) and watch the area bias
  shrink. At what separation is fitting them one at a time good enough?

## Design choices

| Choice | Why |
| --- | --- |
| lmfit rather than `scipy.optimize.curve_fit` | Named parameters with bounds, derived parameters (area) with propagated errors, and models that add together, which step 6 needs. It uses SciPy's Levenberg–Marquardt underneath. |
| Our own line shapes, parameterised by center, FWHM and height | The same functions that made the synthetic data, so fitted values compare directly with the true peak table, and a fitted row can be rebuilt as a `Peak`. lmfit's built-in models use amplitude (area) and σ instead. |
| Area as a derived parameter | It is fixed by height, FWHM and η, so it isn't fitted separately, but lmfit still reports its error. |
| Pseudo-Voigt by default, with η free | One model covers Gaussian, Lorentzian and anything between, and η says which. On the notebook spectrum it returns 0 for the Gaussian band and 1 for the Lorentzian one. |
| Straight-line background in each window | Soaks up leftover baseline and the tails of neighbouring peaks, which would otherwise bend the fit. Written around the peak center so its slope and intercept don't trade off. |
| Window ±2 FWHM, cut halfway to neighbours | Wide enough to see the tails that tell the shapes apart; the cut keeps one fit from trying to describe the next peak. |
| Bounds: center inside the window, height ≥ 0, 0 ≤ η ≤ 1 | Keeps the fit physical and stops it wandering onto another peak. |
| Fit unsmoothed data | Tested: on raw data the errors cover the truth 72 % of the time (68 % expected); on smoothed data 1 %, and heights come out 2 % low. |
| Errors scaled by the residuals (lmfit default) | We don't know the noise in advance; the residuals measure it. `rms_residual` is reported so you can compare it with `estimate_noise`. |
| One peak per fit | Simple and enough for isolated bands. Overlapping bands lose area this way; step 6 fits them together. |

## Literature

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Nonlinear least-squares fit of standard profiles | The established way to measure IR band parameters (Maddams, 1980); a recent IR tool fits pseudo-Voigt bands with Levenberg–Marquardt in lmfit, as we do. | Standard. |
| Linear background, physical bounds, visual check of residuals | Maddams names the baseline form as part of the model, and asks that fits be plausible and checked by eye, not only by a statistic. | Standard. |
| Fit unsmoothed data | Smoothing correlates the noise, and fits then underestimate uncertainties; our test shows the same. | Standard, and tested. |
| Errors from the covariance matrix scaled by reduced χ² | lmfit's default when the noise isn't known. Assumes independent noise and a correct model. | Standard, with stated limits. |
| One peak at a time; no true Voigt | Overlapping bands should be fitted together; the Voigt is the physical profile, the pseudo-Voigt an approximation. | Simplifications; step 6 and step 9. |

Full references:
[LITERATURE.md, step 5](../LITERATURE.md#step-5--peak-fitting).

## Check yourself

1. What does a least-squares fit minimise?
2. Why does the fit need starting values, and where do ours come from?
3. Why is the area not a fitted parameter, and how does it still get an
   error?
4. What does η tell you, and what values did the notebook's bands get?
5. Why fit the unsmoothed spectrum when detection uses the smoothed one?
6. What does it mean for a standard error to be "honest", and how does the
   test check it?
7. What is the straight-line background for?
8. The C–H bands come back with too little area, yet their errors are
   small. Why don't the errors warn you?
9. `rms_residual` is much larger than the noise for one peak. What would
   you suspect?

<details>
<summary>Answers</summary>

1. The sum of squared differences between the data and the curve, over the
   points in the window.
2. There's no formula for the best parameters, so the algorithm improves a
   guess step by step, and a bad guess can end on the wrong peak. Ours come
   from `detect_peaks` on the smoothed spectrum.
3. It is fixed by height, FWHM and η (e.g. 1.0645 · h · w for a Gaussian),
   so fitting it too would be redundant. lmfit propagates the errors of the
   parameters it depends on, including how they're correlated.
4. The Lorentzian fraction, i.e. the shape. 0 for the Gaussian O–H band, 1
   for the Lorentzian C–O band, about 0.5 for the pseudo-Voigt C=O band.
5. The errors assume each point's noise is independent. Smoothing averages
   neighbours, so they share noise; the fit then looks more certain than it
   is (errors 2–3× too small), and the smoothed peak is also flatter, so the
   height comes out low.
6. That it matches how much the value really varies with fresh noise, so
   the truth lies within ±1 error about 68 % of the time. The test fits 100
   noise realisations and counts how often that happens.
7. Leftover baseline from step 3 and the tails of nearby peaks add a slowly
   varying offset under the peak. A line absorbs it so the peak parameters
   don't have to.
8. The errors only describe noise, assuming the model is right. Here the
   model is wrong (one peak where there are two, with a window cut off), so
   the values are biased, and the errors can't know that.
9. The shape doesn't fit (wrong line shape, an asymmetric band), or the
   window contains part of another peak. Plot the residual.

</details>

---

[← Step 4](04_peak_detection.md) · [← Study guide](README.md)
