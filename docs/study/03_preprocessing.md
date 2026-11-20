# Preprocessing

## The idea

A measured spectrum is **peaks + baseline + noise**, and only the peaks carry
chemistry. Preprocessing strips off the other two, then puts samples on a
common scale. Each operation is a small function that takes a `Spectrum` and
returns a new one, so they chain:

```text
 raw ──► remove_baseline ──► smooth ──► normalize ──► ready for peak detection / features
         (drift away)        (noise down)  (scale removed)
```

Because the synthetic generator lets us build the same spectrum with and
without baseline and noise, every function is tested by asking: *does it give
back the clean spectrum?*

## Read

1. `src/spectro/preprocessing.py`: four public functions. Read the `Notes`
   of `estimate_baseline` and `smooth`; they hold the science. Then look at
   `_record`, which keeps the processing history.
2. `tests/test_preprocessing.py`: see how each test builds a "raw" and a
   "clean" spectrum from the same peaks and compares them.
3. `notebooks/03_preprocessing.ipynb`: run it.

## Try

- Call `remove_baseline(raw, lam=1e4)` and `lam=1e10`. Which one eats into
  the peaks, and which one can't bend enough to follow the drift?
- Compare `remove_baseline(raw, "asls")` with the default `"arpls"` on the
  notebook spectrum. Look at the O–H band near 3350 cm⁻¹.
- Smooth the C=O peak with `window=5, 11, 21, 41` and print `y.max()` each
  time. At roughly what window does the height start to drop?
- Try `polyorder=2` versus `polyorder=4` with the same window.
- Print `metadata["preprocessing"]` after a chain of calls, and check that
  the input's metadata didn't change.

## Design choices

| Choice | Why |
| --- | --- |
| Separate small functions, not one `preprocess()` | Each function can be swapped, skipped or reordered, and tested on its own. Plain function calls chain clearly enough; a pipeline helper can come later if needed. |
| arPLS as the default baseline (via pybaselines) | On our synthetic spectra it got back the true baseline best at every noise level. AsLS (the classic choice) sits below the true baseline when there is noise and rides up under the broad O–H band. Other pybaselines methods are one argument away. |
| `estimate_baseline` is public | So you can plot the baseline over the raw spectrum and check it by eye, which is how baseline correction is judged on real data. |
| `lam` default of 1e7, tuned on 1801 points | `lam` is a stiffness penalty whose effect depends on how many points there are. A fixed, documented default is simpler than auto-scaling; change it for very different data. |
| Savitzky–Golay smoothing | It fits a local polynomial, so it keeps peak height and width far better than a moving average for the same noise reduction. |
| Smoothing window in **points**, not cm⁻¹ | That's what the filter actually uses and it doesn't assume evenly spaced data. The docstring says how to convert: keep it below FWHM ÷ point spacing. |
| Four normalisations | "max" for plotting, "area" and "vector" for comparing samples, "snv" for classification. |
| `y_unit` records the normalisation | "absorbance (max-normalized)" stops a normalised spectrum from being mistaken for real absorbance, and the plot label says so. |
| History in `metadata["preprocessing"]` | A processed spectrum says how it was made, which matters when comparing results later. |
| Order: baseline → smooth → normalise | Normalising first divides by a value that includes the baseline, so identical samples with different backgrounds end up at different scales (notebook part 4). |

## Literature

All four techniques are standard. arPLS beat AsLS in its original paper,
as in our own tests. Our `lam = 1e7` is higher than pybaselines' default of
1e5; it was tuned on our grid and still needs rechecking on real data.
Edwards and Willson recommend a smoothing window of about 0.7 × the
narrowest FWHM, close to our default (0.8). Normalising last is the
consensus; whether to smooth before or after baseline removal varies
between sources. Details and sources:
[LITERATURE.md, Preprocessing](../LITERATURE.md#preprocessing).

## Check yourself

1. What three things add up to a measured spectrum, and which one do we
   want?
2. In arPLS, what does `lam` control, and what goes wrong if it's too small
   or too large?
3. Why does the baseline fit follow the bottom of the spectrum instead of
   going through the peaks?
4. Why is the broad O–H band the hardest case for baseline removal?
5. Why Savitzky–Golay rather than a moving average?
6. What is the rule of thumb for choosing the smoothing window?
7. Why must the baseline be removed before normalising?
8. Why is the smoothing window in points rather than cm⁻¹?

<details>
<summary>Answers</summary>

1. Peaks + baseline + noise. We want the peaks; baseline and noise are
   removed.
2. Stiffness: how much the fitted curve is allowed to bend. Too small and it
   bends up into the peaks, cutting them down; too large and it can't follow
   real curvature in the drift.
3. Points far above the current curve get almost no weight in the next
   iteration, so peaks stop pulling it up, while points within the noise
   keep full weight.
4. It is 300 cm⁻¹ wide, so it starts to look like slow background drift. The
   method can't fully tell them apart, and the band loses a little height.
5. It fits a polynomial in each window, which follows the curved top of a
   peak; an average just blurs it, lowering the height and widening it.
6. Keep the window (in points) below the narrowest FWHM divided by the
   point spacing; Edwards and Willson recommend about 0.7 × FWHM. At 2 cm⁻¹
   spacing and a 25 cm⁻¹ peak, that's about 9–12 points; 11 is the default.
7. Normalising divides by something (max, area, norm) that includes the
   baseline, so two identical samples with different backgrounds get
   different scales, and subtracting the baseline afterwards can't undo it.
8. The filter works on points, and a cm⁻¹ window assumes evenly spaced data,
   which real files may not have.

</details>

---

[← Synthetic spectra](02_synthetic_data.md) · [← Study guide](README.md) ·
[Peak detection →](04_peak_detection.md)
