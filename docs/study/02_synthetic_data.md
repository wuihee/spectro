# Step 2 · Synthetic spectra

## The idea

We describe a spectrum as a **list of peaks** (each with a center, width,
height and shape), add them together, then add a baseline and noise. Because
we built it, we know the true peaks exactly, and we keep them in a table.
That table is the "answer key" for testing every later step.

```text
   [Peak, Peak, Peak]  ──►  sum of curves  ──►  + baseline  ──►  + noise  ──►  Spectrum
          │
          └────────────────────────────────────────────────────────────────►  true_peaks table
```

## Read

1. `src/spectro/lineshapes.py`: three functions. Look at the formulas in the
   `Notes` sections; don't worry about deriving them.
2. `src/spectro/synthetic.py`: `Peak` (a description of one peak) and
   `make_spectrum` (builds the spectrum and the answer key).
3. `notebooks/02_synthetic_data.ipynb`: run it.

## Line shapes in one picture

All three shapes in notebook 2, section 1, have the **same center, height
and FWHM**. They differ only in their **tails**:

- **Gaussian:** tails die off fast. Comes from disorder: many slightly
  different environments for the same bond (common in solids).
- **Lorentzian:** long tails. The natural shape of a single vibration
  (lifetime broadening; common in liquids and gases).
- **Pseudo-Voigt:** a weighted mix of the two (`eta` = Lorentzian
  fraction). Real IR bands usually have both effects, so this is the usual
  choice.

Because the tails differ, the **areas differ** even when height and width
match: Lorentzian area ≈ 1.5 × Gaussian area.

## Try

- Change `eta` from 0 to 1 on a pseudo-Voigt peak and watch the tails change.
- Move two peaks closer together until you can no longer see two bumps. (This
  is the problem step 6 solves.)
- Increase `noise` until a small peak disappears into it. (This matters for
  step 4.)
- Build the same spectrum twice with the same `seed`, then with different
  seeds. What changes?
- Compare `peak.area` with `np.trapezoid(peak.evaluate(x), x)` for a
  Lorentzian over a narrow x range. Why don't they match?

## Design choices

| Choice | Why |
| --- | --- |
| Build synthetic data *before* any analysis | It gives us ground truth. Without it, we can't measure whether peak detection or fitting is accurate. |
| `make_spectrum` returns the spectrum **and** the true peak table | The answer key travels with the data. Later steps output tables with the same columns, so comparison is row by row. |
| Describe peaks by center, FWHM, height | These are what you read off a plot, so peak lists are easy to write and check. Area is derived with an exact formula. |
| Three line shapes, pseudo-Voigt by default | Covers the physically relevant cases. Pseudo-Voigt is the standard approximation for IR and needs no extra library. |
| Baseline as polynomial on x rescaled to 0–1 | Coefficients are in absorbance units ("rises by 0.1 across the spectrum"), regardless of the x range. |
| Noise with a `seed` | Experiments are reproducible: the same seed gives the same spectrum. |
| No random variation or sample classes yet | Kept for steps 7–8. Step 2 only needs to make one spectrum well. |

## Literature

Testing methods on simulated spectra with known peaks is standard practice
in method papers. Gaussian–Lorentzian mixtures are the usual IR band
shapes. Two simplifications: our pseudo-Voigt shares one FWHM between its
parts (the Thompson–Cox–Hastings version derives it from a true Voigt), and
all bands are symmetric, while real condensed-phase bands can be skewed.
Details and sources:
[LITERATURE.md, step 2](../LITERATURE.md#step-2--synthetic-spectra).

## Check yourself

1. Why build a synthetic generator before building peak detection?
2. What's in the `true_peaks` table, and how will later steps use it?
3. Two peaks have the same height and FWHM, one Gaussian and one Lorentzian.
   Which has more area, and why?
4. What does `eta` control?
5. Why might a fitted Lorentzian's area come out smaller than the true area
   if the peak is near the edge of the spectrum?
6. Why does `make_spectrum` take a `seed`?

<details>
<summary>Answers</summary>

1. To have ground truth. With real data we don't know the correct peaks, so
   we can't tell whether a detector or fitter is right. With synthetic data
   we compare its output against the known answer.
2. One row per peak: shape, center, FWHM, height, area. Steps 4 and 5 will
   output tables with the same columns, so we can measure their errors
   directly (e.g. how far off is each detected center?).
3. The Lorentzian, about 1.5×, because its long tails hold area that the
   Gaussian's tails don't.
4. The mix between Lorentzian and Gaussian in a pseudo-Voigt: 0 is pure
   Gaussian, 1 is pure Lorentzian.
5. Part of its long tail lies outside the measured x range, so that area is
   missing from the data.
6. So results are reproducible: the same seed gives exactly the same noise,
   which makes tests and experiments repeatable.

</details>

---

[← Step 1](01_spectrum.md) · [← Study guide](README.md) · [Step 3 →](03_preprocessing.md)
