# Study guide

A guide to understanding what has been built so far, why it was built that
way, and how to explain it. Each step has:

- **The idea:** the mental model in a few sentences.
- **Read:** the files to look at, in order.
- **Try:** small experiments to run in a notebook.
- **Design choices:** what was decided and the one-line reason, which is
  what your professor is most likely to ask about.
- **Check yourself:** questions to answer out loud before moving on.
  Answers are folded underneath; try first.

Don't try to memorise the code. Aim to be able to explain *what each piece is
for* and *why it is shaped the way it is*.

---

## The big picture

The project goal: take IR spectra, find and measure their peaks (including
overlapping ones), and classify samples by type. Then find out how much data
that needs.

The whole project is a pipeline, where each step takes the output of the one
before:

```text
 file / synthetic ──► Spectrum ──► preprocess ──► detect peaks ──► fit peaks ──► features ──► classify
     (1, 2)            (1)            (3)             (4)           (5, 6)          (7)          (7, 8)
```

Two ideas hold it together:

1. **One data type.** Every step takes and returns a `Spectrum`. Nothing
   downstream needs to know where the data came from.
2. **Ground truth from synthetic data.** With real data we never know the
   "right" peaks, so we can't tell if a method works. With synthetic data we
   do, so every later step is tested by asking: *did it recover the peaks we
   put in?*

If you can draw this pipeline and explain those two ideas, you understand the
architecture.

---

## Background science (just enough)

| Term | What it means here |
| --- | --- |
| **Wavenumber (cm⁻¹)** | The x-axis of an IR spectrum: 1 / wavelength. Higher = more energetic vibration. IR plots run from ~4000 on the left to ~400 on the right, by convention. |
| **Transmittance (T, %T)** | Fraction of light that gets through the sample. Peaks point *down*. Often what the instrument exports. |
| **Absorbance (A)** | A = −log₁₀(T). Peaks point *up*. |
| **Beer–Lambert law** | A = ε · c · l: absorbance is proportional to concentration. This is why we analyse in absorbance, not transmittance. |
| **Band / peak** | A bump in the spectrum from one molecular vibration (e.g. C=O stretch near 1715 cm⁻¹). |
| **Center, height, FWHM, area** | Where the peak is, how tall, how wide at half its height, and the total area under it. Area tracks the *amount* of that bond. |
| **Line shape** | The mathematical curve of a single peak: Gaussian, Lorentzian, or a mix. |

---

## Step 1 · The `Spectrum` object

### The idea

A spectrum is just two arrays (x and y) plus units. `Spectrum` wraps them in
one object that **guarantees they are valid**, so no other code has to check.
It's the "contract" every other module relies on.

### Read

1. `src/spectro/spectrum.py`: the dataclass. Focus on `__init__` (what is
   guaranteed) and `with_y` (how changes are made).
2. `src/spectro/plotting.py`: short; note the inverted x-axis.
3. `src/spectro/loaders.py`: skim. Just know it turns a text file into a
   `Spectrum`.
4. `notebooks/01_spectrum_basics.ipynb`: run it.

### Try

- Create a spectrum with `x` in *decreasing* order and print `s.x`. What
  happened?
- Create one with mismatched lengths and read the error.
- Make a copy with `s.with_y(s.y * 2)` and check that `s.y` didn't change.
- Make a `%transmittance` spectrum, call `.to_absorbance()`, and plot both.
  Which way do the peaks point in each?

### Design choices

| Choice | Why |
| --- | --- |
| One `Spectrum` dataclass used everywhere | Every step speaks the same language; steps can be swapped or chained freely. |
| Sort by x and validate on creation | Check once at the door, so later code (peak finding, integration) can assume clean, ascending data. Bad files fail immediately, with a clear message. |
| Hand-written `__init__` on a dataclass | Callers may pass lists or arrays (`ArrayLike`), but the stored fields are always float arrays (`np.ndarray`). The dataclass-generated `__init__` can't type the two differently, so the type checker would reject `Spectrum(x=[1, 2], ...)`. |
| Never modify in place; return a new spectrum (`with_y`) | You can always compare before and after a processing step, and a bug in one step can't silently corrupt data used elsewhere. |
| Convert to absorbance | Only absorbance is proportional to concentration (Beer–Lambert), so areas and classification features are meaningful. |
| Plain CSV loader for now | No file format is fixed yet. New formats can be added as new loader functions without touching anything else, because they all return a `Spectrum`. |

