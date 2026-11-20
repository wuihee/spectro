# Peak detection

## The idea

Find each peak automatically and read off its center, FWHM and height,
giving a peak table with the same columns as the synthetic answer key. The hard
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

## Read

1. `src/spectro/peaks.py`: start with `detect_peaks` and its `Notes` (what
   prominence is, how width is measured, where it fails). Then
   `estimate_noise` and its `Notes`. Then `detect_peaks_derivative`: read
   the `Notes` for its limits. `match_peaks` is bookkeeping; skim it.
2. `tests/test_peaks.py`: see how each test builds a spectrum from known
   peaks and checks that detection gets them back.
3. `notebooks/04_peak_detection.ipynb`: run it.

## Key terms

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

## Try

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

## Design choices

| Choice | Why |
| --- | --- |
| Threshold on prominence, not height | Prominence doesn't depend on the baseline level and ignores noise wiggles on the side of a big peak. Height would do neither. |
| Default threshold 5 × noise | A threshold in units of noise needs no tuning per spectrum. On smoothed pure noise, 3σ still lets the odd bump through and 4σ none; 5σ leaves a margin. |
| Noise from second differences, with the median | It works on a spectrum that has peaks in it, without knowing where they are. The median ignores the points where peaks do change the second difference. |
| Estimate noise before smoothing, detect after | Unsmoothed, the noise makes false peaks and splits the broad O–H band (notebook part 2). Smoothing removes the point-to-point noise the estimate needs, so the order matters. |
| Center from a parabola through the top three points | The grid is 2 cm⁻¹; the parabola puts the center between points, to within ~0.1 cm⁻¹ on clean data. Cheap, no fitting needed. |
| FWHM from `peak_widths` at half prominence, interpolated | Interpolating the half-height crossings gives sub-point widths. Measuring from the prominence base handles peaks on top of broader bands. |
| Same column names as the true peak table | Detection and truth line up by name, so `match_peaks` can compare them directly. |
| `match_peaks` pairs closest first, each peak used once | Two detections can't both claim the same true peak; leftovers are reported as missed or false. The same function can match against literature bands on real spectra. |
| Add a second-derivative method | It is the standard IR way to find shoulders and overlapping bands, and the maxima method can't. On clean data it separates equal peaks half a FWHM apart (maxima need ~¾ FWHM). |
| Two separate functions, not one with a `method` argument | They take different input (smoothed vs. unsmoothed) and different settings (window, polyorder), and the derivative one can't give a FWHM. |
| Derivative via Savitzky–Golay, window 11, polyorder 4 | Neighbour differences are far too noisy. Czarnecki (2015) found a small window and high polynomial order keep the dips narrowest; a wider window copes with more noise but blurs close bands. |
| Derivative threshold 12 × the noise *after* the filter | The filter's effect on noise is computed exactly from its coefficients. 12 was set on pure synthetic noise, where 8 still gave the odd false band. |
| Derivative method gives no FWHM | The width of a dip in the derivative of overlapping bands isn't a reliable width. Fitting (`fit_peaks`) gives widths. |
| No fitting yet | Detection gives a quick estimate and a starting point. Exact parameters and areas, and separating overlapping peaks, come from fitting and deconvolution. |

## Literature

| What we do | What the literature does | Verdict |
| --- | --- | --- |
| Smooth, find local maxima, keep those above a threshold | The basic textbook method for spectra and chromatograms. | Standard. |
| Threshold as a multiple of the noise | Detection limits in analytical chemistry are set the same way, in multiples of the noise standard deviation (the IUPAC detection limit is commonly the blank plus 3σ). | Standard idea; our 5σ was set by testing. |
| Robust noise from the median absolute deviation | The MAD is a standard robust estimate of spread; wavelet denoising estimates noise the same way, from high-frequency parts of the signal. | Standard. |
| Minima of the Savitzky–Golay second derivative | The usual way to locate overlapping IR bands, e.g. protein amide I components (Susi & Byler, 1986). Czarnecki (2015) studies how the window and polynomial order affect it. | Standard, with known limits (noise, broad bands). |
| Not used: continuous wavelet transform (CWT) | Matches the spectrum against peak-shaped wavelets at many widths (Du, Kibbe & Lin, 2006). Popular in mass spectrometry; available as `scipy.signal.find_peaks_cwt`. | Less common for IR; could be compared later. |
| Not used: Fourier self-deconvolution (FSD) | Narrows all bands mathematically before finding peaks (Kauppinen et al., 1981). Classic in IR. | Sensitive to its settings and can create false bands; fitting and deconvolution cover the same need. |

Full references:
[LITERATURE.md, Peak detection](../LITERATURE.md#peak-detection).

## Check yourself

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
   (`deconvolve`): fit a sum of two peak shapes to the region.
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

[← Preprocessing](03_preprocessing.md) · [← Study guide](README.md) · [Peak fitting →](05_peak_fitting.md)