### Literature

Standard. IUPAC defines absorbance as log₁₀(P₀/P) and states the Beer–Lambert
law in absorbance, which is why we convert. JCAMP-DX, planned for step 9, is
the IUPAC standard file format for IR spectra. Details and sources:
[LITERATURE.md, step 1](LITERATURE.md#step-1--the-spectrum-object).

### Check yourself

1. Why does `Spectrum` sort points by wavenumber?
2. What could go wrong if processing functions modified the spectrum in
   place?
3. Why do we work in absorbance rather than transmittance?
4. If we get data in a new vendor format next month, what needs to change?

<details>
<summary>Answers</summary>

1. Instruments often export from high to low wavenumber. Sorting once means
   every later step can assume ascending x (needed for things like
   integration and peak widths) without checking.
2. You'd lose the original, so you can't compare before/after, and if two
   parts of the code share the same spectrum, one step could silently change
   the other's data.
3. Beer–Lambert: absorbance is proportional to concentration, so peak heights
   and areas reflect how much of something is there. Transmittance is not
   linear in concentration.
4. Only a new loader function that returns a `Spectrum`. Nothing downstream
   changes.

</details>

---

## Step 2 · Synthetic spectra

### The idea

We describe a spectrum as a **list of peaks** (each with a center, width,
height and shape), add them together, then add a baseline and noise. Because
we built it, we know the true peaks exactly, and we keep them in a table.
That table is the "answer key" for testing every later step.

```text
   [Peak, Peak, Peak]  ──►  sum of curves  ──►  + baseline  ──►  + noise  ──►  Spectrum
          │
          └────────────────────────────────────────────────────────────────►  true_peaks table
```

### Read

1. `src/spectro/lineshapes.py`: three functions. Look at the formulas in the
   `Notes` sections; don't worry about deriving them.
2. `src/spectro/synthetic.py`: `Peak` (a description of one peak) and
   `make_spectrum` (builds the spectrum and the answer key).
3. `notebooks/02_synthetic_data.ipynb`: run it.

### Line shapes in one picture

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

### Try

- Change `eta` from 0 to 1 on a pseudo-Voigt peak and watch the tails change.
- Move two peaks closer together until you can no longer see two bumps. (This
  is the problem step 6 solves.)
- Increase `noise` until a small peak disappears into it. (This matters for
  step 4.)
- Build the same spectrum twice with the same `seed`, then with different
  seeds. What changes?
- Compare `peak.area` with `np.trapezoid(peak.evaluate(x), x)` for a
  Lorentzian over a narrow x range. Why don't they match?

### Design choices

| Choice | Why |
| --- | --- |
| Build synthetic data *before* any analysis | It gives us ground truth. Without it, we can't measure whether peak detection or fitting is accurate. |
| `make_spectrum` returns the spectrum **and** the true peak table | The answer key travels with the data. Later steps output tables with the same columns, so comparison is row by row. |
| Describe peaks by center, FWHM, height | These are what you read off a plot, so peak lists are easy to write and check. Area is derived with an exact formula. |
| Three line shapes, pseudo-Voigt by default | Covers the physically relevant cases. Pseudo-Voigt is the standard approximation for IR and needs no extra library. |
| Baseline as polynomial on x rescaled to 0–1 | Coefficients are in absorbance units ("rises by 0.1 across the spectrum"), regardless of the x range. |
| Noise with a `seed` | Experiments are reproducible: the same seed gives the same spectrum. |
| No random variation or sample classes yet | Kept for steps 7–8. Step 2 only needs to make one spectrum well. |

### Literature

Testing methods on simulated spectra with known peaks is standard practice
in method papers. Gaussian–Lorentzian mixtures are the usual IR band
shapes. Two simplifications: our pseudo-Voigt shares one FWHM between its
parts (the Thompson–Cox–Hastings version derives it from a true Voigt), and
all bands are symmetric, while real condensed-phase bands can be skewed.
Details and sources:
[LITERATURE.md, step 2](LITERATURE.md#step-2--synthetic-spectra).

### Check yourself

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

## Step 3 · Preprocessing

### The idea

A measured spectrum is **peaks + baseline + noise**, and only the peaks carry
chemistry. Preprocessing strips off the other two, then puts samples on a
common scale. Each operation is a small function that takes a `Spectrum` and
returns a new one, so they chain:

```text
 raw ──► remove_baseline ──► smooth ──► normalize ──► ready for peak detection / features
         (drift away)        (noise down)  (scale removed)
```

Because step 2 lets us build the same spectrum with and without baseline and
noise, every function is tested by asking: *does it give back the clean
spectrum?*

### Read

1. `src/spectro/preprocessing.py`: four public functions. Read the `Notes`
   of `estimate_baseline` and `smooth`; they hold the science. Then look at
   `_record`, which keeps the processing history.
2. `tests/test_preprocessing.py`: see how each test builds a "raw" and a
   "clean" spectrum from the same peaks and compares them.
3. `notebooks/03_preprocessing.ipynb`: run it.

### Try

- Call `remove_baseline(raw, lam=1e4)` and `lam=1e10`. Which one eats into
  the peaks, and which one can't bend enough to follow the drift?
- Compare `remove_baseline(raw, "asls")` with the default `"arpls"` on the
  notebook spectrum. Look at the O–H band near 3350 cm⁻¹.
- Smooth the C=O peak with `window=5, 11, 21, 41` and print `y.max()` each
  time. At roughly what window does the height start to drop?
- Try `polyorder=2` versus `polyorder=4` with the same window.
- Print `metadata["preprocessing"]` after a chain of calls, and check that
  the input's metadata didn't change.

### Design choices

| Choice | Why |
| --- | --- |
| Separate small functions, not one `preprocess()` | Each step can be swapped, skipped or reordered, and tested on its own. Plain function calls chain clearly enough; a pipeline helper can come later if needed. |
| arPLS as the default baseline (via pybaselines) | On our synthetic spectra it got back the true baseline best at every noise level. AsLS (the classic choice) sits below the true baseline when there is noise and rides up under the broad O–H band. Other pybaselines methods are one argument away. |
| `estimate_baseline` is public | So you can plot the baseline over the raw spectrum and check it by eye, which is how baseline correction is judged on real data. |
| `lam` default of 1e7, tuned on 1801 points | `lam` is a stiffness penalty whose effect depends on how many points there are. A fixed, documented default is simpler than auto-scaling; change it for very different data. |
| Savitzky–Golay smoothing | It fits a local polynomial, so it keeps peak height and width far better than a moving average for the same noise reduction. |
| Smoothing window in **points**, not cm⁻¹ | That's what the filter actually uses and it doesn't assume evenly spaced data. The docstring says how to convert: keep it below FWHM ÷ point spacing. |
| Four normalisations | "max" for plotting, "area" and "vector" for comparing samples, "snv" for classification (step 7). |
| `y_unit` records the normalisation | "absorbance (max-normalized)" stops a normalised spectrum from being mistaken for real absorbance, and the plot label says so. |
| History in `metadata["preprocessing"]` | A processed spectrum says how it was made, which matters when comparing results later. |
| Order: baseline → smooth → normalise | Normalising first divides by a value that includes the baseline, so identical samples with different backgrounds end up at different scales (notebook part 4). |

### Literature

All four techniques are standard. arPLS beat AsLS in its original paper,
as in our own tests. Our `lam = 1e7` is higher than pybaselines' default of
1e5; it was tuned on our grid and gets rechecked on real data in step 9.
Edwards and Willson recommend a smoothing window of about 0.7 × the
narrowest FWHM, close to our default (0.8). Normalising last is the
consensus; whether to smooth before or after baseline removal varies
between sources. Details and sources:
[LITERATURE.md, step 3](LITERATURE.md#step-3--preprocessing).

### Check yourself

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

## Step 4 · Peak detection

### The idea

Find each peak automatically and read off its center, FWHM and height,
giving a peak table with the same columns as step 2's answer key. The hard
part is not finding maxima (noise makes hundreds) but deciding which ones
are real. A maximum counts as a peak only if it stands out by more than a
few times the noise:

```text
 corrected ──► estimate_noise ──► noise σ
     │                               │
     └──► smooth ──► detect_peaks(prominence = 5σ) ──► peak table ──► match_peaks vs. truth
```

There is a second method for low-noise spectra. Every band makes a sharp dip
in the **second derivative**, even a shoulder that makes no maximum in the
spectrum. `detect_peaks_derivative` finds those dips, so it can find bands
that looking for maxima misses. The cost: differentiating amplifies noise,
and broad bands almost vanish.

### Read

1. `src/spectro/peaks.py`: start with `detect_peaks` and its `Notes` (what
   prominence is, how width is measured, where it fails). Then
   `estimate_noise` and its `Notes`. Then `detect_peaks_derivative`: read
   the `Notes` for its limits. `match_peaks` is bookkeeping; skim it.
2. `tests/test_peaks.py`: see how each test builds a spectrum from known
   peaks and checks that detection gets them back.
3. `notebooks/04_peak_detection.ipynb`: run it.

### Key terms

- **Prominence:** how far a peak rises above the higher of the two lowest
  points separating it from taller peaks on either side. A noise wiggle on
  top of a big peak is high but not prominent, so prominence (not height)
  is what tells real peaks from noise.
- **Robust noise estimate:** peaks are smooth, noise changes at every point,
  so the second difference of `y` is almost pure noise. The median of its
  absolute values ignores the few points where peaks contribute.
- **Second derivative:** the curvature of the spectrum. At a band's center
  it is strongly negative, in a dip narrower than the band. Its depth scales
  as height / FWHM², so narrow bands stand out and broad ones fade.

### Try

- Run `detect_peaks(corrected, prominence=p)` for `p` = 0.005, 0.02, 0.1,
  0.5 on the notebook's noisy spectrum. How many peaks each time?
- Compare `estimate_noise(corrected)` with `estimate_noise(smooth(corrected))`.
  Why is the second one so much smaller?
- Build a spectrum with a single peak at 1715.7 cm⁻¹ and check how close
  the detected center gets, given points 2 cm⁻¹ apart.
- Move two equal peaks (FWHM 20) from 30 to 10 cm⁻¹ apart, in 2 cm⁻¹
  steps. At what separation do they merge? Repeat with `noise=0.01`.
- Look at the detected FWHM of the 2870 cm⁻¹ peak and explain why it is too
  small.
- Run `detect_peaks_derivative` on the clean notebook spectrum, then on the
  noisy one. Which bands does it lose, and in what order?
- Try `detect_peaks_derivative(spectrum, window=w)` on the 12 cm⁻¹ pair from
  notebook part 5 for `w` = 7, 11, 21. When do the two dips merge?

### Design choices

| Choice | Why |
| --- | --- |
| Threshold on prominence, not height | Prominence doesn't depend on the baseline level and ignores noise wiggles on the side of a big peak. Height would do neither. |
| Default threshold 5 × noise | A threshold in units of noise needs no tuning per spectrum. On smoothed pure noise, 3σ still lets the odd bump through and 4σ none; 5σ leaves a margin. |
| Noise from second differences, with the median | It works on a spectrum that has peaks in it, without knowing where they are. The median ignores the points where peaks do change the second difference. |
| Estimate noise before smoothing, detect after | Unsmoothed, the noise makes false peaks and splits the broad O–H band (notebook part 2). Smoothing removes the point-to-point noise the estimate needs, so the order matters. |
| Center from a parabola through the top three points | The grid is 2 cm⁻¹; the parabola puts the center between points, to within ~0.1 cm⁻¹ on clean data. Cheap, no fitting needed. |
| FWHM from `peak_widths` at half prominence, interpolated | Interpolating the half-height crossings gives sub-point widths. Measuring from the prominence base handles peaks on top of broader bands. |
| Same column names as the true peak table | Detection and truth line up by name, so `match_peaks` can compare them directly. |
| `match_peaks` pairs closest first, each peak used once | Two detections can't both claim the same true peak; leftovers are reported as missed or false. The same function will match against literature bands in step 9. |
| Add a second-derivative method | It is the standard IR way to find shoulders and overlapping bands, and the maxima method can't. On clean data it separates equal peaks half a FWHM apart (maxima need ~¾ FWHM). |
| Two separate functions, not one with a `method` argument | They take different input (smoothed vs. unsmoothed) and different settings (window, polyorder), and the derivative one can't give a FWHM. |
| Derivative via Savitzky–Golay, window 11, polyorder 4 | Neighbour differences are far too noisy. Czarnecki (2015) found a small window and high polynomial order keep the dips narrowest; a wider window copes with more noise but blurs close bands. |
| Derivative threshold 12 × the noise *after* the filter | The filter's effect on noise is computed exactly from its coefficients. 12 was set on pure synthetic noise, where 8 still gave the odd false band. |
| Derivative method gives no FWHM | The width of a dip in the derivative of overlapping bands isn't a reliable width. Fitting (step 5) gives widths. |
| No fitting yet | Detection gives a quick estimate and a starting point. Exact parameters and areas, and separating overlapping peaks, come from fitting (steps 5–6). |

### Literature

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Smooth, find local maxima, keep those above a threshold | The basic textbook method for spectra and chromatograms. | Standard. |
| Threshold as a multiple of the noise | Detection limits in analytical chemistry are set the same way, in multiples of the noise standard deviation (the IUPAC detection limit is commonly the blank plus 3σ). | Standard idea; our 5σ was set by testing. |
| Robust noise from the median absolute deviation | The MAD is a standard robust estimate of spread; wavelet denoising estimates noise the same way, from high-frequency parts of the signal. | Standard. |
| Minima of the Savitzky–Golay second derivative | The usual way to locate overlapping IR bands, e.g. protein amide I components (Susi & Byler, 1986). Czarnecki (2015) studies how the window and polynomial order affect it. | Standard, with known limits (noise, broad bands). |
| Not used: continuous wavelet transform (CWT) | Matches the spectrum against peak-shaped wavelets at many widths (Du, Kibbe & Lin, 2006). Popular in mass spectrometry; available as `scipy.signal.find_peaks_cwt`. | Less common for IR; could be compared later. |
| Not used: Fourier self-deconvolution (FSD) | Narrows all bands mathematically before finding peaks (Kauppinen et al., 1981). Classic in IR. | Sensitive to its settings and can create false bands; fitting (steps 5–6) covers the same need. |

Full references:
[LITERATURE.md, step 4](LITERATURE.md#step-4--peak-detection).

### Check yourself

1. Why does a noisy spectrum have many more local maxima than real peaks?
2. What is prominence, and why is it better than height for rejecting
   noise?
3. Why does `estimate_noise` use the second difference rather than the
   spread of `y` itself?
4. Why must the noise be estimated before smoothing?
5. How can the detected center be more precise than the point spacing?
6. Why is the 2870 cm⁻¹ peak's detected FWHM too small?
7. Two equal peaks are closer than about ¾ of their FWHM. What does
   detection report, and what will fix it?
8. Why does `match_peaks` need a tolerance, and why was 40 cm⁻¹ used for
   the noisy spectrum instead of the default 10?
9. How does the second derivative find a shoulder that has no maximum?
10. Why does the second-derivative method miss the O–H band, and why does
    it miss more bands as noise grows?
11. When would you use `detect_peaks` and when `detect_peaks_derivative`?

<details>
<summary>Answers</summary>

1. Every point where noise happens to go up then down is a local maximum,
   so a 1800-point noisy spectrum has hundreds. Only a few are peaks.
2. How far a peak rises above the lowest points separating it from taller
   neighbours. Noise wiggles are small relative to their surroundings even
   when they sit high up on a big peak; and it doesn't depend on the
   baseline level.
3. The spread of `y` is dominated by the peaks. Peaks and baselines are
   smooth, so their second difference is tiny, while noise's is large. The
   median keeps the few peak points from mattering.
4. Smoothing removes the point-to-point changes the estimate measures, so on
   smoothed data it reads far too low and the threshold lets noise through.
5. A parabola is fitted through the highest point and its two neighbours,
   and its vertex can fall between points.
6. It sits on the shoulder of the 2950 cm⁻¹ peak. The width is measured at
   half the prominence, which is measured from the shoulder, so only the
   top of the peak is counted.
7. One wider peak between them, because there's no dip left. Deconvolution
   (step 6): fit a sum of two peak shapes to the region.
8. Detected centers never equal the truth exactly, so "the same peak" means
   "within some distance". The broad O–H band has a flat top, so noise moves
   its detected center by up to ~10–15 cm⁻¹; narrow peaks are within ~1.
9. Each band's curvature is most negative at its own center, so each makes
   its own dip in the second derivative. The dips are narrower than the
   bands, so they stay separate even where the bands have blended into one
   bump.
10. The dip's depth scales as height / FWHM², so a 300 cm⁻¹ band's dip is
    tiny. Differentiating amplifies noise, so the threshold must rise with
    noise, and the shallower dips fall below it first.
11. `detect_peaks_derivative` on good, low-noise spectra where bands overlap
    or appear as shoulders. `detect_peaks` (after smoothing) on noisy data
    and for broad bands. Neither gives final values; fitting does.

</details>

---

## Ready to move on when you can…

- [ ] Draw the pipeline from memory and say what each step takes in and
      gives out.
- [ ] Explain in two sentences why everything uses one `Spectrum` type.
- [ ] Explain why we analyse in absorbance.
- [ ] Explain why synthetic data comes first, and what "ground truth" buys us.
- [ ] Sketch a Gaussian and a Lorentzian with the same height and FWHM, and
      say which has more area.
- [ ] Build a spectrum with `make_spectrum` from your own peak list, without
      looking at the notebook.
- [ ] Explain what arPLS does in one sentence and what `lam` controls.
- [ ] Explain the smoothing trade-off and pick a window for a given FWHM.
- [ ] Say why the order is baseline → smooth → normalise.
- [ ] Explain prominence, and why the detection threshold is a multiple of
      the noise.
- [ ] Say why noise is estimated before smoothing and peaks detected after.
- [ ] Name two cases where detection gets a peak wrong (shoulder, close
      overlap) and what will fix them.
- [ ] Explain how the second derivative finds hidden bands, and its two
      main limits.
- [ ] For each step, say whether our method is standard in the literature,
      and name one place where we simplified or deviated, and why (see
      `docs/LITERATURE.md`).
- [ ] Answer every "Check yourself" question above without opening the
      answers.

## Explaining it to your professor (≈ 1 minute)

> We're building an IR analysis pipeline: load or generate a spectrum,
> preprocess it, detect and fit peaks, then classify samples. Everything
> passes around one validated `Spectrum` object, so each stage is
> independent and swappable. Before writing any analysis, we built a
> synthetic generator: we describe a spectrum as a list of peaks with known
> center, width, height and shape (Gaussian, Lorentzian or pseudo-Voigt),
> plus noise and baseline. It returns the true peak table alongside the
> spectrum, so every later stage can be measured against ground truth. That
> also lets us control noise and peak overlap to find where methods break
> down, and later, how much data classification needs. Preprocessing is a
> set of small functions run in order: arPLS baseline removal, Savitzky–Golay
> smoothing and normalisation. Each is tested by checking it gives back the
> clean synthetic spectrum. Peak detection keeps a local maximum only if its
> prominence is more than five times the noise, which we estimate robustly
> from second differences before smoothing. It returns the same columns as
> the true peak table, and on noisy synthetic spectra it finds every peak
> with no false ones, centers within about a wavenumber. For low-noise
> spectra we also find bands as minima of the second derivative, the
> standard IR way to reveal shoulders and overlapping bands.

Be ready for follow-ups like: *Why pseudo-Voigt and not a true Voigt?* (A
standard, cheap approximation that is close enough for IR and is what we'll
fit with later.) *How do you know the generator is correct?* (Tests check
height at center, FWHM and area against the formulas for every shape.) *Why
arPLS and not AsLS or a polynomial?* (On our test spectra it got back the
true baseline best, and it doesn't need to know where the peaks are.) *How
did you choose the smoothing window?* (Below the narrowest peak's FWHM in
points; the tests show the peak flattening once the window is wider.)
*Why not just threshold on height?* (Height depends on the baseline and
doesn't reject noise wiggles on top of big peaks; prominence does both.)
*What happens with overlapping peaks?* (Equal peaks closer than about ¾
FWHM merge into one; the second derivative separates them down to about half
a FWHM on clean data, and deconvolution in step 6 goes further.) *Are these
standard methods?* (Yes, each step was checked against the literature, with
sources in `docs/LITERATURE.md`. The main deviations are a baseline stiffness
tuned higher than the library default, and a simplified, symmetric
pseudo-Voigt; both get checked on real spectra in step 9.)
